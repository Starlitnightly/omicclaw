"""OmicClaw CLI entry points.

Default behavior is gateway-first so the web UI, shared session state, and
configured channels run through the unified gateway daemon path.
"""

from __future__ import annotations

import os
from typing import Iterable, Sequence


_PASSTHROUGH_SUBCOMMANDS = {"gateway", "claw", "jarvis", "skill-seeker"}


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
    args = _normalize_argv(argv)
    if args:
        subcommand = args[0]
        if subcommand == "web":
            return _run_web(args[1:])
        if subcommand in _PASSTHROUGH_SUBCOMMANDS:
            return _run_passthrough(args)
    return _run_gateway(args)


def omicclaw_main(argv: Iterable[str] | None = None) -> int:
    return main(list(argv) if argv is not None else None)


__all__ = ["main", "omicclaw_main"]
