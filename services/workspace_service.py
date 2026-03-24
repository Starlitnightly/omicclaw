"""
Workspace Service — Per-conversation disk workspace management
=============================================================

Each conversation gets an isolated directory under::

    ~/.omicclaw/conversations/<session_id>/
        meta.json       - title, created_at, last_active
        history.jsonl   - ChatMessage records (one JSON object per line)
        uploads/        - any files uploaded by the user
        outputs/        - PNG figures + CSV/PDF artifacts from agent

A lightweight ``conversations.json`` index at ``~/.omicclaw/`` provides
O(1) listing without directory traversal.
"""

import json
import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("omicclaw.workspace")

BASE_DIR = Path.home() / ".omicclaw"
CONVERSATIONS_JSON = BASE_DIR / "conversations.json"
_INDEX_LOCK = threading.Lock()


class WorkspaceManager:
    """Manages per-conversation workspace directories."""

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def workspace_dir(self, session_id: str) -> Path:
        return BASE_DIR / "conversations" / session_id

    def uploads_dir(self, session_id: str) -> Path:
        return self.workspace_dir(session_id) / "uploads"

    def outputs_dir(self, session_id: str) -> Path:
        return self.workspace_dir(session_id) / "outputs"

    def _meta_path(self, session_id: str) -> Path:
        return self.workspace_dir(session_id) / "meta.json"

    def _history_path(self, session_id: str) -> Path:
        return self.workspace_dir(session_id) / "history.jsonl"

    # ------------------------------------------------------------------
    # Conversation lifecycle
    # ------------------------------------------------------------------

    def get_or_create(self, session_id: str, title: str = "") -> dict:
        """Ensure workspace exists; create it if needed.

        Returns the meta dict for this conversation.
        """
        ws = self.workspace_dir(session_id)
        meta_path = self._meta_path(session_id)

        if ws.exists() and meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                return meta
            except Exception:
                pass

        # Create directories
        ws.mkdir(parents=True, exist_ok=True)
        self.uploads_dir(session_id).mkdir(exist_ok=True)
        self.outputs_dir(session_id).mkdir(exist_ok=True)

        now = time.time()
        meta = {
            "session_id": session_id,
            "title": title or "",
            "created_at": now,
            "last_active": now,
        }
        meta_path.write_text(json.dumps(meta))
        self._update_index(meta)
        logger.info("workspace_created", extra={"session_id": session_id})
        return meta

    def list_conversations(self) -> list:
        """Return all conversations sorted by last_active descending."""
        entries = self._read_index()
        entries.sort(key=lambda e: e.get("last_active", 0), reverse=True)
        return entries

    def touch(self, session_id: str) -> None:
        """Update last_active for a conversation."""
        meta_path = self._meta_path(session_id)
        if not meta_path.exists():
            return
        try:
            meta = json.loads(meta_path.read_text())
            meta["last_active"] = time.time()
            meta_path.write_text(json.dumps(meta))
            self._update_index(meta)
        except Exception:
            logger.exception("workspace_touch_failed", extra={"session_id": session_id})

    def rename(self, session_id: str, title: str) -> bool:
        """Rename a conversation. Returns True on success."""
        meta_path = self._meta_path(session_id)
        if not meta_path.exists():
            return False
        try:
            meta = json.loads(meta_path.read_text())
            meta["title"] = title
            meta["last_active"] = time.time()
            meta_path.write_text(json.dumps(meta))
            self._update_index(meta)
            return True
        except Exception:
            logger.exception("workspace_rename_failed", extra={"session_id": session_id})
            return False

    def delete(self, session_id: str) -> bool:
        """Delete conversation workspace and remove from index."""
        ws = self.workspace_dir(session_id)
        try:
            if ws.exists():
                shutil.rmtree(ws)
        except Exception:
            logger.exception("workspace_delete_failed", extra={"session_id": session_id})
            return False

        with _INDEX_LOCK:
            entries = self._read_index_unlocked()
            entries = [e for e in entries if e.get("session_id") != session_id]
            self._write_index_unlocked(entries)
        return True

    def get_meta(self, session_id: str) -> Optional[dict]:
        """Return meta for a conversation, or None if not found."""
        meta_path = self._meta_path(session_id)
        if not meta_path.exists():
            return None
        try:
            return json.loads(meta_path.read_text())
        except Exception:
            return None

    # ------------------------------------------------------------------
    # History persistence
    # ------------------------------------------------------------------

    def save_history(self, session_id: str, messages: list) -> None:
        """Overwrite history.jsonl with the given list of message dicts."""
        path = self._history_path(session_id)
        if not self.workspace_dir(session_id).exists():
            return
        try:
            lines = [json.dumps(m, ensure_ascii=False) for m in messages]
            path.write_text("\n".join(lines) + ("\n" if lines else ""))
        except Exception:
            logger.exception("workspace_save_history_failed", extra={"session_id": session_id})

    def load_history(self, session_id: str) -> list:
        """Load history from history.jsonl. Returns list of message dicts."""
        path = self._history_path(session_id)
        if not path.exists():
            return []
        messages = []
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
        except Exception:
            logger.exception("workspace_load_history_failed", extra={"session_id": session_id})
        return messages

    # ------------------------------------------------------------------
    # Artifact management
    # ------------------------------------------------------------------

    def save_figure(self, session_id: str, png_bytes: bytes, name: str = "") -> Optional[Path]:
        """Write PNG bytes to outputs/. Returns the path on success."""
        out_dir = self.outputs_dir(session_id)
        if not out_dir.exists():
            return None
        ts = int(time.time() * 1000)
        safe_name = (name.replace("/", "_").replace(" ", "_") or "fig") + ".png"
        filename = f"{ts}_{safe_name}"
        dest = out_dir / filename
        try:
            dest.write_bytes(png_bytes)
            return dest
        except Exception:
            logger.exception("workspace_save_figure_failed", extra={"session_id": session_id})
            return None

    def save_artifact(self, session_id: str, data: bytes, filename: str) -> Optional[Path]:
        """Write arbitrary artifact bytes to outputs/<filename>."""
        out_dir = self.outputs_dir(session_id)
        if not out_dir.exists():
            return None
        safe = Path(filename).name  # strip any directory traversal
        dest = out_dir / safe
        try:
            dest.write_bytes(data)
            return dest
        except Exception:
            logger.exception("workspace_save_artifact_failed", extra={"session_id": session_id})
            return None

    def list_outputs(self, session_id: str) -> list:
        """Return file info dicts for all files in outputs/."""
        return self._list_dir(session_id, self.outputs_dir(session_id), "outputs")

    def list_uploads(self, session_id: str) -> list:
        """Return file info dicts for all files in uploads/."""
        return self._list_dir(session_id, self.uploads_dir(session_id), "uploads")

    def _list_dir(self, session_id: str, directory: Path, kind: str) -> list:
        if not directory.exists():
            return []
        result = []
        for p in sorted(directory.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.is_file():
                stat = p.stat()
                result.append({
                    "name": p.name,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "url": f"/api/conversations/{session_id}/{kind}/{p.name}",
                })
        return result

    # ------------------------------------------------------------------
    # Index management (thread-safe)
    # ------------------------------------------------------------------

    def _update_index(self, entry: dict) -> None:
        """Upsert an entry in conversations.json."""
        with _INDEX_LOCK:
            entries = self._read_index_unlocked()
            entries = [e for e in entries if e.get("session_id") != entry.get("session_id")]
            entries.append(entry)
            self._write_index_unlocked(entries)

    def _read_index(self) -> list:
        with _INDEX_LOCK:
            return self._read_index_unlocked()

    def _read_index_unlocked(self) -> list:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        if not CONVERSATIONS_JSON.exists():
            return []
        try:
            return json.loads(CONVERSATIONS_JSON.read_text())
        except Exception:
            return []

    def _write_index_unlocked(self, entries: list) -> None:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            CONVERSATIONS_JSON.write_text(json.dumps(entries, ensure_ascii=False))
        except Exception:
            logger.exception("workspace_write_index_failed")


# Module-level singleton
workspace_manager = WorkspaceManager()
