# omicclaw

Standalone repository for OmicVerse skills.

- GitHub repository name: `omicclaw`
- PyPI distribution name: `omicverse-skills`
- Python package name: `omicverse_skills`

## What This Repository Contains

This repository publishes the OmicVerse skill catalog as a standalone Python package,
so `omicverse` and `omicverseweb` do not need to rely on a source checkout under
`.claude/skills` at runtime.

Bundled assets live under:

```text
src/omicverse_skills/skills/
```

Each skill directory contains at minimum:

- `SKILL.md`
- optional `reference.md`

## Install

```bash
pip install omicverse-skills
```

## Python API

```python
from omicverse_skills import skill_root, list_skills

print(skill_root())
print(list_skills()[0])
```

## Release

```bash
python -m build
python -m twine upload dist/*
```
