"""
Channel configuration API — /api/gateway/channels/*

Endpoints:
  GET  /api/gateway/channels/config          Read full jarvis config (tokens masked)
  POST /api/gateway/channels/config          Write full jarvis config
  POST /api/gateway/channels/<ch>/test       Test channel connectivity
  GET  /api/gateway/channels/processes       List running channel bot processes
  POST /api/gateway/channels/<ch>/start      Start channel bot subprocess
  POST /api/gateway/channels/<ch>/stop       Stop channel bot subprocess
"""

from __future__ import annotations

import base64
import collections
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

import requests
from flask import Blueprint, current_app, has_app_context, jsonify, request

channel_config_bp = Blueprint("channel_config", __name__)

# --------------------------------------------------------------------------
# Global process registry + persistent log buffers
# --------------------------------------------------------------------------

_PROCESSES: dict[str, subprocess.Popen] = {}
_PROCESS_LOCK = threading.Lock()

# Codex OAuth flow state — lives for one login attempt
_codex_oauth_state: dict = {"status": "idle"}
_codex_oauth_lock = threading.Lock()

# Latest lifecycle snapshot for each channel. This is shared by the config
# endpoint, auto-start bootstrap, and the per-channel start/stop handlers.
_CHANNEL_STATES: dict[str, dict] = {}

# Ring-buffer of log lines per channel — survives process death so the
# user can see crash output after the process exits.
_LOG_BUFFERS: dict[str, collections.deque] = {}
_LOG_BUF_SIZE = 200  # max lines kept per channel


def _terminate_process(proc: subprocess.Popen, timeout: float = 5.0) -> None:
    """Terminate *proc* and fall back to kill if it does not exit quickly."""
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass


def _register_exit_state(channel: str, proc: subprocess.Popen, *, intentional: bool) -> None:
    """Store the final lifecycle state for a channel process."""
    with _PROCESS_LOCK:
        prev = dict(_CHANNEL_STATES.get(channel, {}))
        _CHANNEL_STATES[channel] = {
            **prev,
            "channel": channel,
            "status": "stopped" if intentional else "failed",
            "running": False,
            "pid": proc.pid,
            "exit_code": proc.poll(),
        }
        _PROCESSES.pop(channel, None)


def _log_reader(channel: str, proc: subprocess.Popen) -> None:
    """Background thread: drain proc.stdout into _LOG_BUFFERS[channel]."""
    buf = _LOG_BUFFERS.setdefault(channel, collections.deque(maxlen=_LOG_BUF_SIZE))
    try:
        for line in proc.stdout:
            buf.append(line)
    except Exception:
        pass
    # Append exit code so users can see why the process ended
    rc = proc.wait()
    buf.append(f"\n[process exited with code {rc}]\n")
    with _PROCESS_LOCK:
        prev = dict(_CHANNEL_STATES.get(channel, {}))
        intentional = prev.get("desired_state") == "stopped"
    _register_exit_state(channel, proc, intentional=intentional)


def _start_log_reader(channel: str, proc: subprocess.Popen) -> None:
    """Clear old buffer and start a fresh reader thread for this process."""
    _LOG_BUFFERS[channel] = collections.deque(maxlen=_LOG_BUF_SIZE)
    t = threading.Thread(target=_log_reader, args=(channel, proc), daemon=True)
    t.start()


def _find_omicverse_cmd() -> list[str]:
    """Return the best command prefix for 'omicverse <subcommand>'."""
    # 1. Binary next to sys.executable (same venv) — most reliable
    venv_binary = Path(sys.executable).parent / "omicverse"
    if venv_binary.exists():
        return [str(venv_binary)]
    # 2. Binary anywhere on PATH
    binary = shutil.which("omicverse")
    if binary:
        return [binary]
    # 3. Fall back to python -m omicverse
    return [sys.executable, "-m", "omicverse"]

# --------------------------------------------------------------------------
# Default / schema
# --------------------------------------------------------------------------

DEFAULT_CONFIG: dict = {
    "channel": None,
    "model": "gpt-4o",
    "auth_mode": "openai_api_key",
    "endpoint": None,
    "session_dir": None,
    "max_prompts": 0,
    "temperature": 0.3,
    "top_p": 1.0,
    "max_tokens": 2048,
    "timeout": 60,
    "system_prompt": "",
    "telegram": {
        "token": None,
        "allowed_users": [],
    },
    "discord": {
        "token": None,
    },
    "wechat": {
        "token": None,
        "base_url": "https://ilinkai.weixin.qq.com",
        "allow_from": [],
    },
    "feishu": {
        "app_id": None,
        "app_secret": None,
        "connection_mode": "websocket",
        "verification_token": None,
        "encrypt_key": None,
        "host": "0.0.0.0",
        "port": 8080,
        "path": "/feishu/events",
    },
    "imessage": {
        "cli_path": "imsg",
        "db_path": "~/Library/Messages/chat.db",
        "include_attachments": False,
    },
    "qq": {
        "app_id": None,
        "client_secret": None,
        "image_host": None,
        "image_server_port": 8081,
        "markdown": False,
    },
}

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _config_path() -> Path:
    custom = current_app.config.get("GATEWAY_JARVIS_CONFIG_PATH")
    if custom:
        return Path(custom)
    return Path.home() / ".ovjarvis" / "config.json"


