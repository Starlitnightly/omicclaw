"""
ChannelContextBridge — cross-channel history / adata read-write.

Provides a thin façade over ``SessionManager`` so that channel adapters
(Telegram bot, Feishu bot, …) can write conversation turns and commit
adata back into the web session without importing Flask directly.

Usage::

    bridge = ChannelContextBridge(session_manager=sm)

    # After a bot turn completes:
    bridge.write_turn(session_id, user_text="cluster the data", assistant_text="Done!")

    # Commit mutated adata:
    bridge.commit_adata(session_id, new_adata=adata)

    # Read back:
    history = bridge.get_history(session_id)
    adata   = bridge.get_adata(session_id)
"""

import logging
import time
import uuid
from typing import Any, Optional

logger = logging.getLogger("omicclaw.gateway.context")


class ChannelContextBridge:
    """Thin facade for cross-channel session context I/O.

    Parameters
    ----------
    session_manager:
        Web ``SessionManager`` instance (from
        ``services.agent_session_service``).
    workspace_manager:
        Optional ``WorkspaceManager`` instance.  When provided, every call to
        ``write_turn`` / ``sync_from_channel`` automatically persists the
        session history to disk so channel conversations survive server
        restarts and appear in the Agent chat sidebar.
    """

    def __init__(self, session_manager, workspace_manager=None):
        self._sm = session_manager
        self._wm = workspace_manager

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def write_turn(
        self,
        session_id: str,
        user_text: str,
        assistant_text: str,
        channel: str = "",
        turn_id: str = "",
    ) -> None:
        """Append a completed (user, assistant) turn to the session history.

        Parameters
        ----------
        session_id:
            Target ``AgentSession.session_id``.
        user_text:
            The user's message.
        assistant_text:
            The assistant's reply.
        channel:
            Optional channel tag embedded in the message metadata.
        turn_id:
            Explicit turn ID; auto-generated if empty.
        """
        session = self._sm.get_or_create(session_id)
        tid = turn_id or f"turn_{uuid.uuid4().hex[:8]}"

        # Prepend a channel marker to the user message when channel is set
        effective_user = f"[{channel}] {user_text}" if channel else user_text
        session.add_message("user", effective_user, turn_id=tid)
        session.add_message("assistant", assistant_text, turn_id=tid)
        logger.debug(
            "ChannelContextBridge.write_turn: session=%s channel=%s turn_id=%s",
            session_id,
            channel,
            tid,
        )

        # Persist to workspace so the conversation survives restarts and
        # appears in the Agent chat sidebar.
        if self._wm is not None:
            try:
                ch_label = channel or ""
                # Auto-title: use channel name + truncated user text
                auto_title = (f"[{ch_label}] " if ch_label else "") + user_text[:20]
                existing_meta = self._wm.get_meta(session_id)
                if existing_meta is None:
                    self._wm.get_or_create(session_id, title=auto_title)
                    session.workspace_dir = str(self._wm.workspace_dir(session_id))
                    session.title = auto_title
                self._wm.save_history(session_id, session.get_history_dicts())
                self._wm.touch(session_id)
            except Exception:
                logger.exception("ChannelContextBridge.write_turn: workspace persist failed")

    def get_history(self, session_id: str) -> list[dict]:
        """Return serialised chat history for *session_id*."""
        session = self._sm.get_session(session_id)
        if session is None:
            return []
        return session.get_history_dicts()

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        turn_id: str = "",
    ) -> None:
        """Append a single message (more granular than ``write_turn``)."""
        session = self._sm.get_or_create(session_id)
        session.add_message(role, content, turn_id=turn_id)

    # ------------------------------------------------------------------
    # AnnData
    # ------------------------------------------------------------------

    def get_adata(self, session_id: str, fallback=None) -> Any:
        """Return the session-scoped AnnData object."""
        return self._sm.get_session_adata(session_id, fallback_adata=fallback)

    def commit_adata(self, session_id: str, adata: Any) -> None:
        """Persist a mutated ``adata`` back into the session."""
        self._sm.commit_session_adata(session_id, adata)
        logger.info(
            "ChannelContextBridge.commit_adata: session=%s n_obs=%s",
            session_id,
            getattr(adata, "n_obs", "?"),
        )

    # ------------------------------------------------------------------
    # Session metadata helpers
    # ------------------------------------------------------------------

    def session_exists(self, session_id: str) -> bool:
        return self._sm.get_session(session_id) is not None

    def get_summary(self, session_id: str) -> Optional[dict]:
        session = self._sm.get_session(session_id)
        if session is None:
            return None
        return session.to_summary()

    def sync_from_channel(
        self,
        session_id: str,
        messages: list[dict],
        overwrite: bool = False,
    ) -> int:
        """Bulk-import messages into the session history.

        Parameters
        ----------
        messages:
            List of ``{"role": ..., "content": ...}`` dicts.
        overwrite:
            If *True*, replace existing history; otherwise append only
            messages with timestamps newer than the last stored message.

        Returns
        -------
        int
            Number of messages actually added.
        """
        session = self._sm.get_or_create(session_id)
        if overwrite:
            session.history.clear()

        existing_count = len(session.history)
        added = 0
        for msg in messages:
            role = str(msg.get("role", "user")).strip()
            content = str(msg.get("content", "")).strip()
            turn_id = str(msg.get("turn_id", ""))
            if not content:
                continue
            # Skip messages already present (idempotent on re-sync)
            if not overwrite:
                if any(
                    m.role == role and m.content == content
                    for m in session.history
                ):
                    continue
            session.add_message(role, content, turn_id=turn_id)
            added += 1

        logger.info(
            "ChannelContextBridge.sync_from_channel: session=%s existing=%d added=%d",
            session_id,
            existing_count,
            added,
        )

        # Persist to workspace when workspace_manager is available
        if added > 0 and self._wm is not None:
            try:
                if self._wm.get_meta(session_id) is None:
                    self._wm.get_or_create(session_id)
                self._wm.save_history(session_id, session.get_history_dicts())
                self._wm.touch(session_id)
            except Exception:
                logger.exception("ChannelContextBridge.sync_from_channel: workspace persist failed")

        return added
