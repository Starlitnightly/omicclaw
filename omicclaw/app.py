"""Source-tree facade exposing the desktop-friendly Flask app factory."""

from __future__ import annotations

from app import app as flask_app
from app import create_app

app = flask_app

__all__ = ["app", "create_app"]