def _auth_path() -> Path:
    return _config_path().parent / "auth.json"


def _read_config() -> dict:
    p = _config_path()
    merged: dict = {}
    # Deep-merge defaults first
    for k, v in DEFAULT_CONFIG.items():
        merged[k] = dict(v) if isinstance(v, dict) else v
    if p.exists():
        try:
            with open(p) as f:
                data = json.load(f)
            for k, v in data.items():
                if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                    merged[k] = {**merged[k], **v}
                else:
                    merged[k] = v
        except Exception:
            pass
    return merged


def _write_config(new_cfg: dict) -> None:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_config()
    # Preserve existing secret values if the incoming value is empty/None
    _SENSITIVE = [
        ("telegram", "token"),
        ("discord", "token"),
        ("wechat", "token"),
        ("feishu", "app_secret"),
        ("feishu", "verification_token"),
        ("feishu", "encrypt_key"),
        ("qq", "client_secret"),
    ]
    for section, field in _SENSITIVE:
        incoming = new_cfg.get(section, {}).get(field)
        # Preserve existing value when incoming is empty OR looks like a masked placeholder
        if not incoming or _looks_masked(incoming):
            old_val = existing.get(section, {}).get(field)
            if old_val:
                new_cfg.setdefault(section, {})[field] = old_val
    with open(p, "w") as f:
        json.dump(new_cfg, f, indent=2)


def _read_api_key() -> str:
    p = _auth_path()
    if p.exists():
        try:
            with open(p) as f:
                data = json.load(f)
            return data.get("OPENAI_API_KEY") or ""
        except Exception:
            pass
    return os.environ.get("OPENAI_API_KEY", "")


def _read_auth_data() -> dict:
    p = _auth_path()
    if not p.exists():
        return {}
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return {}


def _read_codex_access_token() -> str:
    auth = _read_auth_data()
    return str((auth.get("tokens") or {}).get("access_token") or "").strip()


def _read_codex_account_id() -> str:
    auth = _read_auth_data()
    return str((auth.get("tokens") or {}).get("account_id") or "").strip()


def _resolve_effective_api_key(endpoint: str | None = None, explicit_api_key: str | None = None) -> str:
    endpoint_text = str(endpoint or "").strip()
    api_key = str(explicit_api_key or "").strip() or _read_api_key()
    if "chatgpt.com" in endpoint_text:
        codex_token = _read_codex_access_token()
        if codex_token:
            return codex_token
    return api_key


def _get_channel_manager():
    if not has_app_context():
        return None
    return current_app.config.get("GATEWAY_CHANNEL_MANAGER")


def _write_api_key(key: str) -> None:
    if not key:
        return
    p = _auth_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if p.exists():
        try:
            with open(p) as f:
                data = json.load(f)
        except Exception:
            pass
    data["OPENAI_API_KEY"] = key
    with open(p, "w") as f:
        json.dump(data, f, indent=2)


def _mask(s: Optional[str]) -> str:
    if not s:
        return ""
    if len(s) <= 8:
        return "****"
    return s[:4] + "****" + s[-4:]


def _looks_masked(s: Optional[str]) -> bool:
    """Return True if the string looks like a value we already masked (e.g. 'ab12****ef78').
    We use this to avoid overwriting real secrets with masked placeholders on Save."""
    if not s:
        return False
    return "****" in s


def _random_wechat_uin() -> str:
    value = secrets.randbits(32)
    return base64.b64encode(str(value).encode("utf-8")).decode("ascii")


def _make_qr_data_uri(content: str) -> str:
    """Generate a PNG QR code from *content* and return a data: URI.

    Mirrors cc-weixin's ``QRCode.toString(qrcode_img_content)`` — the WeChat
    API's ``qrcode_img_content`` field is a URL that must be *encoded into* a
    QR code, not treated as raw image bytes.
    """
    if not content:
        return ""
    try:
        import io
        import qrcode  # type: ignore
        img = qrcode.make(content)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""


