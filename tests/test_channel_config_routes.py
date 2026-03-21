from __future__ import annotations

import unittest
from unittest import mock

from gateway import channel_config_routes as routes


class ChannelConfigRoutesTests(unittest.TestCase):
    def test_build_start_command_uses_channel_only_jarvis_runner(self) -> None:
        cfg = {
            "model": "gpt-5.3-codex",
            "endpoint": "https://chatgpt.com/backend-api",
            "telegram": {
                "token": "telegram-token",
                "allowed_users": ["alice", 12345],
            },
        }

        with mock.patch.object(routes, "_find_omicverse_cmd", return_value=["/tmp/omicverse"]):
            cmd = routes._build_start_command("telegram", cfg, "api-key")

        self.assertEqual(cmd[:4], ["/tmp/omicverse", "jarvis", "--channel", "telegram"])
        self.assertIn("--model", cmd)
        self.assertIn("--api-key", cmd)
        self.assertIn("--endpoint", cmd)
        self.assertNotIn("claw", cmd)


if __name__ == "__main__":
    unittest.main()
