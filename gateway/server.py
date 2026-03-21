"""
GatewayServer — start the OmicVerse web UI in a background thread.

Usage (from a channel bot or CLI):

    from gateway.server import GatewayServer

    gw = GatewayServer()
    thread, url = gw.start(host="127.0.0.1", port=0, session_manager=sm)
    # url => "http://127.0.0.1:5050"
    gw.open_browser(url)          # optional
"""

import os
import sys
import atexit
import socket
import signal
import threading
import webbrowser
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("omicclaw.gateway.server")
_SHUTDOWN_HOOKS_REGISTERED = False
_INPROCESS_CHANNEL_MANAGER = None


def _register_shutdown_hooks() -> None:
    """Ensure tracked channel subprocesses are stopped when the gateway exits."""
    global _SHUTDOWN_HOOKS_REGISTERED
    if _SHUTDOWN_HOOKS_REGISTERED:
        return
    _SHUTDOWN_HOOKS_REGISTERED = True

    def _cleanup() -> None:
        try:
            from gateway.channel_config_routes import stop_all_channel_processes

            stop_all_channel_processes()
        except Exception:
            logger.exception("GatewayServer: failed to stop channel subprocesses")
        manager = _INPROCESS_CHANNEL_MANAGER
        if manager is not None:
            try:
                manager.stop_all()
            except Exception:
                logger.exception("GatewayServer: failed to stop in-process channels")

    atexit.register(_cleanup)

    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            prev_handler = signal.getsignal(sig)

            def _handler(signum, frame, *, _prev=prev_handler) -> None:  # type: ignore[override]
                _cleanup()
                if callable(_prev) and _prev not in {signal.SIG_DFL, signal.SIG_IGN}:
                    _prev(signum, frame)
                raise SystemExit(0)

            try:
                signal.signal(sig, _handler)
            except Exception:
                logger.debug("GatewayServer: could not install %s handler", sig, exc_info=True)


def _attach_shared_adata_sync(session_manager, web_state) -> None:
    """Wire shared AnnData updates between the web state and the session manager.

    The reverse sync hook is optional because some callers may pass a session
    manager implementation that only supports ``set_shared_adata``.
    """
    try:
        web_attach = getattr(web_state, "attach_session_manager", None)
        if callable(web_attach):
            web_attach(session_manager)
    except Exception:
        logger.exception("GatewayServer: failed to attach web session manager")
        return

    sync_handler = getattr(session_manager, "set_adata_sync_handler", None)
    if not callable(sync_handler):
        logger.debug(
            "GatewayServer: session manager does not expose set_adata_sync_handler; "
            "skipping reverse AnnData sync",
        )
        return

    existing_handler = getattr(session_manager, "_adata_sync_handler", None)

    def _combined_handler(session_id, adata) -> None:  # noqa: ANN001
        if callable(existing_handler):
            existing_handler(session_id, adata)
        setattr(web_state, "current_adata", adata)

    try:
        sync_handler(_combined_handler)
    except Exception:
        logger.exception("GatewayServer: failed to attach shared AnnData handler")


def get_available_port(start_port: int = 5050) -> Optional[int]:
    """Return the first free TCP port starting from *start_port*."""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue
    return None


class GatewayServer:
    """Manages a Flask web server that runs in a daemon thread.

    Parameters
    ----------
    web_root:
        Directory that contains ``app.py``.  Defaults to the parent of this
        file (i.e. the omicclaw project root).
    """

    def __init__(self, web_root: Optional[str] = None):
        self._web_root = Path(web_root or Path(__file__).parent.parent).resolve()
        self._thread: Optional[threading.Thread] = None
        self._url: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        session_manager=None,
        channel_registry=None,
        channel_manager=None,
        memory_db_path: Optional[str] = None,
        channels: Optional[list] = None,
        auto_start_channels: bool = False,
        jarvis_config_path: Optional[str] = None,
        debug: bool = False,
    ) -> Tuple[threading.Thread, str]:
        """Start the Flask app in a background daemon thread.

        Parameters
        ----------
        host:
            Bind address (default ``127.0.0.1``).
        port:
            Port number.  If 0 or omitted, auto-select from 5050.
        session_manager:
            A ``SessionManager`` instance to inject into the Flask app as
            ``app.config["GATEWAY_SESSION_MANAGER"]``.
        debug:
            Enable Flask debug mode (not recommended in gateway mode).

        Returns
        -------
        (thread, url)
            Background thread and the base URL where the UI is accessible.
        """
        if self._thread is not None and self._thread.is_alive():
            logger.warning("GatewayServer.start() called while already running")
            return self._thread, self._url  # type: ignore[return-value]

        global _INPROCESS_CHANNEL_MANAGER
        _INPROCESS_CHANNEL_MANAGER = channel_manager
        _register_shutdown_hooks()

        bind_port = port if port > 0 else get_available_port()
        if bind_port is None:
            raise RuntimeError("GatewayServer: no available port found in range 5050-5150")

        self._url = f"http://localhost:{bind_port}"

        def _run():
            # Ensure the web root is on sys.path so ``app.py`` can import its
            # sibling packages (routes, services, utils, …).
            web_root_str = str(self._web_root)
            if web_root_str not in sys.path:
                sys.path.insert(0, web_root_str)

            os.environ.setdefault("PORT", str(bind_port))

            from app import app as flask_app, state as web_state  # type: ignore[import]

            if session_manager is not None:
                flask_app.config["GATEWAY_SESSION_MANAGER"] = session_manager
                try:
                    _attach_shared_adata_sync(session_manager, web_state)
                except Exception:
                    logger.exception("GatewayServer: failed to attach shared AnnData handler")
            if channel_registry is not None:
                flask_app.config["GATEWAY_CHANNEL_REGISTRY"] = channel_registry
            if channel_manager is not None:
                flask_app.config["GATEWAY_CHANNEL_MANAGER"] = channel_manager
            if memory_db_path is not None:
                flask_app.config["GATEWAY_MEMORY_DB_PATH"] = memory_db_path
            if channels is not None:
                flask_app.config["GATEWAY_ACTIVE_CHANNELS"] = list(channels)
            if jarvis_config_path is not None:
                flask_app.config["GATEWAY_JARVIS_CONFIG_PATH"] = jarvis_config_path

            if auto_start_channels:
                try:
                    from gateway.channel_config_routes import auto_start_configured_channels

                    with flask_app.app_context():
                        auto_start_configured_channels()
                except Exception:
                    logger.exception("GatewayServer: auto-starting configured channels failed")

            flask_app.run(
                host=host,
                port=bind_port,
                debug=debug,
                use_reloader=False,
                threaded=True,
            )

        self._thread = threading.Thread(target=_run, daemon=True, name="gateway-web")
        self._thread.start()
        logger.info("GatewayServer started on %s (thread: %s)", self._url, self._thread.name)
        return self._thread, self._url

    def open_browser(self, url: Optional[str] = None) -> None:
        """Open *url* (or the last started URL) in the default browser."""
        target = url or self._url
        if not target:
            logger.warning("GatewayServer.open_browser(): no URL to open")
            return
        webbrowser.open(target)
        logger.info("GatewayServer: opened browser at %s", target)

    @property
    def url(self) -> Optional[str]:
        """Base URL of the running server, or *None* if not started."""
        return self._url

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
