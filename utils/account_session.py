"""Persistent account session helpers for desktop and browser clients."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


APP_NAME = "OmiCClaw"
SESSION_FILENAME = "account-session.json"


def account_support_root() -> Path:
    override = str(os.environ.get("OMICCLAW_SUPPORT_ROOT") or "").strip()
    if override:
        root = Path(override).expanduser().resolve()
    elif os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
    elif sys_platform() == "darwin":
        root = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def account_session_path() -> Path:
    return account_support_root() / SESSION_FILENAME


def load_account_session() -> dict[str, Any]:
    path = account_session_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def persisted_account_token() -> str:
    return str(load_account_session().get("token") or "").strip()


def persisted_account_user() -> dict[str, Any] | None:
    user = load_account_session().get("user")
    return user if isinstance(user, dict) else None


def persist_account_session(token: str, user: dict[str, Any] | None = None) -> None:
    token = str(token or "").strip()
    if not token:
        clear_account_session()
        return

    payload: dict[str, Any] = {"token": token}
    if isinstance(user, dict) and user:
        payload["user"] = user

    path = account_session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".account-session-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def clear_account_session() -> None:
    path = account_session_path()
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def header_bearer_token(header: str | None) -> str:
    text = str(header or "")
    if not text.lower().startswith("bearer "):
        return ""
    return text.split(" ", 1)[1].strip()


def resolve_account_token(header: str | None = None) -> str:
    return header_bearer_token(header) or persisted_account_token()


def sys_platform() -> str:
    return str(os.sys.platform)
