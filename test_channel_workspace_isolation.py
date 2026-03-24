#!/usr/bin/env python3
"""
Simulation test: channel message workspace routing
==================================================
Simulates the complete frontend/backend flow for channel messages (e.g., QQ)
and verifies that:

  1. The same channel_session_id reuses the same workspace and history
  2. A new channel_session_id creates a new conversation entry immediately
  3. History is reloaded from disk after restart when the session id returns
  4. When no channel_session_id exists, the stable route id becomes the workspace id

Run:
    cd omicclaw
    python test_channel_workspace_isolation.py
"""

import sys
import json
import hashlib
import re
import shutil
import tempfile
import threading
import time
from pathlib import Path

# Project root on path
PROJECT_ROOT = Path(__file__).parent

# Isolated temp dir so the test never touches ~/.omicclaw
TMP = Path(tempfile.mkdtemp(prefix="omicclaw_sim_"))

# Import service modules DIRECTLY (bypassing services/__init__.py which
# requires omicverse), then patch module-level constants before use.
import importlib.util as _ilu


def _load_module(name, rel_path):
    spec = _ilu.spec_from_file_location(name, PROJECT_ROOT / rel_path)
    mod = _ilu.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_wm_module = _load_module("workspace_service", "services/workspace_service.py")
_wm_module.BASE_DIR = TMP / ".omicclaw"
_wm_module.CONVERSATIONS_JSON = _wm_module.BASE_DIR / "conversations.json"
_wm_module._INDEX_LOCK = threading.Lock()

_ss_module = _load_module("agent_session_service", "services/agent_session_service.py")

WorkspaceManager = _wm_module.WorkspaceManager
SessionManager = _ss_module.SessionManager
ChatMessage = _ss_module.ChatMessage

workspace_manager = WorkspaceManager()
session_manager = SessionManager(max_sessions=50)


class SimBridge:
    """Simulates the patched _WorkspaceBridge from app.py."""

    _ROUTES_FILE = TMP / ".omicclaw" / "channel_routes.json"
    _SESSION_ID_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")

    def __init__(self):
        self._routes_lock = threading.Lock()
        self._route_to_workspace: dict = self._load_routes()
    def _load_routes(self) -> dict:
        try:
            if self._ROUTES_FILE.exists():
                return json.loads(self._ROUTES_FILE.read_text())
        except Exception:
            pass
        return {}

    def _save_routes(self):
        self._ROUTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._ROUTES_FILE.write_text(json.dumps(self._route_to_workspace))

    @staticmethod
    def _routing_sid(channel, scope_type, scope_id, thread_id=None):
        key = f"{channel}:{scope_type}:{scope_id}"
        if thread_id:
            key += f":thread:{thread_id}"
        return hashlib.sha1(key.encode()).hexdigest()[:16]

    def _normalize_workspace_sid(self, raw_session_id):
        if raw_session_id is None:
            return ""
        session_id = str(raw_session_id).strip()
        if not session_id:
            return ""
        safe = self._SESSION_ID_SAFE_RE.sub("_", session_id).strip("._-")
        if not safe:
            safe = "session"
        if safe != session_id:
            digest = hashlib.sha1(session_id.encode("utf-8")).hexdigest()[:12]
            safe = f"{safe}-{digest}"
        return safe

    def _hydrate_session_from_workspace(self, workspace_sid):
        session = session_manager.get_or_create(workspace_sid)
        meta = workspace_manager.get_meta(workspace_sid)
        if meta is not None:
            session.workspace_dir = str(workspace_manager.workspace_dir(workspace_sid))
            if meta.get("title"):
                session.title = meta["title"]
        if session.history:
            return session
        saved = workspace_manager.load_history(workspace_sid)
        for item in saved:
            session.history.append(ChatMessage(
                role=item.get("role", "user"),
                content=item.get("content", ""),
                turn_id=item.get("turn_id", ""),
                timestamp=item.get("timestamp", 0.0),
            ))
        return session

    def _active_workspace_for(self, routing_sid, channel, scope_type, scope_id,
                               thread_id=None, channel_session_id=None):
        wsid = self._normalize_workspace_sid(channel_session_id) or routing_sid
        with self._routes_lock:
            self._route_to_workspace[routing_sid] = wsid
            self._save_routes()
        ws_dir = workspace_manager.workspace_dir(wsid)
        ws_dir.mkdir(parents=True, exist_ok=True)
        (ws_dir / "channel_route.json").write_text(json.dumps({
            "routing_sid": routing_sid,
            "channel": channel,
            "scope_type": scope_type,
            "scope_id": str(scope_id),
            "thread_id": thread_id,
            "channel_session_id": channel_session_id or "",
        }))
        return wsid

    def _workspace_for_route(self, routing_sid: str):
        with self._routes_lock:
            return self._route_to_workspace.get(routing_sid)

    def _pre_create_workspace(self, routing_sid, channel, scope_type, scope_id,
                               thread_id=None, channel_session_id=None):
        wsid = self._active_workspace_for(
            routing_sid, channel, scope_type, scope_id, thread_id, channel_session_id
        )
        if workspace_manager.get_meta(wsid) is None:
            workspace_manager.get_or_create(wsid, title="")
        else:
            workspace_manager.touch(wsid)
        return wsid

    def activate_workspace(self, routing_sid: str, workspace_sid: str):
        with self._routes_lock:
            self._route_to_workspace[routing_sid] = workspace_sid
            self._save_routes()

    def get_prior_history_simple(self, channel, scope_type, scope_id, thread_id=None,
                                 channel_session_id=None, session_id=None):
        routing_sid = self._routing_sid(channel, scope_type, scope_id, thread_id)
        channel_session_id = channel_session_id or session_id
        wsid = self._pre_create_workspace(
            routing_sid, channel, scope_type, scope_id, thread_id, channel_session_id
        )
        session = self._hydrate_session_from_workspace(wsid)
        if session and session.history:
            return session.get_history_dicts(), wsid
        return [], wsid

    def on_turn_complete_simple(self, channel, scope_type, scope_id,
                                user_text, llm_text, thread_id=None,
                                channel_session_id=None, session_id=None):
        routing_sid = self._routing_sid(channel, scope_type, scope_id, thread_id)
        channel_session_id = channel_session_id or session_id
        if channel_session_id:
            self._pre_create_workspace(
                routing_sid, channel, scope_type, scope_id, thread_id, channel_session_id
            )
        workspace_sid = self._workspace_for_route(routing_sid)
        if not workspace_sid:
            return None
        web_session = session_manager.get_or_create(workspace_sid)
        web_session.add_message("user", f"[{channel}] {user_text}")
        if llm_text:
            web_session.add_message("assistant", llm_text)
        title = f"[{channel}] {user_text[:20]}"
        existing = workspace_manager.get_meta(workspace_sid)
        workspace_manager.get_or_create(workspace_sid, title=title)
        if existing is None or not existing.get("title", "").strip():
            workspace_manager.rename(workspace_sid, title)
        workspace_manager.save_history(workspace_sid, web_session.get_history_dicts())
        workspace_manager.touch(workspace_sid)
        return workspace_sid

    def simulate_restart(self):
        self._route_to_workspace = self._load_routes()
        session_manager._sessions.clear()


PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"


def check(cond, msg):
    if cond:
        print(f"  {PASS}  {msg}")
    else:
        print(f"  {FAIL}  {msg}")
    assert cond, msg


def banner(title):
    print(f"\n{'━' * 60}")
    print(f"  {title}")
    print(f"{'━' * 60}")


def print_conversations(label):
    convs = workspace_manager.list_conversations()
    print(f"\n  [Frontend sidebar after {label!r}]  ({len(convs)} entries)")
    for item in convs:
        print(f"    workspace={item['session_id']}  title={item['title']!r}")
    return convs


def simulate_turn(bridge, label, channel, scope_type, scope_id, user_text,
                  llm_reply, thread_id=None, channel_session_id=None, session_id=None):
    print(f"\n  ── {label} ──")
    print(f"     channel={channel}  scope={scope_type}:{scope_id}")
    print(f"     channel_session_id={channel_session_id!r}  session_id={session_id!r}")
    print(f"     QQ sends:  {user_text!r}")

    before = {c["session_id"] for c in workspace_manager.list_conversations()}
    history, wsid_pre = bridge.get_prior_history_simple(
        channel, scope_type, scope_id, thread_id, channel_session_id, session_id
    )
    print(f"     prior history: {len(history)} msgs  workspace_pre={wsid_pre}")
    time.sleep(0.01)
    wsid_post = bridge.on_turn_complete_simple(
        channel, scope_type, scope_id, user_text, llm_reply, thread_id, channel_session_id, session_id
    )
    print(f"     LLM replies:   {llm_reply!r}")
    print(f"     workspace_sid: {wsid_post}")
    after = {c["session_id"] for c in workspace_manager.list_conversations()}
    print(f"     new sidebar entries: {after - before}")

    check(wsid_pre == wsid_post, "get_prior_history and on_turn_complete agree on same workspace")
    return wsid_post, len(history)


