"""
WebChannelAdapter — delivers channel bot turns into web AgentSessions.

When a channel bot (Telegram, Feishu, QQ, …) finishes processing a user
message, it can call ``WebChannelAdapter.deliver()`` to write the turn
into the shared ``AgentSession`` so that the web UI reflects the
conversation in real time.

Usage (from a bot handler, after analysis is complete)::

    from gateway.channel_adapter import WebChannelAdapter
    from gateway.registry import GatewayChannelRegistry
    from gateway.context import ChannelContextBridge
    from services.agent_session_service import session_manager

    registry = GatewayChannelRegistry()
    bridge   = ChannelContextBridge(session_manager)
    adapter  = WebChannelAdapter(
        session_manager=session_manager,
        registry=registry,
        context_bridge=bridge,
    )

    # In the bot message handler:
    session = adapter.get_or_create_session(
        channel="telegram",
        scope_type="dm",
        scope_id=str(chat_id),
    )
    adapter.deliver(
        session_id=session.session_id,
        channel="telegram",
        user_text=user_message,
        assistant_text=bot_reply,
    )
"""

import logging
from typing import Any, Optional

logger = logging.getLogger("omicverse_web.gateway.channel_adapter")


class WebChannelAdapter:
    """Bridges channel bot output into web ``AgentSession`` history.

    Parameters
    ----------
    session_manager:
        Web ``SessionManager`` instance.
    registry:
        ``GatewayChannelRegistry`` for stable channel→session mapping.
    context_bridge:
        ``ChannelContextBridge`` for history / adata I/O.
    """

    def __init__(self, session_manager, registry, context_bridge):
        self._sm = session_manager
        self._registry = registry
        self._bridge = context_bridge

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def get_or_create_session(
        self,
        channel: str,
        scope_type: str,
        scope_id: str,
        base_adata: Any = None,
    ):
        """Return (or create) the ``AgentSession`` for this channel scope."""
        return self._registry.get_or_create_session(
            channel=channel,
            scope_type=scope_type,
            scope_id=scope_id,
            session_manager=self._sm,
            base_adata=base_adata,
        )

    # ------------------------------------------------------------------
    # Turn delivery
    # ------------------------------------------------------------------

    def deliver(
        self,
        session_id: str,
        channel: str,
        user_text: str,
        assistant_text: str,
        turn_id: str = "",
        adata: Any = None,
    ) -> None:
        """Write a completed conversation turn into the shared session.

        Parameters
        ----------
        session_id:
            Target ``AgentSession`` (use ``get_or_create_session`` first).
        channel:
            Source channel name (e.g. ``"telegram"``).
        user_text:
            The user's original message.
        assistant_text:
            The bot's reply.
        turn_id:
            Explicit turn ID; auto-generated if empty.
        adata:
            If provided, commit this updated AnnData into the session.
        """
        self._bridge.write_turn(
            session_id=session_id,
            user_text=user_text,
            assistant_text=assistant_text,
            channel=channel,
            turn_id=turn_id,
        )
        if adata is not None:
            self._bridge.commit_adata(session_id, adata)
        logger.debug(
            "WebChannelAdapter.deliver: session=%s channel=%s has_adata=%s",
            session_id,
            channel,
            adata is not None,
        )

    # ------------------------------------------------------------------
    # Convenience: channel-specific helpers
    # ------------------------------------------------------------------

    def telegram_deliver(
        self,
        chat_id: str,
        user_text: str,
        assistant_text: str,
        adata: Any = None,
        turn_id: str = "",
    ) -> str:
        """Deliver a Telegram turn.  Returns the stable ``session_id``."""
        session = self.get_or_create_session("telegram", "dm", str(chat_id))
        self.deliver(
            session_id=session.session_id,
            channel="telegram",
            user_text=user_text,
            assistant_text=assistant_text,
            turn_id=turn_id,
            adata=adata,
        )
        return session.session_id

    def feishu_deliver(
        self,
        chat_id: str,
        user_text: str,
        assistant_text: str,
        adata: Any = None,
        turn_id: str = "",
    ) -> str:
        """Deliver a Feishu turn.  Returns the stable ``session_id``."""
        session = self.get_or_create_session("feishu", "dm", str(chat_id))
        self.deliver(
            session_id=session.session_id,
            channel="feishu",
            user_text=user_text,
            assistant_text=assistant_text,
            turn_id=turn_id,
            adata=adata,
        )
        return session.session_id
