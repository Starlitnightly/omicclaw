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

import json
import logging
import os

from flask import Blueprint, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from omicverse.jarvis.media_ingest import looks_like_image_name, prepare_image_bytes

logger = logging.getLogger("omicclaw.conversations")

bp = Blueprint("conversations", __name__)

# bp.workspace_manager is injected by app.py after registration
# bp.session_manager  is injected by app.py after registration


def _wm():
    return bp.workspace_manager  # type: ignore[attr-defined]


def _sm():
    return bp.session_manager  # type: ignore[attr-defined]


def _load_channel_route(session_id: str) -> dict:
    """Load channel metadata saved alongside a workspace, if present."""
    try:
        route_file = _wm().workspace_dir(session_id) / "channel_route.json"
        if route_file.exists():
            return json.loads(route_file.read_text())
    except Exception:
        logger.exception("load_channel_route_failed sid=%s", session_id)
    return {}


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
    convs_by_id = {}
    for entry in wm.list_conversations():
        sid = entry.get("session_id", "")
        if not sid:
            continue
        route_info = _load_channel_route(sid)
        merged = dict(entry)
        if route_info.get("channel"):
            merged["channel"] = str(route_info.get("channel", "")).lower()
            merged["scope_type"] = str(route_info.get("scope_type", ""))
            merged["scope_id"] = str(route_info.get("scope_id", ""))
            merged["channel_session_id"] = str(route_info.get("channel_session_id", ""))
        convs_by_id[sid] = merged

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
            route_info = _load_channel_route(sid)
            if route_info.get("channel"):
                convs_by_id[sid]["channel"] = str(route_info.get("channel", "")).lower()
                convs_by_id[sid]["scope_type"] = str(route_info.get("scope_type", ""))
                convs_by_id[sid]["scope_id"] = str(route_info.get("scope_id", ""))
                convs_by_id[sid]["channel_session_id"] = str(route_info.get("channel_session_id", ""))

    convs = sorted(convs_by_id.values(), key=lambda e: e.get("last_active", 0), reverse=True)
    return jsonify({"conversations": convs})


@bp.route("/debug", methods=["GET"])
def debug_conversations():
    """Debug: show raw data from workspace index and live sessions."""
    wm = _wm()
    sm = _sm()
    workspace_entries = wm.list_conversations()
    live_sessions = sm.list_sessions() if sm is not None else []
    # Also try Jarvis SM via channel manager
    jarvis_sessions = []
    try:
        from flask import current_app
        cm = current_app.config.get("GATEWAY_CHANNEL_MANAGER")
        if cm is not None:
            jsm = getattr(cm, "_sm", None)
            if jsm is not None and hasattr(jsm, "_sessions"):
                for uid, kernels in jsm._sessions.items():
                    for kname, jsess in kernels.items():
                        gwb = getattr(jsm, "gateway_web_bridge", None)
                        jarvis_sessions.append({
                            "user_id": uid, "kernel": kname,
                            "has_web_bridge": gwb is not None,
                            "web_bridge_type": type(gwb).__name__ if gwb else None,
                        })
    except Exception as e:
        jarvis_sessions = [{"error": str(e)}]
    return jsonify({
        "workspace_count": len(workspace_entries),
        "workspace_entries": workspace_entries,
        "live_session_count": len(live_sessions),
        "live_sessions": live_sessions,
        "jarvis_sm_info": jarvis_sessions,
    })


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
    """Get conversation metadata + history.

    Also hydrates the in-memory AgentSession from workspace history when the
    session is not already live.  This ensures that when the user selects a
    historical conversation in the web UI, the corresponding channel agent
    (e.g. QQ, Telegram) will immediately have multi-turn context available
    via get_prior_history / get_prior_history_simple.
    """
    meta = _wm().get_meta(session_id)
    if meta is None:
        return jsonify({"error": "Conversation not found"}), 404

    history = _wm().load_history(session_id)

    sm = _sm()
    if sm is not None:
        live_session = sm.get_session(session_id)
        if live_session is not None and live_session.history:
            # In-memory is already populated and up-to-date; use it.
            history = live_session.get_history_dicts()
        elif history:
            # In-memory is empty (e.g. after server restart) but workspace has
            # history.  Hydrate the in-memory session so that:
            #   1. Channel agents get context on the next incoming message.
            #   2. The web UI agent chat continues with full context.
            live_session = sm.get_or_create(session_id)
            if not live_session.history:
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role and content:
                        live_session.add_message(role, content)

    return jsonify({
        "session_id": session_id,
        "meta": meta,
        "history": history,
        "route": _load_channel_route(session_id),
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
    mime_type = str(getattr(file, "mimetype", "") or "").strip().lower()
    if mime_type.startswith("image/") or looks_like_image_name(filename):
        prepared = prepare_image_bytes(
            file.read(),
            target_dir=up_dir,
            filename=filename,
            mime_type=mime_type,
            prefix="web_image",
            source="web",
        )
        dest = prepared.path
        filename = dest.name
    else:
        dest = up_dir / filename
        file.save(str(dest))

    stat = dest.stat()
    _wm().touch(session_id)

    payload = {
        "filename": filename,
        "size": stat.st_size,
        "path": str(dest),
        "url": f"/api/conversations/{session_id}/uploads/{filename}",
    }
    if mime_type.startswith("image/") or looks_like_image_name(filename):
        payload["kind"] = "image"
        payload["mime_type"] = prepared.mime_type
    return jsonify(payload)
