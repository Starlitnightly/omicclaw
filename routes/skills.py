"""
Skills Routes - Skill Store API Endpoints
=========================================
Expose the same skill catalog that ``ov.Agent`` discovers at runtime.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote

import omicverse
from flask import Blueprint, jsonify, request

from omicverse.utils.skill_registry import (
    build_multi_path_skill_registry,
    discover_multi_path_skill_roots,
)
from utils.remote_store import request_remote_json, remote_store_enabled


bp = Blueprint("skills", __name__)


def _package_root() -> Path:
    return Path(omicverse.__file__).resolve().parent.parent


def _workspace_root() -> Path:
    return Path.cwd().resolve()


def _skill_roots() -> List[Tuple[str, Path]]:
    return discover_multi_path_skill_roots(_package_root(), _workspace_root())


def _builtin_skill_roots() -> List[Tuple[str, Path]]:
    return [(label, root) for label, root in _skill_roots() if label != "Workspace"]


def _builtin_skill_root() -> Path:
    roots = _builtin_skill_roots()
    if roots:
        return roots[-1][1]
    return (_package_root() / ".claude" / "skills").resolve()


def _workspace_skill_root() -> Path:
    return (_workspace_root() / ".claude" / "skills").resolve()


def _allowed_roots() -> List[Tuple[str, Path]]:
    return _skill_roots()


def _resolve_skill_path(raw_path: str) -> Path:
    candidate = Path(raw_path or "").expanduser().resolve()
    for _, root in _allowed_roots():
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    raise ValueError("Invalid skill path")


def _parse_frontmatter(text: str) -> Dict[str, str]:
    payload: Dict[str, str] = {}
    lines = (text or "").splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return payload
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip().lower()] = value.strip().strip('"').strip("'")
    return payload


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip()).strip("-_.")
    return text.lower() or "custom-skill"


def _read_text_if_exists(path: Path | None) -> str:
    if not path or not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _reference_file(skill_dir: Path) -> Path:
    return skill_dir / "reference.md"


def _is_builtin_path(path: Path) -> bool:
    resolved = path.resolve()
    for _, root in _builtin_skill_roots():
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _is_workspace_path(path: Path) -> bool:
    try:
        path.resolve().relative_to(_workspace_skill_root())
        return True
    except ValueError:
        return False


def _is_editable_path(path: Path) -> bool:
    resolved = path.resolve()
    try:
        resolved.relative_to(_workspace_skill_root())
        return True
    except ValueError:
        return False


def _markdown_excerpt(text: str, limit: int = 260) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"^[#>*\-\s]+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _default_skill_template(name: str, description: str) -> str:
    skill_name = (name or "Custom Skill").strip() or "Custom Skill"
    skill_desc = (description or "Describe what this skill does.").strip() or "Describe what this skill does."
    return (
        "---\n"
        f'name: {skill_name}\n'
        f'description: "{skill_desc}"\n'
        "---\n\n"
        f"# {skill_name}\n\n"
        "## Overview\n\n"
        "Describe when to use this skill.\n\n"
        "## Workflow\n\n"
        "1. Define the task.\n"
        "2. Explain the constraints.\n"
        "3. Execute the specialized steps.\n"
    )


def _skill_entry_from_metadata(slug: str, metadata) -> Dict[str, object]:
    skill_dir = Path(metadata.path).resolve()
    skill_file = skill_dir / "SKILL.md"
    reference_file = _reference_file(skill_dir)
    reference_content = _read_text_if_exists(reference_file)
    root_label = "Workspace"
    root_path = _workspace_skill_root()
    editable = _is_editable_path(skill_file)
    for label, root in _allowed_roots():
        try:
            skill_dir.relative_to(root)
            root_label = label
            root_path = root
            break
        except ValueError:
            continue

    try:
        rel_path = str(skill_file.relative_to(root_path))
    except ValueError:
        rel_path = skill_file.name

    return {
        "name": metadata.name,
        "slug": slug,
        "description": metadata.description,
        "summary": metadata.description,
        "version": "",
        "path": str(skill_file),
        "filename": skill_file.name,
        "directory": str(skill_dir),
        "relative_path": rel_path,
        "root_label": root_label,
        "editable": editable,
        "source": "local",
        "remote_slug": "",
        "author": "",
        "tags": [],
        "homepage_url": "",
        "install_command": "",
        "package_name": "",
        "updated_at": int(skill_file.stat().st_mtime) if skill_file.exists() else 0,
        "reference_path": str(reference_file) if reference_file.exists() else "",
        "reference_relative_path": str(reference_file.relative_to(root_path)) if reference_file.exists() else "",
        "reference_excerpt": _markdown_excerpt(reference_content),
    }


def _remote_skill_entry(payload: Dict[str, object]) -> Dict[str, object]:
    slug = str(payload.get("slug") or "").strip()
    summary = str(payload.get("summary") or payload.get("description") or "").strip()
    tags = payload.get("tags") if isinstance(payload.get("tags"), list) else []
    return {
        "name": str(payload.get("name") or slug),
        "slug": slug,
        "description": str(payload.get("description") or ""),
        "summary": summary,
        "version": str(payload.get("version") or ""),
        "path": f"remote://{slug}",
        "filename": "SKILL.md",
        "directory": "",
        "relative_path": str(payload.get("package_name") or slug or "online-skill"),
        "root_label": "Online",
        "editable": False,
        "source": "online",
        "remote_slug": slug,
        "author": str(payload.get("author") or ""),
        "tags": [str(tag) for tag in tags if str(tag).strip()],
        "homepage_url": str(payload.get("homepage_url") or ""),
        "install_command": str(payload.get("install_command") or ""),
        "package_name": str(payload.get("package_name") or ""),
        "updated_at": 0,
        "reference_path": "",
        "reference_relative_path": "",
        "reference_excerpt": _markdown_excerpt(summary),
    }


def _read_bearer_token() -> str:
    header = str(request.headers.get("Authorization") or "")
    if not header.lower().startswith("bearer "):
        return ""
    return header.split(" ", 1)[1].strip()


def _fetch_remote_skills() -> tuple[List[Dict[str, object]], str]:
    if not remote_store_enabled():
        return [], ""
    data, status = request_remote_json("/api/v1/store/skills")
    if status != 200:
        return [], str(data.get("error") or "Failed to load online skills")
    items = data.get("skills")
    if not isinstance(items, list):
        return [], ""
    return [_remote_skill_entry(item) for item in items if isinstance(item, dict)], ""


def _remote_skill_markdown(skill: Dict[str, object]) -> str:
    lines = [f"# {skill.get('name') or skill.get('slug')}", ""]

    description = str(skill.get("description") or "").strip()
    if description:
        lines.extend([description, ""])

    lines.extend(["## Metadata", ""])
    lines.append(f"- Slug: `{skill.get('slug') or ''}`")
    if skill.get("version"):
        lines.append(f"- Version: `{skill['version']}`")
    if skill.get("author"):
        lines.append(f"- Author: {skill['author']}")
    if skill.get("package_name"):
        lines.append(f"- Package: `{skill['package_name']}`")
    if skill.get("install_command"):
        lines.append(f"- Install: `{skill['install_command']}`")
    if skill.get("homepage_url"):
        lines.append(f"- Homepage: {skill['homepage_url']}")
    tags = skill.get("tags") if isinstance(skill.get("tags"), list) else []
    if tags:
        lines.append(f"- Tags: {', '.join(str(tag) for tag in tags)}")

    readme_markdown = str(skill.get("readme_markdown") or "").strip()
    if readme_markdown:
        lines.extend(["", "## README", "", readme_markdown])

    return "\n".join(lines).strip() + "\n"


@bp.route("/list", methods=["GET"])
def list_skills():
    registry = build_multi_path_skill_registry(_package_root(), _workspace_root())
    local_items = [
        _skill_entry_from_metadata(slug, metadata)
        for slug, metadata in sorted(registry.skill_metadata.items(), key=lambda item: item[0].lower())
    ]
    bearer_token = _read_bearer_token()
    online_requires_auth = remote_store_enabled() and not bearer_token
    if online_requires_auth:
        remote_items, remote_error = [], ""
    else:
        remote_items, remote_error = _fetch_remote_skills()
    builtin_roots = [{"label": label, "path": str(root)} for label, root in _builtin_skill_roots()]
    return jsonify(
        {
            "skills": local_items + remote_items,
            "local_count": len(local_items),
            "online_count": len(remote_items),
            "online_enabled": remote_store_enabled(),
            "online_requires_auth": online_requires_auth,
            "online_error": remote_error,
            "workspace_root": str(_workspace_skill_root()),
            "builtin_root": str(_builtin_skill_root()),
            "builtin_roots": builtin_roots,
        }
    )


@bp.route("/open", methods=["POST"])
def open_skill():
    payload = request.get_json(silent=True) or {}
    raw_path = str(payload.get("path") or "")
    if not raw_path:
        return jsonify({"error": "Missing skill path"}), 400
    try:
        skill_file = _resolve_skill_path(raw_path)
    except ValueError:
        return jsonify({"error": "Invalid skill path"}), 400
    if not skill_file.exists() or not skill_file.is_file():
        return jsonify({"error": "Skill file not found"}), 404

    text = skill_file.read_text(encoding="utf-8", errors="ignore")
    meta = _parse_frontmatter(text)
    reference_file = _reference_file(skill_file.parent)
    reference_content = _read_text_if_exists(reference_file)
    editable = _is_editable_path(skill_file)

    return jsonify(
        {
            "name": meta.get("name") or skill_file.parent.name,
            "filename": skill_file.name,
            "path": str(skill_file),
            "content": text,
            "type": "skill",
            "editable": editable,
            "reference_path": str(reference_file) if reference_file.exists() else "",
            "reference_content": reference_content,
        }
    )


@bp.route("/open_reference", methods=["POST"])
def open_reference():
    payload = request.get_json(silent=True) or {}
    raw_path = str(payload.get("path") or "")
    if not raw_path:
        return jsonify({"error": "Missing skill path"}), 400
    try:
        source_path = _resolve_skill_path(raw_path)
    except ValueError:
        return jsonify({"error": "Invalid skill path"}), 400

    skill_dir = source_path.parent if source_path.suffix.lower() == ".md" else source_path
    reference_file = _reference_file(skill_dir)
    editable = _is_editable_path(reference_file)

    if not reference_file.exists() and editable:
        reference_file.parent.mkdir(parents=True, exist_ok=True)
        reference_file.write_text("", encoding="utf-8")

    content = _read_text_if_exists(reference_file)
    return jsonify(
        {
            "name": "reference.md",
            "filename": "reference.md",
            "path": str(reference_file),
            "content": content,
            "type": "skill",
            "editable": editable,
        }
    )


@bp.route("/open_remote", methods=["POST"])
def open_remote_skill():
    payload = request.get_json(silent=True) or {}
    slug = str(payload.get("slug") or "").strip()
    if not slug:
        return jsonify({"error": "Missing remote skill slug"}), 400
    if not remote_store_enabled():
        return jsonify({"error": "Remote skill store is not configured"}), 503

    data, status = request_remote_json(f"/api/v1/store/skills/{quote(slug)}")
    if status != 200:
        return jsonify(data), status

    skill = data.get("skill")
    if not isinstance(skill, dict):
        return jsonify({"error": "Invalid remote skill payload"}), 502

    return jsonify(
        {
            "name": str(skill.get("name") or slug),
            "filename": f"{slug}.md",
            "path": f"remote://{slug}",
            "content": _remote_skill_markdown(skill),
            "type": "skill",
            "editable": False,
            "reference_path": "",
            "reference_content": "",
        }
    )


@bp.route("/save", methods=["POST"])
def save_skill():
    payload = request.get_json(silent=True) or {}
    raw_path = str(payload.get("path") or "")
    content = payload.get("content")
    if not raw_path or not isinstance(content, str):
        return jsonify({"error": "Missing skill path or content"}), 400
    try:
        skill_file = _resolve_skill_path(raw_path)
    except ValueError:
        return jsonify({"error": "Invalid skill path"}), 400

    if not _is_editable_path(skill_file):
        return jsonify({"error": "Skill path is not editable"}), 403

    skill_file.parent.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(content, encoding="utf-8")
    return jsonify({"success": True})


@bp.route("/create", methods=["POST"])
def create_skill():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name") or "").strip()
    slug = _slugify(str(payload.get("slug") or name))
    description = str(payload.get("description") or "").strip()
    content = payload.get("content")
    if not name:
        return jsonify({"error": "Missing skill name"}), 400
    if content is not None and not isinstance(content, str):
        return jsonify({"error": "Invalid skill content"}), 400

    root = _workspace_skill_root()
    root.mkdir(parents=True, exist_ok=True)
    skill_dir = (root / slug).resolve()
    try:
        skill_dir.relative_to(root)
    except ValueError:
        return jsonify({"error": "Invalid skill destination"}), 400
    if skill_dir.exists():
        return jsonify({"error": "Skill already exists"}), 400

    skill_dir.mkdir(parents=True, exist_ok=False)
    skill_file = skill_dir / "SKILL.md"
    reference_file = _reference_file(skill_dir)
    body = content if isinstance(content, str) and content.strip() else _default_skill_template(name, description)
    skill_file.write_text(body, encoding="utf-8")
    reference_file.write_text("", encoding="utf-8")
    return jsonify(
        {
            "success": True,
            "skill": {
                "name": name,
                "slug": slug,
                "description": description,
                "version": "",
                "path": str(skill_file),
                "filename": skill_file.name,
                "directory": str(skill_dir),
                "relative_path": str(skill_file.relative_to(root)),
                "root_label": "Workspace",
                "editable": True,
                "updated_at": int(skill_file.stat().st_mtime),
                "reference_path": str(reference_file),
                "reference_relative_path": str(reference_file.relative_to(root)),
                "reference_excerpt": "",
            },
        }
    )
