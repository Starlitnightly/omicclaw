"""Sphinx configuration for the default GitHub Pages / local docs build."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from _conf_common import apply_config

apply_config(globals(), mode="pages")
