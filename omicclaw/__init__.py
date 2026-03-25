"""OmicClaw source package facade."""

from __future__ import annotations

try:
    from importlib.metadata import version
except ImportError:  # pragma: no cover
    from importlib_metadata import version  # type: ignore


try:
    __version__ = version("omicclaw")
except Exception:  # pragma: no cover - source tree without installed metadata
    __version__ = "2.0.5rc1"


__all__ = ["__version__"]
