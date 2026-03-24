"""
Conversations Routes — Per-conversation workspace management API
================================================================
Blueprint prefix: /api/conversations

Endpoints
---------
GET  /                          List all conversations (last_active desc)
POST /                          Create a new conversation
GET  /<id>                      Get conversation detail + history
DELETE /<id>                    Delete conversation and workspace files
PATCH /<id>                     Rename conversation
GET  /<id>/outputs              List output files
GET  /<id>/uploads              List uploaded files
GET  /<id>/outputs/<filename>   Download output file
GET  /<id>/uploads/<filename>   Download uploaded file
POST /<id>/upload               Upload any file into workspace/uploads/
"""

import logging
import os

from flask import Blueprint, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

logger = logging.getLogger("omicclaw.conversations")

bp = Blueprint("conversations", __name__)

# bp.workspace_manager is injected by app.py after registration
# bp.session_manager  is injected by app.py after registration


def _wm():
    return bp.workspace_manager  # type: ignore[attr-defined]


def _sm():
    return bp.session_manager  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------

@bp.route("/", methods=["GET"])
def list_conversations():
    """Return all conversations sorted by last_active descending.

    Merges workspace index entries with live session_manager sessions so that:
    - channel sessions (Telegram, WeChat, …) created outside the web UI appear
    - browser sessions that sent messages before a workspace was created appear
    """
    wm = _wm()
    sm = _sm()

    # Start with workspace index (persisted, survives restarts)
    convs_by_id = {c["session_id"]: c for c in wm.list_conversations()}

    # Merge live sessions (in-memory, may include channel sessions)
    if sm is not None:
        for s in sm.list_sessions():
            sid = s.get("session_id", "")
            if not sid or sid in convs_by_id:
                continue
            # Skip sessions with no messages (not worth showing)
            if s.get("message_count", 0) == 0:
                continue
            # Derive title from session title field or first user message prefix
            title = s.get("title") or ""
            if not title:
                live = sm.get_session(sid)
                if live and live.history:
                    first = live.history[0]
                    content = first.content if hasattr(first, "content") else (first.get("content", "") if isinstance(first, dict) else "")
                    # Extract [channel] prefix if present
                    if content.startswith("[") and "]" in content:
                        bracket_end = content.index("]")
                        ch = content[1:bracket_end]
                        rest = content[bracket_end + 2:bracket_end + 22]
                        title = f"[{ch}] {rest}"
                    else:
                        title = content[:25]
            convs_by_id[sid] = {
                "session_id": sid,
                "title": title,
                "created_at": s.get("created_at", 0),
                "last_active": s.get("last_active", 0),
            }

    convs = sorted(convs_by_id.values(), key=lambda e: e.get("last_active", 0), reverse=True)
    return jsonify({"conversations": convs})


@bp.route("/", methods=["POST"])
def create_conversation():
    """Create a new conversation workspace.

    Optional body: { "session_id": "...", "title": "..." }
    """
    from services.agent_service import make_turn_id  # local import to avoid circulars

    payload = request.json or {}
    session_id = (payload.get("session_id") or "").strip() or make_turn_id()
    title = (payload.get("title") or "").strip()

    meta = _wm().get_or_create(session_id, title=title)
    return jsonify({"session_id": session_id, "workspace": meta}), 201


@bp.route("/<session_id>", methods=["GET"])
def get_conversation(session_id):
    """Get conversation metadata + history."""
    meta = _wm().get_meta(session_id)
    if meta is None:
        return jsonify({"error": "Conversation not found"}), 404

    history = _wm().load_history(session_id)

    # Also try to get live session history (more up-to-date if in memory)
    sm = _sm()
    if sm is not None:
        live_session = sm.get_session(session_id)
        if live_session is not None and live_session.history:
            history = live_session.get_history_dicts()

    return jsonify({
        "session_id": session_id,
        "meta": meta,
        "history": history,
    })


@bp.route("/<session_id>", methods=["DELETE"])
def delete_conversation(session_id):
    """Delete conversation workspace and in-memory session."""
    sm = _sm()
    if sm is not None:
        sm.delete_session(session_id)

    _wm().delete(session_id)
    return jsonify({"deleted": session_id})


@bp.route("/<session_id>", methods=["PATCH"])
def rename_conversation(session_id):
    """Rename a conversation.

    Body: { "title": "New title" }
    """
    payload = request.json or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    ok = _wm().rename(session_id, title)
    if not ok:
        return jsonify({"error": "Conversation not found"}), 404

    # Sync title to in-memory session if present
    sm = _sm()
    if sm is not None:
        live_session = sm.get_session(session_id)
        if live_session is not None:
            live_session.title = title

    return jsonify({"session_id": session_id, "title": title})


# ---------------------------------------------------------------------------
# File listing
# ---------------------------------------------------------------------------

@bp.route("/<session_id>/outputs", methods=["GET"])
def list_outputs(session_id):
    files = _wm().list_outputs(session_id)
    return jsonify({"session_id": session_id, "files": files})


@bp.route("/<session_id>/uploads", methods=["GET"])
def list_uploads(session_id):
    files = _wm().list_uploads(session_id)
    return jsonify({"session_id": session_id, "files": files})


# ---------------------------------------------------------------------------
# File download
# ---------------------------------------------------------------------------

@bp.route("/<session_id>/outputs/<path:filename>", methods=["GET"])
def download_output(session_id, filename):
    out_dir = _wm().outputs_dir(session_id)
    if not out_dir.exists():
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(str(out_dir), filename)


@bp.route("/<session_id>/uploads/<path:filename>", methods=["GET"])
def download_upload(session_id, filename):
    up_dir = _wm().uploads_dir(session_id)
    if not up_dir.exists():
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(str(up_dir), filename)


# ---------------------------------------------------------------------------
# Generic file upload into workspace
# ---------------------------------------------------------------------------

@bp.route("/<session_id>/upload", methods=["POST"])
def upload_to_workspace(session_id):
    """Upload any file into workspace/uploads/<filename>.

    If the file is a .h5ad, the caller should also hit /api/upload to
    trigger the data adaptor pipeline.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No filename"}), 400

    # Ensure workspace exists
    _wm().get_or_create(session_id)

    filename = secure_filename(file.filename)
    up_dir = _wm().uploads_dir(session_id)
    up_dir.mkdir(parents=True, exist_ok=True)
    dest = up_dir / filename
    file.save(str(dest))

    stat = dest.stat()
    _wm().touch(session_id)

    return jsonify({
        "filename": filename,
        "size": stat.st_size,
        "path": str(dest),
        "url": f"/api/conversations/{session_id}/uploads/{filename}",
    })
