"""
Gateway API Blueprint — /api/gateway/*

Endpoints
---------
GET  /api/gateway/status
    Returns gateway running status and connected channels.

GET  /api/gateway/sessions
    Returns a list of cross-channel sessions with their summaries.

POST /api/gateway/sessions/<session_id>/sync
    Bulk-import messages into a session from a channel adapter.
    Body: {"messages": [{"role": ..., "content": ...}, ...], "overwrite": false}

DELETE /api/gateway/sessions/<session_id>
    Delete (evict) a specific session.
"""

from flask import Blueprint, current_app, jsonify, request

gateway_bp = Blueprint("gateway", __name__)


def _get_registry():
    """Return the GatewayChannelRegistry from app config, or None."""
    return current_app.config.get("GATEWAY_CHANNEL_REGISTRY")


def _get_session_manager():
    """Return the session manager injected by GatewayServer (or the module-level singleton)."""
    sm = current_app.config.get("GATEWAY_SESSION_MANAGER")
    if sm is not None:
        return sm
    # Fall back to the module-level singleton used by the rest of the web app
    from services.agent_session_service import session_manager  # type: ignore[import]
    return session_manager


# --------------------------------------------------------------------------
# GET /api/gateway/status
# --------------------------------------------------------------------------

def _get_active_channels() -> list[dict]:
    """Return a merged channel list with live process states when available."""
    try:
        from gateway.channel_config_routes import list_channel_states
        process_states = list_channel_states()
    except Exception:
        process_states = []

    registry = _get_registry()
    # Per-session entries from the registry (populated when messages arrive)
    per_session = registry.list_channels() if registry is not None else []

    # Build a set of already-known channel names from the live process snapshot
    known_names = {c["channel"] for c in process_states}
    live_names = set(known_names)

    # Also include names seen in per-session entries, even if the process
    # snapshot is unavailable (legacy in-process gateway mode).
    known_names.update(c["channel"] for c in per_session)

    # Also derive channels from session messages ([channel] prefix tagging)
    sm = _get_session_manager()
    if sm is not None:
        try:
            for s in sm.list_sessions():
                sid = s.get("session_id", "")
                session = sm.get_session(sid)
                if session is None:
                    continue
                for msg in session.history:
                    content = msg.get("content", "") if isinstance(msg, dict) else ""
                    if content.startswith("[") and "]" in content:
                        ch_name = content[1:content.index("]")]
                        if ch_name and ch_name not in known_names:
                            # Count sessions per channel
                            matching = [c for c in per_session if c["channel"] == ch_name]
                            if not matching:
                                per_session.append({
                                    "channel": ch_name,
                                    "scope_type": "dm",
                                    "scope_id": sid,
                                    "session_id": sid,
                                })
                                known_names.add(ch_name)
                        break  # only need to check first message per session
        except Exception:
            pass

    # Aggregate per-channel stats. Prefer live process state; fall back to
    # per-session entries so legacy in-process gateway mode still renders.
    channel_map: dict[str, dict] = {}
    for entry in process_states + per_session:
        ch = entry.get("channel", "unknown")
        if ch not in channel_map:
            channel_map[ch] = {
                "name": ch,
                "channel": ch,
                "status": entry.get("status", "connected"),
                "session_count": 0,
                "sessions": [],
                "running": bool(entry.get("running", False)),
                "configured": bool(entry.get("configured", False)),
                "can_start": bool(entry.get("can_start", False)),
                "pid": entry.get("pid"),
                "error": entry.get("error"),
            }
        if entry.get("session_id"):
            channel_map[ch]["sessions"].append(entry["session_id"])
        channel_map[ch]["session_count"] = len(channel_map[ch]["sessions"])
        # Live process state should win over derived state from sessions.
        if ch in live_names:
            channel_map[ch]["status"] = entry.get("status", channel_map[ch]["status"])
            channel_map[ch]["running"] = bool(entry.get("running", channel_map[ch]["running"]))
            channel_map[ch]["configured"] = bool(entry.get("configured", channel_map[ch]["configured"]))
            channel_map[ch]["can_start"] = bool(entry.get("can_start", channel_map[ch]["can_start"]))
            channel_map[ch]["pid"] = entry.get("pid", channel_map[ch]["pid"])
            channel_map[ch]["error"] = entry.get("error", channel_map[ch]["error"])

    return list(channel_map.values())


@gateway_bp.route("/status", methods=["GET"])
def gateway_status():
    """Return gateway running state and registered channel connections."""
    registry = _get_registry()
    channels = _get_active_channels()
    return jsonify(
        {
            "status": "running",
            "gateway_mode": bool(registry) or bool(channels),
            "channel_count": len(channels),
            "channels": channels,
        }
    )


# --------------------------------------------------------------------------
# GET /api/gateway/sessions
# --------------------------------------------------------------------------

@gateway_bp.route("/sessions", methods=["GET"])
def list_gateway_sessions():
    """List all cross-channel sessions with lightweight summaries."""
    sm = _get_session_manager()
    sessions = sm.list_sessions()
    registry = _get_registry()

    # Build registry channel map
    registry_channel_map: dict[str, dict] = {}
    if registry is not None:
        registry_channel_map = {c["session_id"]: c for c in registry.list_channels()}

    # Annotate each session with channel derived from registry or message prefix
    for s in sessions:
        sid = s.get("session_id", "")
        if sid in registry_channel_map:
            s["channel"] = registry_channel_map[sid].get("channel", "")
            s["channel_info"] = registry_channel_map[sid]
        else:
            # Derive from first user message prefix [channel]
            channel_name = ""
            session = sm.get_session(sid)
            if session:
                for msg in session.history:
                    content = msg.get("content", "") if isinstance(msg, dict) else ""
                    if content.startswith("[") and "]" in content:
                        channel_name = content[1:content.index("]")]
                        break
            s["channel"] = channel_name
            s["channel_info"] = {}

    return jsonify({"sessions": sessions, "total": len(sessions)})


# --------------------------------------------------------------------------
# POST /api/gateway/sessions/<session_id>/sync
# --------------------------------------------------------------------------

@gateway_bp.route("/sessions/<session_id>/sync", methods=["POST"])
def sync_session(session_id: str):
    """Bulk-import messages from a channel adapter into a web session."""
    body = request.get_json(silent=True) or {}
    messages = body.get("messages", [])
    overwrite = bool(body.get("overwrite", False))

    if not isinstance(messages, list):
        return jsonify({"error": "messages must be a list"}), 400

    sm = _get_session_manager()
    # Import bridge locally to avoid circular import at module load time
    from gateway.context import ChannelContextBridge  # type: ignore[import]
    try:
        from services.workspace_service import workspace_manager as _wm
    except Exception:
        _wm = None
    bridge = ChannelContextBridge(session_manager=sm, workspace_manager=_wm)
    added = bridge.sync_from_channel(session_id, messages, overwrite=overwrite)

    session = sm.get_session(session_id)
    return jsonify(
        {
            "session_id": session_id,
            "messages_added": added,
            "total_messages": len(session.history) if session else 0,
        }
    )


# --------------------------------------------------------------------------
# DELETE /api/gateway/sessions/<session_id>
# --------------------------------------------------------------------------

@gateway_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_gateway_session(session_id: str):
    """Delete (evict) a session."""
    sm = _get_session_manager()
    deleted = sm.delete_session(session_id)
    return jsonify({"session_id": session_id, "deleted": deleted})
