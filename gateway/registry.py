"""
GatewayChannelRegistry — stable channel→AgentSession mapping.

Maps any external channel (telegram, feishu, qq, imessage, …) to an
``AgentSession`` in the web ``SessionManager`` using a deterministic
SHA-1 derived session ID — the same approach used in jarvis's
``gateway/routing.py``.

Usage::

    registry = GatewayChannelRegistry()
    session = registry.get_or_create_session(
        channel="telegram",
        scope_type="dm",
        scope_id="123456789",
        session_manager=sm,
    )
"""

import hashlib
import logging
import threading
from typing import Optional

logger = logging.getLogger("omicverse_web.gateway.registry")


def _stable_uid(channel: str, scope_type: str, scope_id: str) -> str:
    """Return a stable 16-char hex session ID derived from the three keys.

    The hash is deterministic: the same ``(channel, scope_type, scope_id)``
    triple always produces the same session ID, even across restarts.
    """
    raw = f"{channel}:{scope_type}:{scope_id}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


class SessionKey:
    """Immutable descriptor for a single channel scope.

    Parameters
    ----------
    channel:
        Channel name, e.g. ``"telegram"``, ``"web"``, ``"feishu"``.
    scope_type:
        Granularity of the scope: ``"dm"`` | ``"group"`` | ``"session"``.
    scope_id:
        Channel-specific unique identifier (e.g. Telegram ``chat_id``,
        browser session cookie, …).
    """

    __slots__ = ("channel", "scope_type", "scope_id")

    def __init__(self, channel: str, scope_type: str, scope_id: str):
        self.channel = channel
        self.scope_type = scope_type
        self.scope_id = scope_id

    @property
    def session_id(self) -> str:
        return _stable_uid(self.channel, self.scope_type, self.scope_id)

    def __repr__(self) -> str:
        return (
            f"SessionKey(channel={self.channel!r}, "
            f"scope_type={self.scope_type!r}, "
            f"scope_id={self.scope_id!r}, "
            f"session_id={self.session_id!r})"
        )


class GatewayChannelRegistry:
    """Registry that maps channel sessions to ``AgentSession`` objects.

    All channels (web browser tabs, Telegram DMs, Feishu conversations, …)
    share the same ``SessionManager`` instance.  The registry ensures that a
    stable ``session_id`` is derived from each ``(channel, scope_type,
    scope_id)`` triple so sessions survive bot restarts.
    """

    def __init__(self):
        self._keys: dict[str, SessionKey] = {}  # session_id → SessionKey
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def get_or_create_session(
        self,
        channel: str,
        scope_type: str,
        scope_id: str,
        session_manager,
        base_adata=None,
    ):
        """Return (or lazily create) the ``AgentSession`` for this channel scope.

        Parameters
        ----------
        channel:
            E.g. ``"telegram"`` or ``"web"``.
        scope_type:
            E.g. ``"dm"``, ``"group"``, ``"session"``.
        scope_id:
            Channel-specific unique ID (chat_id, browser cookie, …).
        session_manager:
            Web ``SessionManager`` instance.
        base_adata:
            Optional AnnData object to seed a new session with.
        """
        key = SessionKey(channel, scope_type, scope_id)
        sid = key.session_id
        with self._lock:
            if sid not in self._keys:
                self._keys[sid] = key
                logger.info(
                    "GatewayChannelRegistry: registered %s → session_id=%s",
                    key,
                    sid,
                )
        session = session_manager.get_or_create(sid, base_adata=base_adata)
        return session

    def session_key(self, session_id: str) -> Optional[SessionKey]:
        """Look up the ``SessionKey`` for a known *session_id*."""
        with self._lock:
            return self._keys.get(session_id)

    def list_channels(self) -> list[dict]:
        """Return a snapshot of all registered channel mappings."""
        with self._lock:
            return [
                {
                    "session_id": sid,
                    "channel": key.channel,
                    "scope_type": key.scope_type,
                    "scope_id": key.scope_id,
                }
                for sid, key in self._keys.items()
            ]

    # ------------------------------------------------------------------
    # Convenience constructors for each channel type
    # ------------------------------------------------------------------

    def web_session(self, browser_session_id: str, session_manager, base_adata=None):
        """Create/get a session for a web browser session."""
        return self.get_or_create_session(
            "web", "session", browser_session_id, session_manager, base_adata
        )

    def telegram_session(self, chat_id: str, session_manager, base_adata=None):
        return self.get_or_create_session(
            "telegram", "dm", chat_id, session_manager, base_adata
        )

    def feishu_session(self, chat_id: str, session_manager, base_adata=None):
        return self.get_or_create_session(
            "feishu", "dm", chat_id, session_manager, base_adata
        )

    def qq_session(self, chat_id: str, session_manager, base_adata=None):
        return self.get_or_create_session(
            "qq", "dm", chat_id, session_manager, base_adata
        )
