from __future__ import annotations

import collections
import logging
import threading
from typing import Any, Optional


_SUPPORTED_CHANNELS = ("telegram", "feishu", "qq", "imessage")
_LOG_BUF_SIZE = 200


def _channel_configured(channel: str, cfg: dict) -> bool:
    if channel == "telegram":
        return bool((cfg.get("telegram") or {}).get("token"))
    if channel == "feishu":
        fc = cfg.get("feishu") or {}
        return bool(fc.get("app_id") and fc.get("app_secret"))
    if channel == "qq":
        qc = cfg.get("qq") or {}
        return bool(qc.get("app_id") and qc.get("client_secret"))
    if channel == "imessage":
        ic = cfg.get("imessage") or {}
        return bool(ic.get("cli_path") or ic.get("db_path"))
    return False


class _ChannelLogHandler(logging.Handler):
    def __init__(self, channel: str, buffer: collections.deque[str]) -> None:
        super().__init__()
        self._channel = channel
        self._buffer = buffer
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        name = record.name or ""
        if self._channel == "qq" and not name.startswith("omicverse.jarvis.qq"):
            return
        if self._channel == "telegram" and not name.startswith("omicverse.jarvis"):
            return
        if self._channel == "feishu" and not name.startswith("omicverse.jarvis.feishu"):
            return
        if self._channel == "imessage" and not name.startswith("omicverse.jarvis.imessage"):
            return
        try:
            self._buffer.append(self.format(record) + "\n")
        except Exception:
            pass


