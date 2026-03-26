from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_CATALOG_PATH = Path(__file__).with_name("llm_provider_catalog.json")

_LEGACY_AUTH_MODE_MAP = {
    "openai_api_key": "official",
    "saved_api_key": "official",
    "openai_oauth": "oauth",
    "openai_codex": "oauth",
}


@lru_cache(maxsize=1)
def load_llm_catalog() -> dict[str, Any]:
    with _CATALOG_PATH.open() as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("LLM catalog must be a JSON object")
    return data


def catalog_path() -> Path:
    return _CATALOG_PATH


def normalize_auth_mode(value: object) -> str:
    mode = str(value or "").strip().lower()
    if mode in _LEGACY_AUTH_MODE_MAP:
        mode = _LEGACY_AUTH_MODE_MAP[mode]
    if mode in {"official", "custom", "oauth"}:
        return mode
    catalog = load_llm_catalog()
    return str(catalog.get("default_auth_mode") or "official")


def api_providers() -> list[dict[str, Any]]:
    return list(load_llm_catalog().get("providers") or [])


def oauth_providers() -> list[dict[str, Any]]:
    return list(load_llm_catalog().get("oauth_providers") or [])


def get_api_provider(provider_id: object) -> dict[str, Any] | None:
    normalized = str(provider_id or "").strip().lower()
    for provider in api_providers():
        if str(provider.get("id") or "").strip().lower() == normalized:
            return provider
    return None


def get_oauth_provider(provider_id: object) -> dict[str, Any] | None:
    normalized = str(provider_id or "").strip().lower()
    for provider in oauth_providers():
        if str(provider.get("id") or "").strip().lower() == normalized:
            return provider
    return None


def normalize_api_provider(provider_id: object) -> str:
    catalog = load_llm_catalog()
    default_provider = str(catalog.get("default_provider") or "openai")
    normalized = str(provider_id or "").strip().lower()
    return normalized if get_api_provider(normalized) else default_provider


def normalize_oauth_provider(provider_id: object) -> str:
    normalized = str(provider_id or "").strip().lower()
    if normalized in {"", "openai", "openai_codex"}:
        normalized = "codex"
    catalog = load_llm_catalog()
    default_provider = str(catalog.get("default_oauth_provider") or "codex")
    return normalized if get_oauth_provider(normalized) else default_provider


def find_provider_for_model(model: object) -> str | None:
    target = str(model or "").strip()
    if not target:
        return None
    for provider in api_providers():
        for item in provider.get("models") or []:
            if str(item.get("id") or "").strip() == target:
                return str(provider.get("id") or "").strip().lower() or None
    return None


def default_model_for_provider(provider_id: object) -> str:
    provider = get_api_provider(provider_id)
    if provider and provider.get("default_model"):
        return str(provider["default_model"])
    catalog = load_llm_catalog()
    fallback = get_api_provider(catalog.get("default_provider"))
    if fallback and fallback.get("default_model"):
        return str(fallback["default_model"])
    return "gpt-5"


def default_model_for_oauth_provider(provider_id: object) -> str:
    provider = get_oauth_provider(provider_id)
    if provider and provider.get("default_model"):
        return str(provider["default_model"])
    return default_model_for_provider("openai")


def default_endpoint_for_provider(provider_id: object) -> str:
    provider = get_api_provider(provider_id)
    if provider and provider.get("api_base"):
        return str(provider["api_base"])
    fallback = get_api_provider(load_llm_catalog().get("default_provider"))
    if fallback and fallback.get("api_base"):
        return str(fallback["api_base"])
    return "https://api.openai.com/v1"


def default_endpoint_for_oauth_provider(provider_id: object) -> str:
    provider = get_oauth_provider(provider_id)
    if provider and provider.get("api_base"):
        return str(provider["api_base"])
    return "https://chatgpt.com/backend-api"


def catalog_for_browser() -> dict[str, Any]:
    catalog = load_llm_catalog()
    return {
        "version": catalog.get("version", 1),
        "auth_modes": catalog.get("auth_modes") or [],
        "providers": api_providers(),
        "oauth_providers": oauth_providers(),
        "default_auth_mode": normalize_auth_mode(catalog.get("default_auth_mode")),
        "default_provider": normalize_api_provider(catalog.get("default_provider")),
        "default_oauth_provider": normalize_oauth_provider(catalog.get("default_oauth_provider")),
        "path": str(_CATALOG_PATH),
    }