def _ilink_headers(body: str, *, token: Optional[str] = None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": _random_wechat_uin(),
        "Content-Length": str(len(body.encode("utf-8"))),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _ilink_get_headers(*, token: Optional[str] = None) -> dict[str, str]:
    """Headers for GET requests — no Content-Length (mirrors cc-weixin apiGet)."""
    headers: dict[str, str] = {
        "AuthorizationType": "ilink_bot_token",
        "X-WECHAT-UIN": _random_wechat_uin(),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _resolve_wechat_base_url(body: dict[str, object], cfg: dict) -> str:
    custom = str(body.get("base_url") or cfg.get("wechat", {}).get("base_url") or "").strip()
    if not custom:
        custom = "https://ilinkai.weixin.qq.com"
    return custom.rstrip("/")


def _set_channel_state(channel: str, **state: object) -> dict:
    """Store the latest lifecycle state for a channel."""
    with _PROCESS_LOCK:
        current = dict(_CHANNEL_STATES.get(channel, {}))
        current.update(state)
        current["channel"] = channel
        _CHANNEL_STATES[channel] = current
        return dict(current)


def _channel_configured(channel: str, cfg: dict) -> bool:
    """Return True when a channel has enough config to be started."""
    if channel == "telegram":
        return bool(cfg.get("telegram", {}).get("token"))
    if channel == "discord":
        return bool(cfg.get("discord", {}).get("token"))
    if channel == "wechat":
        return bool(cfg.get("wechat", {}).get("token"))
    if channel == "feishu":
        feishu_cfg = cfg.get("feishu", {})
        return bool(feishu_cfg.get("app_id") and feishu_cfg.get("app_secret"))
    if channel == "qq":
        qq_cfg = cfg.get("qq", {})
        return bool(qq_cfg.get("app_id") and qq_cfg.get("client_secret"))
    if channel == "imessage":
        imessage_cfg = cfg.get("imessage", {})
        return bool(imessage_cfg.get("cli_path") or imessage_cfg.get("db_path"))
    return False


def _build_start_command(channel: str, cfg: dict, api_key: str) -> list[str]:
    """Build the command line used to start a channel bot process."""
    # Use the channel-only Jarvis runner here.
    #
    # `omicverse claw --channel ...` defaults to gateway mode in the OmicVerse
    # CLI dispatcher, which starts a second GatewayServer and may auto-open a
    # new browser window. The gateway UI's fallback subprocess path should only
    # launch the channel backend itself.
    cmd = _find_omicverse_cmd() + ["jarvis", "--channel", channel]

    if cfg.get("model"):
        cmd += ["--model", cfg["model"]]
    if api_key:
        cmd += ["--api-key", api_key]
    if cfg.get("endpoint"):
        cmd += ["--endpoint", cfg["endpoint"]]

    if channel == "telegram":
        token = cfg.get("telegram", {}).get("token") or ""
        if not token:
            raise RuntimeError("Telegram token not configured — save config first")
        cmd += ["--token", token]
        for u in cfg.get("telegram", {}).get("allowed_users") or []:
            cmd += ["--allowed-user", str(u)]
    elif channel == "discord":
        dc = cfg.get("discord", {})
        if not dc.get("token"):
            raise RuntimeError("Discord token not configured — save config first")
        cmd += ["--discord-token", dc["token"]]
    elif channel == "wechat":
        wc = cfg.get("wechat", {})
        if not wc.get("token"):
            raise RuntimeError("WeChat token not configured — save config first")
        cmd += ["--wechat-token", wc["token"]]
        if wc.get("base_url"):
            cmd += ["--wechat-base-url", wc["base_url"]]
        for user_id in wc.get("allow_from") or []:
            cmd += ["--wechat-allow-from", str(user_id)]
    elif channel == "feishu":
        fc = cfg.get("feishu", {})
        if not fc.get("app_id") or not fc.get("app_secret"):
            raise RuntimeError("Feishu app_id/app_secret not configured")
        cmd += [
            "--feishu-app-id",
            fc["app_id"],
            "--feishu-app-secret",
            fc["app_secret"],
            "--feishu-connection-mode",
            fc.get("connection_mode", "websocket"),
        ]
        if fc.get("verification_token"):
            cmd += ["--feishu-verification-token", fc["verification_token"]]
        if fc.get("encrypt_key"):
            cmd += ["--feishu-encrypt-key", fc["encrypt_key"]]
        cmd += [
            "--feishu-host",
            fc.get("host", "0.0.0.0"),
            "--feishu-port",
            str(fc.get("port", 8080)),
            "--feishu-path",
            fc.get("path", "/feishu/events"),
        ]
    elif channel == "qq":
        qc = cfg.get("qq", {})
        if not qc.get("app_id") or not qc.get("client_secret"):
            raise RuntimeError("QQ app_id/client_secret not configured")
        cmd += ["--qq-app-id", qc["app_id"], "--qq-client-secret", qc["client_secret"]]
        if qc.get("image_host"):
            cmd += ["--qq-image-host", qc["image_host"]]
        if qc.get("image_server_port"):
            cmd += ["--qq-image-server-port", str(qc["image_server_port"])]
        if qc.get("markdown"):
            cmd += ["--qq-markdown"]
    elif channel == "imessage":
        ic = cfg.get("imessage", {})
        if ic.get("cli_path"):
            cmd += ["--imessage-cli-path", ic["cli_path"]]
        if ic.get("db_path"):
            cmd += ["--imessage-db-path", ic["db_path"]]
        if ic.get("include_attachments"):
            cmd += ["--imessage-include-attachments"]

    return cmd


def _refresh_channel_states_locked() -> None:
    """Refresh cached channel states from live subprocesses."""
    dead = [ch for ch, p in _PROCESSES.items() if p.poll() is not None]
    for ch in dead:
        proc = _PROCESSES.pop(ch, None)
        prev = dict(_CHANNEL_STATES.get(ch, {}))
        rc = proc.poll() if proc is not None else prev.get("exit_code")
        intentional = prev.get("desired_state") == "stopped"
        _CHANNEL_STATES[ch] = {
            **prev,
            "channel": ch,
            "status": "stopped" if intentional else "failed",
            "running": False,
            "pid": proc.pid if proc is not None else prev.get("pid"),
            "exit_code": rc,
        }


def _start_channel_process(
    channel: str,
    *,
    cfg: Optional[dict] = None,
    api_key: Optional[str] = None,
    source: str = "manual",
) -> dict:
    """Start a channel bot process and persist its state."""
    cfg = cfg or _read_config()
    api_key = _read_api_key() if api_key is None else api_key

    with _PROCESS_LOCK:
        _refresh_channel_states_locked()
        existing = _PROCESSES.get(channel)
        if existing and existing.poll() is None:
            return {"ok": False, "error": f"{channel} is already running (pid={existing.pid})"}

    try:
        cmd = _build_start_command(channel, cfg, api_key)
    except RuntimeError as exc:
        _set_channel_state(
            channel,
            status="failed",
            running=False,
            error=str(exc),
            configured=_channel_configured(channel, cfg),
        )
        return {"ok": False, "error": str(exc)}

    try:
        env = os.environ.copy()
        if api_key:
            env["OPENAI_API_KEY"] = api_key
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        with _PROCESS_LOCK:
            _PROCESSES[channel] = proc
            _CHANNEL_STATES[channel] = {
                "channel": channel,
                "status": "running",
                "running": True,
                "pid": proc.pid,
                "configured": _channel_configured(channel, cfg),
                "desired_state": "running",
                "source": source,
                "command": cmd,
            }
        _start_log_reader(channel, proc)
        _LOG_BUFFERS[channel].appendleft(f"$ {' '.join(cmd)}\n\n")
        return {"ok": True, "pid": proc.pid, "message": f"Started {channel} bot (pid={proc.pid})"}
    except Exception as exc:
        _set_channel_state(
            channel,
            status="failed",
            running=False,
            error=str(exc),
            configured=_channel_configured(channel, cfg),
        )
        return {"ok": False, "error": str(exc)}


def _stop_channel_process(channel: str, proc: subprocess.Popen, *, timeout: float = 5.0) -> dict:
    """Stop a tracked channel process and update its state."""
    _set_channel_state(channel, status="stopped", running=False, desired_state="stopped")
    _terminate_process(proc, timeout=timeout)
    _register_exit_state(channel, proc, intentional=True)
    return {"channel": channel, "ok": True, "pid": proc.pid}


def list_channel_states() -> list[dict]:
    """Return a snapshot of all supported channel states."""
    cfg = _read_config()
    manager = _get_channel_manager()
    if manager is not None:
        managed = {item.get("channel"): dict(item) for item in manager.list_states(cfg)}
    else:
        managed = {}
    with _PROCESS_LOCK:
        _refresh_channel_states_locked()
        snapshot: list[dict] = []
        for channel in ("telegram", "discord", "wechat", "feishu", "qq", "imessage"):
            if channel in managed:
                snapshot.append(managed[channel])
                continue
            configured = _channel_configured(channel, cfg)
            state = dict(_CHANNEL_STATES.get(channel, {}))
            if not state:
                state = {
                    "channel": channel,
                    "status": "stopped" if configured else "not_configured",
                    "running": False,
                }
            else:
                state.setdefault("status", "stopped" if configured else "not_configured")
                state["running"] = state.get("status") == "running"
            state["configured"] = configured
            state["can_start"] = configured and state.get("status") not in {"running", "starting", "not_configured"}
            snapshot.append(state)
        return snapshot


def auto_start_configured_channels() -> list[dict]:
    """Start every configured channel once at gateway bootstrap."""
    cfg = _read_config()
    api_key = _read_api_key()
    results: list[dict] = []
    manager = _get_channel_manager()
    if manager is not None:
        try:
            results.extend(manager.auto_start_configured(cfg, api_key=api_key))
        except Exception as exc:
            results.append({"ok": False, "error": str(exc), "source": "in-process"})
    for channel in ("telegram", "discord", "wechat", "feishu", "qq", "imessage"):
        if manager is not None and manager.supports(channel):
            continue
        if not _channel_configured(channel, cfg):
            _set_channel_state(channel, status="not_configured", running=False, configured=False)
            continue
        results.append(_start_channel_process(channel, cfg=cfg, api_key=api_key, source="gateway-startup"))
    return results


def stop_all_channel_processes(timeout: float = 5.0) -> list[dict]:
    """Stop every tracked channel process.

    This is used when the gateway process exits so child bot subprocesses do
    not survive as orphaned processes.
    """
    with _PROCESS_LOCK:
        _refresh_channel_states_locked()
        snapshot = list(_PROCESSES.items())
    results: list[dict] = []
    for channel, proc in snapshot:
        try:
            results.append(_stop_channel_process(channel, proc, timeout=timeout))
        except Exception as exc:
            _set_channel_state(channel, status="failed", running=False, error=str(exc))
            results.append({"channel": channel, "ok": False, "error": str(exc)})
    with _PROCESS_LOCK:
        _PROCESSES.clear()
    return results


def _get_log_buffer(channel: str) -> str:
    """Return buffered log lines for a channel (persistent across process death)."""
    buf = _LOG_BUFFERS.get(channel)
    if not buf:
        return ""
    return "".join(buf)


# --------------------------------------------------------------------------
# Shared LLM config fields (kept in one place to avoid duplication across routes)
_LLM_FIELDS = ("model", "endpoint", "temperature", "top_p", "max_tokens", "timeout", "system_prompt")
_LLM_NULLABLE = frozenset({"model", "endpoint"})  # empty string → None

# Routes
# --------------------------------------------------------------------------

@channel_config_bp.route("/llm-config", methods=["GET"])
def get_llm_config():
    """Return the shared LLM config (api_key unmasked) for the Agent panel."""
    # _read_config() already deep-merges DEFAULT_CONFIG, so all fields are present.
    cfg = _read_config()
    api_key = _read_api_key()
    return jsonify(
        {field: cfg.get(field) for field in _LLM_FIELDS}
        | {
            "api_key": api_key,
            "codex_linked": bool(_read_codex_access_token()),
            "codex_account_id": _read_codex_account_id(),
        }
    )


@channel_config_bp.route("/llm-config", methods=["POST"])
def save_llm_config():
    """Save shared LLM config from either the Gateway panel or the Agent panel."""
    body = request.get_json(silent=True) or {}
    cfg = _read_config()
    for field in _LLM_FIELDS:
        if field not in body:
            continue
        val = body[field]
        cfg[field] = None if (val == "" and field in _LLM_NULLABLE) else val
    try:
        _write_config(cfg)
        api_key = body.get("api_key", "")
        if api_key and not _looks_masked(api_key):
            _write_api_key(api_key)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@channel_config_bp.route("/llm/test", methods=["POST"])
def test_llm_config():
    """Test LLM API key reachability. Body may override {api_key, endpoint}."""
    body = request.get_json(silent=True) or {}
    cfg = _read_config()
    endpoint = str(body.get("endpoint") or cfg.get("endpoint") or "").strip()
    if not endpoint:
        endpoint = "https://api.openai.com/v1"
    endpoint = endpoint.rstrip("/")
    api_key = _resolve_effective_api_key(endpoint, str(body.get("api_key") or "").strip())
    if not api_key:
        return jsonify({"ok": False, "error": "No API key configured"})
    try:
        resp = requests.get(
            f"{endpoint}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.ok:
            return jsonify({"ok": True})
        try:
            detail = resp.json().get("error", {}).get("message") or f"HTTP {resp.status_code}"
        except Exception:
            detail = f"HTTP {resp.status_code}"
        return jsonify({"ok": False, "error": detail})
    except requests.exceptions.ConnectionError as exc:
        return jsonify({"ok": False, "error": f"Connection error: {exc}"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


@channel_config_bp.route("/codex/oauth/start", methods=["POST"])
def codex_oauth_start():
    """Start Codex PKCE OAuth in a background thread; browser polls /status."""
    from omicverse.jarvis.openai_oauth import OpenAIOAuthManager  # type: ignore
    with _codex_oauth_lock:
        if _codex_oauth_state.get("status") == "pending":
            return jsonify({"ok": False, "error": "OAuth already in progress"})
        _codex_oauth_state.update({"status": "pending", "error": None, "access_token": None})

    auth_path = _auth_path()

    def _run() -> None:
        try:
            mgr = OpenAIOAuthManager(auth_path=auth_path)
            auth = mgr.login(open_browser=True, timeout_seconds=300)
            access_token = str((auth.get("tokens") or {}).get("access_token") or "").strip()
            if access_token:
                _write_api_key(access_token)
            with _codex_oauth_lock:
                _codex_oauth_state.update({"status": "success", "access_token": access_token})
        except Exception as exc:
            with _codex_oauth_lock:
                _codex_oauth_state.update({"status": "error", "error": str(exc)})

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True})


@channel_config_bp.route("/codex/oauth/status", methods=["GET"])
def codex_oauth_status():
    """Return current OAuth flow state plus stored Codex token info."""
    from omicverse.jarvis.openai_oauth import token_expired  # type: ignore
    with _codex_oauth_lock:
        state = dict(_codex_oauth_state)
    # Remove raw access_token from the response (security)
    state.pop("access_token", None)
    # Check stored auth for linked status
    auth_data: dict = {"linked": False, "expired": True, "account_id": ""}
    try:
        p = _auth_path()
        if p.exists():
            raw = json.loads(p.read_text())
            tokens = raw.get("tokens") or {}
            access = str(tokens.get("access_token") or "").strip()
            auth_data = {
                "linked": bool(access),
                "expired": token_expired(access) if access else True,
                "account_id": str(tokens.get("account_id") or ""),
            }
    except Exception:
        pass
    return jsonify({**state, **auth_data})


@channel_config_bp.route("/codex/oauth/import", methods=["POST"])
def codex_oauth_import():
    """Import existing Codex CLI auth from ~/.codex/auth.json."""
    from omicverse.jarvis.openai_oauth import OpenAIOAuthManager  # type: ignore
    try:
        mgr = OpenAIOAuthManager(auth_path=_auth_path())
        auth = mgr.import_codex_auth()
        if auth is None:
            return jsonify({"ok": False, "error": "No valid Codex auth found in ~/.codex/auth.json"})
        access_token = str((auth.get("tokens") or {}).get("access_token") or "").strip()
        if access_token:
            _write_api_key(access_token)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


@channel_config_bp.route("/config", methods=["GET"])
def get_config():
    cfg = _read_config()
    api_key = _read_api_key()

    # For secret fields: return empty string (not the masked value) so the
    # form inputs start blank. Use *_set booleans to show "already configured" hints.
    display = json.loads(json.dumps(cfg))  # deep copy
    _SECRET_FIELDS = [
        ("telegram", "token"),
        ("discord", "token"),
        ("wechat", "token"),
        ("feishu", "app_secret"),
        ("feishu", "verification_token"),
        ("feishu", "encrypt_key"),
        ("qq", "client_secret"),
    ]
    secrets_set: dict = {}
    for section, field in _SECRET_FIELDS:
        real_val = display.get(section, {}).get(field) or ""
        key = f"{section}__{field}"
        secrets_set[key] = bool(real_val)
        if real_val:
            display.setdefault(section, {})[field] = ""  # blank out — don't send to browser

    return jsonify({
        "config": display,
        "secrets_set": secrets_set,          # {section__field: bool}
        "api_key_masked": _mask(api_key),
        "api_key_set": bool(api_key),
        "processes": list_channel_states(),
        "config_path": str(_config_path()),
    })


@channel_config_bp.route("/config", methods=["POST"])
def save_config():
    body = request.get_json(silent=True) or {}
    cfg = body.get("config")
    api_key = body.get("api_key", "")
    if not isinstance(cfg, dict):
        return jsonify({"error": "config must be an object"}), 400
    try:
        _write_config(cfg)
        if api_key:
            _write_api_key(api_key)
        return jsonify({"ok": True, "path": str(_config_path())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@channel_config_bp.route("/processes", methods=["GET"])
def get_processes():
    return jsonify({"processes": list_channel_states()})


@channel_config_bp.route("/<channel>/test", methods=["POST"])
def test_channel(channel: str):
    """Test connectivity for a channel. Accepts inline credentials in body."""
    body = request.get_json(silent=True) or {}
    cfg = _read_config()

    try:
        if channel == "telegram":
            token = body.get("token") or cfg.get("telegram", {}).get("token") or ""
            if not token:
                return jsonify({"ok": False, "error": "No bot token configured"})
            resp = requests.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=8,
            )
            data = resp.json()
            if data.get("ok"):
                bot = data["result"]
                return jsonify({
                    "ok": True,
                    "message": f"✓ Bot @{bot.get('username')} ({bot.get('first_name')}) — connection OK",
                })
            return jsonify({"ok": False, "error": data.get("description", "Unknown Telegram error")})

        elif channel == "discord":
            token = body.get("token") or cfg.get("discord", {}).get("token") or ""
            if not token:
                return jsonify({"ok": False, "error": "No bot token configured"})
            resp = requests.get(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bot {token}"},
                timeout=8,
            )
            data = resp.json()
            if resp.ok and data.get("id"):
                return jsonify({
                    "ok": True,
                    "message": f"✓ Discord bot {data.get('username')}#{data.get('discriminator', '0')} — connection OK",
                })
            return jsonify({"ok": False, "error": data.get("message", "Discord auth failed")})

        elif channel == "wechat":
            token = body.get("token") or cfg.get("wechat", {}).get("token") or ""
            base_url = body.get("base_url") or cfg.get("wechat", {}).get("base_url") or "https://ilinkai.weixin.qq.com"
            if not token:
                return jsonify({"ok": False, "error": "No WeChat token configured"})
            payload = {
                "get_updates_buf": "",
                "base_info": {"channel_version": "gateway-test"},
            }
            body_text = json.dumps(payload, ensure_ascii=False)
            headers = {
                "Content-Type": "application/json",
                "AuthorizationType": "ilink_bot_token",
                "Authorization": f"Bearer {token}",
                "X-WECHAT-UIN": "MTIzNDU2",
                "Content-Length": str(len(body_text.encode("utf-8"))),
            }
            try:
                resp = requests.post(
                    f"{str(base_url).rstrip('/')}/ilink/bot/getupdates",
                    data=body_text.encode("utf-8"),
                    headers=headers,
                    timeout=(5, 2),
                )
                data = resp.json()
                if resp.ok and (data.get("ret") in (None, 0)) and (data.get("errcode") in (None, 0)):
                    return jsonify({
                        "ok": True,
                        "message": "✓ WeChat iLink auth OK",
                    })
                return jsonify({"ok": False, "error": data.get("errmsg", "WeChat auth failed")})
            except requests.exceptions.ReadTimeout:
                return jsonify({
                    "ok": True,
                    "message": "✓ WeChat endpoint reachable — long-poll pending, start the channel to verify inbound events",
                })

        elif channel == "feishu":
            app_id = body.get("app_id") or cfg.get("feishu", {}).get("app_id") or ""
            app_secret = body.get("app_secret") or cfg.get("feishu", {}).get("app_secret") or ""
            if not app_id or not app_secret:
                return jsonify({"ok": False, "error": "app_id and app_secret required"})
            resp = requests.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": app_id, "app_secret": app_secret},
                timeout=8,
            )
            data = resp.json()
            if data.get("code") == 0:
                return jsonify({
                    "ok": True,
                    "message": f"✓ Feishu auth OK — token expires in {data.get('expire', '?')}s",
                })
            return jsonify({"ok": False, "error": data.get("msg", "Feishu auth failed")})

        elif channel == "qq":
            app_id = body.get("app_id") or cfg.get("qq", {}).get("app_id") or ""
            client_secret = body.get("client_secret") or cfg.get("qq", {}).get("client_secret") or ""
            if not app_id or not client_secret:
                return jsonify({"ok": False, "error": "app_id and client_secret required"})
            resp = requests.post(
                "https://bots.qq.com/app/getAppAccessToken",
                json={"appId": app_id, "clientSecret": client_secret},
                timeout=8,
            )
            data = resp.json()
            if data.get("access_token"):
                return jsonify({
                    "ok": True,
                    "message": f"✓ QQ Bot auth OK — expires in {data.get('expiresIn', '?')}s",
                })
            return jsonify({"ok": False, "error": data.get("message", "QQ auth failed")})

        elif channel == "imessage":
            cli = body.get("cli_path") or cfg.get("imessage", {}).get("cli_path") or "imsg"
            db = os.path.expanduser(
                body.get("db_path") or cfg.get("imessage", {}).get("db_path") or "~/Library/Messages/chat.db"
            )
            found = shutil.which(cli)
            if found:
                db_ok = os.path.exists(db)
                msg = f"✓ CLI found at {found}"
                if not db_ok:
                    msg += f" | ⚠ DB not found at {db}"
                return jsonify({"ok": True, "message": msg})
            return jsonify({"ok": False, "error": f"CLI '{cli}' not found in PATH"})

        else:
            return jsonify({"ok": False, "error": f"Unknown channel: {channel}"}), 400

    except requests.exceptions.ConnectionError:
        return jsonify({"ok": False, "error": "Network error — check your internet connection"})
    except requests.exceptions.Timeout:
        return jsonify({"ok": False, "error": "Request timed out"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@channel_config_bp.route("/wechat/login/qr", methods=["POST"])
def wechat_login_qr():
    body = request.get_json(silent=True) or {}
    cfg = _read_config()
    base_url = _resolve_wechat_base_url(body, cfg)
    try:
        resp = requests.get(
            f"{base_url}/ilink/bot/get_bot_qrcode",
            params={"bot_type": "3"},
            headers=_ilink_get_headers(),
            timeout=(10, 30),
        )
        resp.raise_for_status()
        data = resp.json()
        # qrcode_img_content is a URL/string that must be encoded *into* a QR
        # code image — it is NOT already base64 PNG data.
        qr_url = data.get("qrcode_img_content") or ""
        img_src = _make_qr_data_uri(qr_url)
        return jsonify({
            "ok": True,
            "qrcode": data.get("qrcode") or "",
            "image": img_src,
            "message": data.get("message"),
        })
    except requests.exceptions.RequestException as exc:
        return jsonify({"ok": False, "error": f"QR request failed: {exc}"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


@channel_config_bp.route("/wechat/login/status", methods=["GET"])
def wechat_login_status():
    qrcode = request.args.get("qrcode", "")
    if not qrcode:
        return jsonify({"ok": False, "error": "qrcode is required"}), 400
    cfg = _read_config()
    base_url = _resolve_wechat_base_url(request.args, cfg)
    try:
        resp = requests.get(
            f"{base_url}/ilink/bot/get_qrcode_status",
            params={"qrcode": qrcode},
            headers=_ilink_get_headers(),
            timeout=(10, 40),
        )
        resp.raise_for_status()
        data = resp.json()
        status = str(data.get("status") or "").lower()
        if status == "confirmed":
            return jsonify({
                "ok": True,
                "status": "confirmed",
                "bot_token": data.get("bot_token"),
                "baseurl": data.get("baseurl"),
            })
        return jsonify({
            "ok": True,
            "status": status or "wait",
            "message": data.get("message", ""),
        })
    except requests.exceptions.ReadTimeout:
        # Long-poll held the connection; treat as "still waiting".
        return jsonify({"ok": True, "status": "wait"})
    except requests.exceptions.RequestException as exc:
        return jsonify({"ok": False, "error": f"Status request failed: {exc}"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


@channel_config_bp.route("/<channel>/start", methods=["POST"])
def start_channel(channel: str):
    """Start a channel bot in-process when supported, else as a subprocess."""
    if channel not in ("telegram", "discord", "wechat", "feishu", "qq", "imessage"):
        return jsonify({"ok": False, "error": f"Unknown channel: {channel}"}), 400

    cfg = _read_config()
    api_key = _read_api_key()
    manager = _get_channel_manager()
    if manager is not None and manager.supports(channel):
        return jsonify(manager.start_channel(channel, cfg=cfg, api_key=api_key, source="manual"))

    with _PROCESS_LOCK:
        _refresh_channel_states_locked()
        existing = _PROCESSES.get(channel)
        if existing and existing.poll() is None:
            return jsonify({"ok": False, "error": f"{channel} is already running (pid={existing.pid})"})

    result = _start_channel_process(channel, cfg=cfg, api_key=api_key, source="manual")
    return jsonify(result)


@channel_config_bp.route("/<channel>/stop", methods=["POST"])
def stop_channel(channel: str):
    manager = _get_channel_manager()
    if manager is not None and manager.supports(channel):
        return jsonify(manager.stop_channel(channel))
    with _PROCESS_LOCK:
        proc = _PROCESSES.get(channel)
    if proc is None or proc.poll() is not None:
        with _PROCESS_LOCK:
            _PROCESSES.pop(channel, None)
        _set_channel_state(channel, status="stopped", running=False, desired_state="stopped")
        return jsonify({"ok": False, "error": f"{channel} is not running"})
    try:
        result = _stop_channel_process(channel, proc)
        return jsonify({"ok": True, "message": f"{channel} stopped", **result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@channel_config_bp.route("/<channel>/logs", methods=["GET"])
def get_channel_logs(channel: str):
    """Return buffered logs from the active channel runner."""
    manager = _get_channel_manager()
    if manager is not None and manager.supports(channel):
        states = {item.get("channel"): item for item in list_channel_states()}
        state = states.get(channel, {})
        return jsonify({
            "channel": channel,
            "running": bool(state.get("running", False)),
            "logs": manager.get_logs(channel),
            "mode": "thread",
        })
    with _PROCESS_LOCK:
        proc = _PROCESSES.get(channel)
    logs = _get_log_buffer(channel)
    if proc is None:
        return jsonify({"channel": channel, "running": False, "logs": logs})
    running = proc.poll() is None
    return jsonify({
        "channel": channel,
        "running": running,
        "pid": proc.pid,
        "logs": logs,
    })