class InProcessChannelManager:
    """Run configured channels inside the gateway process."""

    def __init__(self, session_manager: Any) -> None:
        self._sm = session_manager
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}
        self._states: dict[str, dict[str, Any]] = {}
        self._logs: dict[str, collections.deque[str]] = {}
        self._handlers: dict[str, logging.Handler] = {}

    def supports(self, channel: str) -> bool:
        return channel in _SUPPORTED_CHANNELS

    def list_states(self, cfg: dict) -> list[dict]:
        snapshot: list[dict] = []
        with self._lock:
            for channel in _SUPPORTED_CHANNELS:
                configured = _channel_configured(channel, cfg)
                state = dict(self._states.get(channel, {}))
                if not state:
                    state = {
                        "channel": channel,
                        "status": "stopped" if configured else "not_configured",
                        "running": False,
                    }
                state["configured"] = configured
                state["can_start"] = configured and state.get("status") not in {"running", "starting", "not_configured"}
                state["mode"] = "thread"
                snapshot.append(state)
        return snapshot

    def auto_start_configured(self, cfg: dict, api_key: Optional[str] = None) -> list[dict]:
        results: list[dict] = []
        for channel in _SUPPORTED_CHANNELS:
            if _channel_configured(channel, cfg):
                results.append(self.start_channel(channel, cfg=cfg, api_key=api_key, source="gateway-startup"))
        return results

    def start_channel(
        self,
        channel: str,
        *,
        cfg: dict,
        api_key: Optional[str] = None,
        source: str = "manual",
    ) -> dict:
        if not self.supports(channel):
            return {"ok": False, "error": f"{channel} is not supported by the in-process manager"}
        if not _channel_configured(channel, cfg):
            self._set_state(channel, status="failed", running=False, error=f"{channel} is not configured")
            return {"ok": False, "error": f"{channel} is not configured"}

        with self._lock:
            existing = self._threads.get(channel)
            if existing and existing.is_alive():
                state = self._states.get(channel, {})
                return {"ok": False, "error": f"{channel} is already running", **({"thread_name": state.get('thread_name')} if state else {})}

            stop_event = threading.Event()
            log_buffer = collections.deque(maxlen=_LOG_BUF_SIZE)
            self._logs[channel] = log_buffer
            handler = _ChannelLogHandler(channel, log_buffer)
            logging.getLogger().addHandler(handler)
            self._handlers[channel] = handler

            def _runner() -> None:
                try:
                    self._run_channel(channel, cfg, stop_event)
                    final_status = "stopped" if stop_event.is_set() else "failed"
                    self._set_state(channel, status=final_status, running=False)
                except Exception as exc:
                    log_buffer.append(f"in-process {channel} failed: {exc}\n")
                    self._set_state(channel, status="failed", running=False, error=str(exc))
                finally:
                    logging.getLogger().removeHandler(handler)
                    with self._lock:
                        self._threads.pop(channel, None)
                        self._stop_events.pop(channel, None)
                        self._handlers.pop(channel, None)

            thread = threading.Thread(target=_runner, daemon=True, name=f"gateway-{channel}")
            self._threads[channel] = thread
            self._stop_events[channel] = stop_event
            self._states[channel] = {
                "channel": channel,
                "status": "running",
                "running": True,
                "configured": True,
                "desired_state": "running",
                "source": source,
                "mode": "thread",
                "thread_name": thread.name,
            }
            log_buffer.append(f"[in-process start] channel={channel} source={source}\n")
            thread.start()
            return {"ok": True, "message": f"Started {channel} in-process", "thread_name": thread.name}

    def _run_channel(self, channel: str, cfg: dict, stop_event: threading.Event) -> None:
        if channel == "telegram":
            from omicverse.jarvis.channels.telegram import AccessControl, run_bot

            tc = dict(cfg.get("telegram") or {})
            run_bot(
                token=str(tc.get("token") or ""),
                session_manager=self._sm,
                access_control=AccessControl([str(x) for x in (tc.get("allowed_users") or [])]),
                verbose=False,
                stop_event=stop_event,
            )
            return

        if channel == "feishu":
            from omicverse.jarvis.channels.feishu import run_feishu_bot, run_feishu_ws_bot

            fc = dict(cfg.get("feishu") or {})
            common = dict(
                app_id=str(fc.get("app_id") or ""),
                app_secret=str(fc.get("app_secret") or ""),
                session_manager=self._sm,
                verification_token=fc.get("verification_token") or None,
                encrypt_key=fc.get("encrypt_key") or None,
                stop_event=stop_event,
            )
            if str(fc.get("connection_mode") or "websocket").lower() == "webhook":
                run_feishu_bot(
                    **common,
                    host=str(fc.get("host") or "0.0.0.0"),
                    port=int(fc.get("port") or 8080),
                    path=str(fc.get("path") or "/feishu/events"),
                )
            else:
                run_feishu_ws_bot(**common)
            return

        if channel == "qq":
            from omicverse.jarvis.channels.qq import run_qq_bot

            qc = dict(cfg.get("qq") or {})
            run_qq_bot(
                app_id=str(qc.get("app_id") or ""),
                client_secret=str(qc.get("client_secret") or ""),
                session_manager=self._sm,
                markdown=bool(qc.get("markdown")),
                image_host=qc.get("image_host") or None,
                image_server_port=int(qc.get("image_server_port") or 8081),
                stop_event=stop_event,
            )
            return

        if channel == "imessage":
            from omicverse.jarvis.channels.imessage import run_imessage_bot

            ic = dict(cfg.get("imessage") or {})
            run_imessage_bot(
                session_manager=self._sm,
                cli_path=str(ic.get("cli_path") or "imsg"),
                db_path=ic.get("db_path") or None,
                include_attachments=bool(ic.get("include_attachments")),
                stop_event=stop_event,
            )
            return

        raise RuntimeError(f"Unsupported channel: {channel}")

    def stop_channel(self, channel: str) -> dict:
        with self._lock:
            stop_event = self._stop_events.get(channel)
            thread = self._threads.get(channel)
        if stop_event is None or thread is None or not thread.is_alive():
            self._set_state(channel, status="stopped", running=False, desired_state="stopped")
            return {"ok": False, "error": f"{channel} is not running"}
        stop_event.set()
        self._set_state(channel, status="stopped", running=False, desired_state="stopped")
        return {"ok": True, "message": f"Stopping {channel}", "thread_name": thread.name}

    def get_logs(self, channel: str) -> str:
        with self._lock:
            buf = self._logs.get(channel)
            if not buf:
                return ""
            return "".join(buf)

    def stop_all(self) -> list[dict]:
        return [self.stop_channel(channel) for channel in _SUPPORTED_CHANNELS]

    def _set_state(self, channel: str, **state: Any) -> None:
        with self._lock:
            current = dict(self._states.get(channel, {}))
            current.update(state)
            current["channel"] = channel
            current["mode"] = "thread"
            self._states[channel] = current
