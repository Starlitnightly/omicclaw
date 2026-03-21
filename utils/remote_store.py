"""Helpers for proxying requests to the standalone skill store service."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_SKILL_STORE_URL = "https://skills.omicverse.com"


def remote_store_base_url() -> str:
    return str(os.environ.get("OV_SKILL_STORE_URL") or DEFAULT_SKILL_STORE_URL).strip().rstrip("/")


def remote_store_enabled() -> bool:
    return bool(remote_store_base_url())


def request_remote_json(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    bearer_token: str = "",
    timeout: float = 8.0,
) -> tuple[dict[str, Any], int]:
    base_url = remote_store_base_url()
    if not base_url:
        return {"error": "Remote skill store is not configured"}, 503

    url = f"{base_url}{path}"
    if query:
        encoded = urlencode({key: value for key, value in query.items() if value is not None})
        if encoded:
            url = f"{url}?{encoded}"

    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    req = Request(url, data=body, method=method.upper(), headers=headers)

    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            if not isinstance(data, dict):
                data = {"data": data}
            return data, int(getattr(response, "status", 200) or 200)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        try:
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {"error": raw or str(exc)}
        if not isinstance(data, dict):
            data = {"error": str(data)}
        return data, int(exc.code)
    except URLError as exc:
        return {"error": f"Remote skill store unavailable: {exc.reason}"}, 502
    except Exception as exc:
        return {"error": f"Remote skill store request failed: {exc}"}, 502
