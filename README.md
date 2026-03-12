<p align="center">
  <img src="https://raw.githubusercontent.com/Starlitnightly/ImageStore/main/omicverse_img/Gemini_Generated_Image_xefpyexefpyexefp.png" width="400" alt="omicclaw">
</p>


<p align="center">
  <strong>The standalone skill catalog for OmicVerse.</strong><br>
  Built for <code>omicverse claw</code> and OmicVerse agent workflows. Tutorial-backed. Reproducible. Bioinformatics-native.
</p>

<p align="center">
  <a href="https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white"><img src="https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white" alt="Python 3.8+"></a>
  <a href="https://img.shields.io/badge/skills-32-orange"><img src="https://img.shields.io/badge/skills-32-orange" alt="32 skills"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
  <a href="https://pypi.org/project/omicverse-skills/"><img src="https://img.shields.io/badge/PyPI-omicverse--skills-blue" alt="PyPI omicverse-skills"></a>
</p>

---

## What omicclaw Does Today

`omicclaw` packages the OmicVerse skill library as a standalone repository and Python distribution:

- `32` skills covering single-cell, bulk RNA-seq, spatial transcriptomics, multi-omics, knowledge lookup, and data export
- tutorial-aligned instructions derived from OmicVerse workflows
- a lightweight Python API for discovering bundled skills
- a clean dependency boundary so skills can evolve independently of the main `omicverse` source tree

This repository is not a replacement for `omicverse`. It is the skill layer that sits on top of `omicverse`.

If `omicverse` provides the analysis engine, `omicclaw` provides the domain-specific task playbooks that help `omicverse claw` generate better code.

---

## The Problem

General-purpose coding agents can usually write plausible bioinformatics code, but they often miss domain details that matter:

- whether a workflow expects raw counts or log-transformed values
- which AnnData fields must exist before a plot or downstream method
- how a specific OmicVerse tutorial orders preprocessing, clustering, annotation, and export
- which defensive checks prevent broken pipelines

That is what these skills encode.

Instead of asking a model to guess how to combine `ov.pp`, `ov.single`, `ov.bulk`, or `ov.space`, `omicclaw` gives the agent reusable, tutorial-backed instructions for each analysis family.

---

## What Is a Skill?

A skill is a small, focused knowledge package for one analysis job.

Each skill directory contains:

- `SKILL.md`: when to use the workflow, its core steps, expected inputs, and defensive checks
- `reference.md` when needed: extra operational notes, caveats, or tutorial-derived details

Conceptually:

```text
general LLM guesswork -> "maybe this is the right omicverse pipeline"
omicverse + omicclaw  -> "use the right workflow, with the right prerequisites"
```

---

## Skill Coverage

Current skills are organized around the major OmicVerse analysis surfaces:

| Area | Examples |
| --- | --- |
| Single-cell | preprocessing, clustering, annotation, trajectory, SCENIC, CellPhoneDB, CellFate |
| Bulk RNA-seq | DEG, DESeq2, ComBat batch correction, WGCNA, TCGA preprocessing |
| Spatial | spatial tutorials, single-to-spatial mapping |
| Multi-omics | single-cell multi-omics integration, Bulk2Single, BulkTrajBlend |
| Knowledge and utilities | BioContext knowledge queries, datasets loading, plotting, stats, transforms |
| Export | Excel export, PDF export |

Skill files live under:

```text
src/omicverse_skills/skills/
```

---

## Quick Start

Install `omicverse` first. This repository depends on the OmicVerse runtime and is meant to be used with it.

### Install from PyPI

```bash
pip install -U omicverse
pip install -U omicverse-skills
omicverse claw --help
```

### Install from source

```bash
git clone https://github.com/Starlitnightly/omicclaw.git
cd omicclaw
pip install -U omicverse
pip install -e .
```

Package names:

- GitHub repository: `omicclaw`
- PyPI distribution: `omicverse-skills`
- Python package: `omicverse_skills`

---

## Basic Usage with `omicverse claw`

The recommended usage pattern follows the `OmicVerse Claw CLI` workflow: describe the analysis you want in natural language and let `omicverse claw` generate code.