def run_tests():
    bridge = SimBridge()

    banner("Scenario 1 — First QQ message with a new channel session id")
    ws1, hist_len1 = simulate_turn(
        bridge, "Msg 1", "qq", "group", "12345",
        "请帮我分析这个单细胞数据", "好的，请上传 .h5ad 文件。",
        channel_session_id="qq-session-A",
    )
    convs = print_conversations("Msg 1")
    check(hist_len1 == 0, "new session id starts without prior history")
    check(ws1 == "qq-session-A", "workspace uses the channel session id")
    check(len(convs) == 1, "sidebar shows 1 conversation")

    banner("Scenario 2 — Same channel session id reuses workspace and history")
    ws1b, hist_len2 = simulate_turn(
        bridge, "Msg 2", "qq", "group", "12345",
        "换个话题，帮我做细胞注释", "可以，先确认 marker 基因。",
        channel_session_id="qq-session-A",
    )
    convs = print_conversations("Msg 2")
    hist1 = workspace_manager.load_history(ws1)
    check(ws1b == ws1, "same channel session id reuses the original workspace")
    check(hist_len2 == 2, "same channel session id reloads prior history")
    check(len(hist1) == 4, "reused workspace now contains both turns")
    check(len(convs) == 1, "sidebar still shows a single conversation")

    banner("Scenario 3 — Same QQ group with a NEW channel session id")
    ws2, hist_len3 = simulate_turn(
        bridge, "Msg 3", "qq", "group", "12345",
        "这是一个全新的会话，请分析免疫细胞", "收到，请提供数据文件。",
        channel_session_id="qq-session-B",
    )
    convs = print_conversations("Msg 3")
    hist2 = workspace_manager.load_history(ws2)
    check(hist_len3 == 0, "new channel session id starts fresh")
    check(ws2 == "qq-session-B", "new channel session id becomes the new workspace id")
    check(ws2 != ws1, "different channel session ids do not collide")
    check(len(hist2) == 2, "new workspace contains only its own first turn")
    check(len(convs) == 2, "sidebar now shows two conversations")

    banner("Scenario 4 — Restart and resume the original channel session id")
    bridge.simulate_restart()
    ws1c, hist_len4 = simulate_turn(
        bridge, "Msg 4", "qq", "group", "12345",
        "服务器重启后继续旧会话", "历史上下文已恢复。",
        channel_session_id="qq-session-A",
    )
    convs = print_conversations("Msg 4")
    hist1_after = workspace_manager.load_history(ws1)
    check(ws1c == ws1, "same session id still maps to the same workspace after restart")
    check(hist_len4 == 4, "history was rehydrated from disk before the new turn")
    check(len(hist1_after) == 6, "workspace continued appending after restart")
    check(len(convs) == 2, "restart did not create duplicate conversations")

    banner("Scenario 5 — Explicit session_id behaves like channel_session_id")
    ws5, hist_len5 = simulate_turn(
        bridge, "Msg 5", "feishu", "dm", "chat-77",
        "继续上一个分析", "好的，接着看。",
        session_id="feishu-session-77",
    )
    ws6, hist_len6 = simulate_turn(
        bridge, "Msg 6", "feishu", "dm", "chat-77",
        "再补一个图", "已经补充。",
        session_id="feishu-session-77",
    )
    check(hist_len5 == 0, "first explicit session_id starts fresh")
    check(ws6 == ws5, "same explicit session_id reuses workspace")
    check(hist_len6 == 2, "same explicit session_id reloads prior history")

    banner("Scenario 6 — Route fallback without channel session id")
    fallback_route_sid = SimBridge._routing_sid("qq", "group", "fallback-group")
    ws_f1, hist_f1 = simulate_turn(
        bridge, "Fallback 1", "qq", "group", "fallback-group",
        "第一条没有 session id 的消息", "收到。"
    )
    ws_f2, hist_f2 = simulate_turn(
        bridge, "Fallback 2", "qq", "group", "fallback-group",
        "第二条没有 session id 的消息", "收到。"
    )
    check(ws_f1 == fallback_route_sid, "without channel session id, workspace falls back to stable route id")
    check(ws_f2 == ws_f1, "same route reuses the same workspace without Web activation")
    check(hist_f1 == 0, "first route-based turn starts fresh")
    check(hist_f2 == 2, "second route-based turn reloads prior history")
    hist_fallback = workspace_manager.load_history(ws_f1)
    check(len(hist_fallback) == 4, "route fallback workspace accumulates both turns")

    banner("RESULTS")
    print(f"  workspace A (session reuse):   {ws1}")
    print(f"  workspace B (new session):     {ws2}")
    print(f"  feishu explicit-session ws:    {ws5}")
    print(f"  fallback workspace:            {ws_f1}")
    print(f"\n  {PASS}  All scenarios passed.")


if __name__ == "__main__":
    try:
        run_tests()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
