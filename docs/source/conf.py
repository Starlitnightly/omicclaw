"""Sphinx configuration entrypoint for local, Pages, and Read the Docs builds."""

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from _conf_common import apply_config


def _select_mode() -> str:
    if os.environ.get("READTHEDOCS") == "True":
        project = os.environ.get("READTHEDOCS_PROJECT", "").lower()
        language = os.environ.get("READTHEDOCS_LANGUAGE", "").lower()

        if project.endswith("-zh") or language.startswith("zh"):
            return "zh"

        return "en"

    return "pages"


apply_config(globals(), mode=_select_mode())
