"""Account routes proxied to the standalone skill store service."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from utils.remote_store import request_remote_json, remote_store_enabled


bp = Blueprint("account", __name__)


def _bearer_token() -> str:
    header = str(request.headers.get("Authorization") or "")
    if not header.lower().startswith("bearer "):
        return ""
    return header.split(" ", 1)[1].strip()


@bp.route("/me", methods=["GET"])
def me():
    if not remote_store_enabled():
        return jsonify({"configured": False, "authenticated": False, "user": None}), 200

    token = _bearer_token()
    if not token:
        return jsonify({"configured": True, "authenticated": False, "user": None}), 200

    data, status = request_remote_json("/api/v1/auth/me", bearer_token=token)
    if status == 200:
        return jsonify({"configured": True, "authenticated": True, "user": data.get("user")}), 200
    if status in (401, 403, 404):
        return jsonify({"configured": True, "authenticated": False, "user": None}), 200
    return jsonify(data), status


@bp.route("/register", methods=["POST"])
def register():
    data, status = request_remote_json(
        "/api/v1/auth/register",
        method="POST",
        payload=request.get_json(silent=True) or {},
    )
    return jsonify(data), status


@bp.route("/login", methods=["POST"])
def login():
    data, status = request_remote_json(
        "/api/v1/auth/login",
        method="POST",
        payload=request.get_json(silent=True) or {},
    )
    return jsonify(data), status


@bp.route("/profile", methods=["PATCH"])
def update_profile():
    data, status = request_remote_json(
        "/api/v1/auth/profile",
        method="PATCH",
        payload=request.get_json(silent=True) or {},
        bearer_token=_bearer_token(),
    )
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
    token = _bearer_token()
    if remote_store_enabled() and token:
        request_remote_json("/api/v1/auth/logout", method="POST", bearer_token=token)
    return jsonify({"success": True}), 200