Reference tutorial:

- `OmicVerse Claw CLI`: <https://omicverse.readthedocs.io/en/latest/Tutorials-jarvis/t_claw_cli/#2-basic-usage>

The simplest form is:

```bash
omicverse claw "basic qc and clustering"
```

This prints generated Python code to `stdout`.

Examples mapped to this skill library:

```bash
omicverse claw "preprocess PBMC3k and run PCA neighbors UMAP"
omicverse claw "annotate lung scRNA-seq with a minimal workflow"
omicverse claw "find marker genes for each leiden cluster"
omicverse claw "run DESeq2-style bulk differential expression with omicverse"
omicverse claw "build a WGCNA workflow from an expression matrix"
omicverse claw "map single-cell atlas to spatial transcriptomics data"
omicverse claw "query UniProt and Reactome for a gene list"
```

In practice, `omicverse claw` initializes the OmicVerse agent and uses this skill catalog to ground code generation in the right workflow family.

---

## Save Output to a File

```bash
omicverse claw "basic qc and clustering" --output workflow.py
```

Useful when you want code generation to stay script-first and reviewable.

More examples:

```bash
omicverse claw "find marker genes for each leiden cluster" --output markers.py
omicverse claw "run a basic PCA plus neighbors plus UMAP pipeline" --output pbmc_pipeline.py
```

---

## Common Options

Choose a model:

```bash
omicverse claw --model gpt-5.2 "basic qc and clustering"
```

Use an explicit API key:

```bash
omicverse claw --api-key "$OPENAI_API_KEY" "basic qc and clustering"
```

Use a custom endpoint:

```bash
omicverse claw \
  --endpoint http://127.0.0.1:11434/v1 \
  --model my-model \
  "basic qc and clustering"
```

Disable the lightweight reflection pass:

```bash
omicverse claw --no-reflection "basic qc and clustering"
```

---

## Debug and Daemon Modes

Inspect skill matching and runtime behavior:

```bash
omicverse claw --debug-registry "basic qc and clustering"
```

Keep the agent warm for repeated local calls:

```bash
omicverse claw --daemon
omicverse claw --use-daemon "basic qc and clustering"
omicverse claw --use-daemon "find marker genes"
omicverse claw --stop-daemon
```

This is useful when you are iterating on prompts across multiple OmicVerse workflows.

---

## When to Use `claw` vs `jarvis`

Use `omicverse claw` when:

- you want code only
- you want to inspect or edit the generated script yourself
- you want a CLI-first workflow that can be called from shells or automation

Use OmicVerse Jarvis when:

- you want a chat-style workflow
- you want interactive follow-up and session memory
- you want a user-facing assistant rather than a code-only generator

---

## Python API

You can also inspect the bundled skill catalog directly:

```python
from omicverse_skills import list_skills, load_skill_text, skill_root

print(skill_root())
print(len(list_skills()))
print(list_skills()[0]["slug"])
print(load_skill_text("single-preprocessing")[:200])
```

This is useful for tooling, testing, indexing, and custom agent integrations.

---

## Repository Layout

```text
.
├── README.md
├── pyproject.toml
├── src/
│   └── omicverse_skills/
│       ├── __init__.py
│       ├── registry.py
│       └── skills/
│           ├── single-preprocessing/
│           ├── bulk-deg-analysis/
│           ├── spatial-tutorials/
│           └── ...
└── LICENSE
```

---

## Add a New Skill

Use the existing directories as the template:

1. Create `src/omicverse_skills/skills/<skill-slug>/SKILL.md`.
2. Add `reference.md` if the workflow needs extra tutorial detail.
3. Keep the scope narrow: one skill should solve one analysis family well.
4. Prefer explicit prerequisites and defensive validation over generic advice.
5. Align the instructions with real OmicVerse APIs and tutorial order.

Good skills for this repo are usually:

- tutorial-backed
- OmicVerse-specific
- reproducible across datasets
- clear about expected inputs and failure modes

---

## Build and Release

```bash
python -m build
python -m twine upload dist/*
```

---

## License

MIT.
