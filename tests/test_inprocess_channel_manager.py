from __future__ import annotations

import threading
import time
import unittest
from unittest import mock

from gateway.inprocess_channel_manager import InProcessChannelManager


class InProcessChannelManagerTests(unittest.TestCase):
    def test_start_and_stop_discord_channel_in_process(self) -> None:
        started = threading.Event()
        stopped = threading.Event()

        def _fake_run_discord_bot(**kwargs) -> None:  # noqa: ANN003
            stop_event = kwargs["stop_event"]
            started.set()
            stop_event.wait(timeout=2.0)
            stopped.set()

        manager = InProcessChannelManager(session_manager=object())
        cfg = {
            "discord": {
                "token": "discord-token",
            }
        }

        with mock.patch("omicverse.jarvis.channels.discord.run_discord_bot", side_effect=_fake_run_discord_bot):
            result = manager.start_channel("discord", cfg=cfg, source="test")
            self.assertTrue(result["ok"])
            self.assertTrue(started.wait(timeout=1.0))

            states = {item["channel"]: item for item in manager.list_states(cfg)}
            self.assertTrue(states["discord"]["running"])

            stop_result = manager.stop_channel("discord")
            self.assertTrue(stop_result["ok"])
            self.assertTrue(stopped.wait(timeout=1.0))

            deadline = time.time() + 1.0
            while time.time() < deadline:
                states = {item["channel"]: item for item in manager.list_states(cfg)}
                if not states["discord"]["running"]:
                    break
                time.sleep(0.05)
            self.assertFalse(states["discord"]["running"])

    def test_start_and_stop_qq_channel_in_process(self) -> None:
        started = threading.Event()
        stopped = threading.Event()

        def _fake_run_qq_bot(**kwargs) -> None:  # noqa: ANN003
            stop_event = kwargs["stop_event"]
            started.set()
            stop_event.wait(timeout=2.0)
            stopped.set()

        manager = InProcessChannelManager(session_manager=object())
        cfg = {
            "qq": {
                "app_id": "123",
                "client_secret": "secret",
                "markdown": False,
                "image_host": None,
                "image_server_port": 8081,
            }
        }

        with mock.patch("omicverse.jarvis.channels.qq.run_qq_bot", side_effect=_fake_run_qq_bot):
            result = manager.start_channel("qq", cfg=cfg, source="test")
            self.assertTrue(result["ok"])
            self.assertTrue(started.wait(timeout=1.0))

            states = {item["channel"]: item for item in manager.list_states(cfg)}
            self.assertTrue(states["qq"]["running"])

            stop_result = manager.stop_channel("qq")
            self.assertTrue(stop_result["ok"])
            self.assertTrue(stopped.wait(timeout=1.0))

            deadline = time.time() + 1.0
            while time.time() < deadline:
                states = {item["channel"]: item for item in manager.list_states(cfg)}
                if not states["qq"]["running"]:
                    break
                time.sleep(0.05)
            self.assertFalse(states["qq"]["running"])


if __name__ == "__main__":
    unittest.main()
