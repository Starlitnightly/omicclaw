"""OmicClaw CLI entry points.

Default behavior is gateway-first so the web UI, shared session state, and
configured channels run through the unified gateway daemon path.
"""

from __future__ import annotations

import os
import sys
from typing import Iterable, Sequence


_PASSTHROUGH_SUBCOMMANDS = {"gateway", "claw", "jarvis", "skill-seeker"}

# Flags that are forwarded verbatim to the underlying omicverse gateway/jarvis CLI.
# Any flag not listed here and not a recognised subcommand triggers gateway mode
# with the full argv forwarded so the downstream parser can act on it (e.g. --setup).
_GATEWAY_FLAGS = {
    "--setup",
    "--setup-language",
    "--no-browser",
    "--web-host",
    "--web-port",
    "--config-file",
    "--auth-file",
    "--verbose",
    "--debug",
}


def _set_omicclaw_env() -> None:
    os.environ["OV_LAUNCHER"] = "omicclaw"
    os.environ["OV_WEB_FORCE_LOGIN"] = "1"


def _normalize_argv(argv: Sequence[str] | None) -> list[str]:
    return list(argv or [])


def _run_gateway(argv: Sequence[str] | None = None) -> int:
    _set_omicclaw_env()
    from omicverse.cli import main as omicverse_main

    return omicverse_main(["gateway", *_normalize_argv(argv)])


def _run_passthrough(argv: Sequence[str]) -> int:
    _set_omicclaw_env()
    from omicverse.cli import main as omicverse_main

    return omicverse_main(list(argv))


def _run_web(argv: Sequence[str] | None = None) -> int:
    from start_server import omicclaw_main as web_main

    return web_main(_normalize_argv(argv))


def main(argv: Sequence[str] | None = None) -> int:
    # When called as the console-script entry point argv is None; read sys.argv.
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        subcommand = args[0]
        if subcommand == "web":
            return _run_web(args[1:])
        if subcommand in _PASSTHROUGH_SUBCOMMANDS:
            return _run_passthrough(args)
    # Unknown flags (e.g. --setup) and bare invocation both fall through to
    # gateway mode.  Forward the full argv so downstream parsers handle them.
    return _run_gateway(args)


def omicclaw_main(argv: Iterable[str] | None = None) -> int:
    return main(list(argv) if argv is not None else None)


__all__ = ["main", "omicclaw_main"]
