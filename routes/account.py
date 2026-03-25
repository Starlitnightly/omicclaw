"""Account routes proxied to the standalone skill store service."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from utils.account_session import (
    clear_account_session,
    header_bearer_token,
    persist_account_session,
    persisted_account_token,
    persisted_account_user,
)
from utils.remote_store import request_remote_json, remote_store_enabled


bp = Blueprint("account", __name__)


def _header_token() -> str:
    return header_bearer_token(request.headers.get("Authorization"))


def _candidate_tokens() -> list[str]:
    candidates: list[str] = []
    for token in (_header_token(), persisted_account_token()):
        if token and token not in candidates:
            candidates.append(token)
    return candidates


def _request_with_session(path: str, *, method: str = "GET", payload: dict | None = None) -> tuple[dict, int, str]:
    tokens = _candidate_tokens()
    if not tokens:
        return {}, 401, ""

    last_data: dict = {}
    last_status = 401
    for token in tokens:
        data, status = request_remote_json(path, method=method, payload=payload, bearer_token=token)
        if status not in (401, 403):
            return data, status, token
        last_data, last_status = data, status
    return last_data, last_status, ""


@bp.route("/me", methods=["GET"])
def me():
    if not remote_store_enabled():
        return jsonify({"configured": False, "authenticated": False, "user": None}), 200

    tokens = _candidate_tokens()
    if not tokens:
        return jsonify({"configured": True, "authenticated": False, "user": None}), 200

    data, status, active_token = _request_with_session("/api/v1/auth/me")
    if status == 200:
        user = data.get("user")
        persist_account_session(active_token or tokens[0], user if isinstance(user, dict) else None)
        return jsonify({"configured": True, "authenticated": True, "user": user}), 200
    if status in (401, 403, 404):
        clear_account_session()
        return jsonify({"configured": True, "authenticated": False, "user": None}), 200
    cached_user = persisted_account_user()
    if cached_user:
        return jsonify({"configured": True, "authenticated": True, "user": cached_user, "stale": True}), 200
    return jsonify(data), status


@bp.route("/register", methods=["POST"])
def register():
    data, status = request_remote_json(
        "/api/v1/auth/register",
        method="POST",
        payload=request.get_json(silent=True) or {},
    )
    if 200 <= status < 300 and data.get("token"):
        persist_account_session(str(data.get("token") or ""), data.get("user") if isinstance(data.get("user"), dict) else None)
    return jsonify(data), status


@bp.route("/login", methods=["POST"])
def login():
    data, status = request_remote_json(
        "/api/v1/auth/login",
        method="POST",
        payload=request.get_json(silent=True) or {},
    )
    if 200 <= status < 300 and data.get("token"):
        persist_account_session(str(data.get("token") or ""), data.get("user") if isinstance(data.get("user"), dict) else None)
    return jsonify(data), status


@bp.route("/profile", methods=["PATCH"])
def update_profile():
    data, status, active_token = _request_with_session(
        "/api/v1/auth/profile",
        method="PATCH",
        payload=request.get_json(silent=True) or {},
    )
    if status == 200 and active_token:
        persist_account_session(active_token, data.get("user") if isinstance(data.get("user"), dict) else None)
    elif status in (401, 403, 404):
        clear_account_session()
    return jsonify(data), status


@bp.route("/resend-activation", methods=["POST"])
def resend_activation():
    data, status = request_remote_json(
        "/api/v1/auth/resend-activation",
        method="POST",
        payload=request.get_json(silent=True) or {},
    )
    return jsonify(data), status


@bp.route("/logout", methods=["POST"])
def logout():
    token = persisted_account_token()
    if remote_store_enabled() and token:
        request_remote_json("/api/v1/auth/logout", method="POST", bearer_token=token)
    clear_account_session()
    return jsonify({"success": True}), 200
