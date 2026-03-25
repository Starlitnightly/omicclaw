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


def _check_and_apply_update() -> None:
    """Check PyPI for a newer omicclaw version and self-update via uv pip install -U.

    Runs silently in the background. Prints a one-line notice if an update is found
    and applied. Does nothing if uv is not available or network is unreachable.
    """
    import threading
    threading.Thread(target=_update_worker, daemon=True).start()


def _update_worker() -> None:
    import subprocess, time
    from importlib.metadata import version as pkg_version, PackageNotFoundError
    try:
        current = pkg_version("omicclaw")
    except PackageNotFoundError:
        return

    try:
        import urllib.request, json as _json
        with urllib.request.urlopen(
            "https://pypi.org/pypi/omicclaw/json", timeout=5
        ) as resp:
            data = _json.loads(resp.read())
        latest = data["info"]["version"]
    except Exception:
        return

    # Simple version comparison — avoid heavy packaging dependency at startup
    def _ver_tuple(v: str):
        import re
        return tuple(int(x) for x in re.findall(r"\d+", v))

    if _ver_tuple(latest) <= _ver_tuple(current):
        return  # already up to date

    # Find uv executable
    import shutil
    uv = shutil.which("uv")
    if not uv:
        print(f"\033[33m[omicclaw] New version {latest} available (current: {current}). Run: uv pip install -U omicclaw\033[0m", flush=True)
        return

    print(f"\033[32m[omicclaw] Updating {current} → {latest}...\033[0m", flush=True)
    try:
        result = subprocess.run(
            [uv, "pip", "install", "-U", "omicclaw"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print(f"\033[32m[omicclaw] Updated to {latest}. Restart to apply.\033[0m", flush=True)
        else:
            print(f"\033[33m[omicclaw] Auto-update failed: {result.stderr.strip()}\033[0m", flush=True)
    except Exception as e:
        print(f"\033[33m[omicclaw] Auto-update error: {e}\033[0m", flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    _check_and_apply_update()
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
