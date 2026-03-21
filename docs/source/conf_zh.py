"""Sphinx configuration for the Read the Docs Chinese translation project."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from _conf_common import apply_config

apply_config(globals(), mode="zh")
