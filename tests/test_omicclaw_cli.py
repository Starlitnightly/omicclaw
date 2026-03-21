from __future__ import annotations

import importlib
import os
import sys
import types
import unittest
from unittest import mock


def _fake_omicverse_modules(main_mock: mock.Mock) -> dict[str, types.ModuleType]:
    package = types.ModuleType("omicverse")
    package.__path__ = []  # type: ignore[attr-defined]
    cli_module = types.ModuleType("omicverse.cli")
    cli_module.main = main_mock  # type: ignore[attr-defined]
    package.cli = cli_module  # type: ignore[attr-defined]
    return {"omicverse": package, "omicverse.cli": cli_module}


class OmicClawCliTests(unittest.TestCase):
    def setUp(self) -> None:
        sys.modules.pop("omicclaw.cli", None)

    def test_default_dispatches_to_gateway_mode(self) -> None:
        delegate = mock.Mock(return_value=17)

        with mock.patch.dict(sys.modules, _fake_omicverse_modules(delegate)):
            cli = importlib.import_module("omicclaw.cli")
            rc = cli.main(["--channel", "telegram", "--model", "gpt-5.3-codex"])

        self.assertEqual(rc, 17)
        delegate.assert_called_once_with(["gateway", "--channel", "telegram", "--model", "gpt-5.3-codex"])
        self.assertEqual(os.environ.get("OV_LAUNCHER"), "omicclaw")
        self.assertEqual(os.environ.get("OV_WEB_FORCE_LOGIN"), "1")

    def test_web_subcommand_uses_local_web_launcher(self) -> None:
        cli = importlib.import_module("omicclaw.cli")

        with mock.patch("start_server.omicclaw_main", return_value=23) as web_main:
            rc = cli.main(["web", "--port", "5055"])

        self.assertEqual(rc, 23)
        web_main.assert_called_once_with(["--port", "5055"])


if __name__ == "__main__":
    unittest.main()
