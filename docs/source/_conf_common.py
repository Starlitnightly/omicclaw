"""Shared Sphinx configuration helpers for OmicClaw docs."""

from __future__ import annotations

from datetime import datetime


def apply_config(namespace: dict, mode: str) -> None:
    project = "OmicClaw"
    author = "OmicClaw Contributors"

    html_title = {
        "pages": "OmicClaw Docs",
        "en": "OmicClaw Documentation",
        "zh": "OmicClaw 文档",
    }[mode]

    exclude_patterns = {
        "pages": ["_build", "Thumbs.db", ".DS_Store"],
        "en": ["_build", "Thumbs.db", ".DS_Store", "zh/**", "index.md"],
        "zh": ["_build", "Thumbs.db", ".DS_Store", "en/**", "index.md"],
    }[mode]

    master_doc = {
        "pages": "index",
        "en": "en/index",
        "zh": "zh/index",
    }[mode]

    redirect_target = {
        "pages": None,
        "en": "en/index.html",
        "zh": "zh/index.html",
    }[mode]

    namespace.update(
        {
            "project": project,
            "author": author,
            "copyright": f"{datetime.now():%Y}, {author}",
            "extensions": [
                "myst_parser",
                "sphinx_design",
                "sphinx_copybutton",
            ],
            "templates_path": ["_templates"],
            "exclude_patterns": exclude_patterns,
            "source_suffix": {
                ".md": "markdown",
            },
            "master_doc": master_doc,
            "root_doc": master_doc,
            "pygments_style": "github-dark",
            "pygments_dark_style": "github-dark",
            "html_theme": "sphinx_book_theme",
            "html_title": html_title,
            "html_static_path": ["_static"],
            "html_css_files": ["custom.css"],
            "html_theme_options": {
                "repository_url": "https://github.com/Starlitnightly/omicclaw",
                "use_repository_button": True,
                "use_source_button": True,
                "use_issues_button": True,
                "path_to_docs": "docs/source",
                "repository_branch": "main",
                "home_page_in_toc": True,
                "show_navbar_depth": 2,
                "collapse_navbar": False,
                "navigation_with_keys": True,
                "logo": {
                    "image_light": "_static/logo.png",
                    "image_dark": "_static/logo.png",
                },
            },
            "myst_enable_extensions": [
                "colon_fence",
                "deflist",
                "html_admonition",
                "html_image",
                "linkify",
                "replacements",
                "smartquotes",
                "strikethrough",
                "tasklist",
            ],
            "copybutton_prompt_text": r">>> |\.\.\. |\$ ",
            "copybutton_prompt_is_regexp": True,
        }
    )

    if redirect_target is not None:
        namespace["html_additional_pages"] = {"index": "redirect.html"}
        namespace["html_context"] = {
            **namespace.get("html_context", {}),
            "redirect_target": redirect_target,
            "redirect_title": html_title,
        }
