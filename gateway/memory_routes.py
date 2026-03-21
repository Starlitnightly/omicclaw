"""
Memory API Blueprint — /api/gateway/memory/*

Provides CRUD + full-text search over the shared MemoryStore.
The MemoryStore path is read from ``app.config["GATEWAY_MEMORY_DB_PATH"]``;
if unset, it falls back to ``~/.ovjarvis/memory.db``.

Endpoints
---------
GET  /api/gateway/memory/stats
GET  /api/gateway/memory/folders
POST /api/gateway/memory/folders
GET  /api/gateway/memory/documents
POST /api/gateway/memory/documents
GET  /api/gateway/memory/documents/<doc_id>
PUT  /api/gateway/memory/documents/<doc_id>
DELETE /api/gateway/memory/documents/<doc_id>
GET  /api/gateway/memory/search?q=<query>[&limit=20][&channel=...][&session_id=...]
"""

import os
from flask import Blueprint, current_app, jsonify, request

memory_bp = Blueprint("gateway_memory", __name__)

_DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".ovjarvis", "memory.db")


def _get_store():
    """Return a cached MemoryStore, creating it on first call."""
    store = current_app.config.get("GATEWAY_MEMORY_STORE")
    if store is None:
        try:
            from omicverse.jarvis.memory.store import MemoryStore  # type: ignore
        except ImportError:
            return None
        db_path = current_app.config.get("GATEWAY_MEMORY_DB_PATH", _DEFAULT_DB)
        store = MemoryStore(db_path)
        current_app.config["GATEWAY_MEMORY_STORE"] = store
    return store


# --------------------------------------------------------------------------
# Stats
# --------------------------------------------------------------------------

@memory_bp.route("/stats", methods=["GET"])
def memory_stats():
    store = _get_store()
    if store is None:
        return jsonify({"error": "omicverse package not installed"}), 503
    return jsonify(store.stats())


# --------------------------------------------------------------------------
# Folders
# --------------------------------------------------------------------------

@memory_bp.route("/folders", methods=["GET"])
def list_folders():
    store = _get_store()
    if store is None:
        return jsonify({"error": "omicverse package not installed"}), 503
    return jsonify({"folders": store.get_folder_tree()})


@memory_bp.route("/folders", methods=["POST"])
def create_folder():
    store = _get_store()
    if store is None:
        return jsonify({"error": "omicverse package not installed"}), 503
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    parent_id = str(body.get("parent_id", "root"))
    folder = store.create_folder(name, parent_id=parent_id)
    return jsonify(folder.to_dict()), 201


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------

@memory_bp.route("/documents", methods=["GET"])
def list_documents():
    store = _get_store()
    if store is None:
        return jsonify({"error": "omicverse package not installed"}), 503
    folder_id = request.args.get("folder_id") or None
    channel = request.args.get("channel") or None
    session_id = request.args.get("session_id") or None
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    docs = store.list_documents(
        folder_id=folder_id,
        channel=channel,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
    return jsonify({"documents": [d.to_dict() for d in docs], "total": len(docs)})


@memory_bp.route("/documents", methods=["POST"])
def create_document():
    store = _get_store()
    if store is None:
        return jsonify({"error": "omicverse package not installed"}), 503
    body = request.get_json(silent=True) or {}
    title = str(body.get("title", "")).strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    doc = store.create_document(
        title=title,
        content=str(body.get("content", "")),
        tags=list(body.get("tags") or []),
        folder_id=str(body.get("folder_id", "root")),
        channel=str(body.get("channel", "web")),
        session_id=str(body.get("session_id", "")),
    )
    return jsonify(doc.to_dict()), 201


@memory_bp.route("/documents/<doc_id>", methods=["GET"])
def get_document(doc_id: str):
    store = _get_store()
    if store is None:
        return jsonify({"error": "omicverse package not installed"}), 503
    doc = store.get_document(doc_id)
    if doc is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(doc.to_dict())


@memory_bp.route("/documents/<doc_id>", methods=["PUT"])
def update_document(doc_id: str):
    store = _get_store()
    if store is None:
        return jsonify({"error": "omicverse package not installed"}), 503
    body = request.get_json(silent=True) or {}
    doc = store.update_document(
        doc_id,
        title=body.get("title"),
        content=body.get("content"),
        tags=body.get("tags"),
        folder_id=body.get("folder_id"),
    )
    if doc is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(doc.to_dict())


@memory_bp.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    store = _get_store()
    if store is None:
        return jsonify({"error": "omicverse package not installed"}), 503
    deleted = store.delete_document(doc_id)
    return jsonify({"deleted": deleted})


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------

@memory_bp.route("/search", methods=["GET"])
def search_memory():
    store = _get_store()
    if store is None:
        return jsonify({"error": "omicverse package not installed"}), 503
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400
    limit = min(int(request.args.get("limit", 20)), 100)
    channel = request.args.get("channel") or None
    session_id = request.args.get("session_id") or None
    results = store.search(query, limit=limit, channel=channel, session_id=session_id)
    return jsonify({"results": [r.to_dict() for r in results], "total": len(results)})
