<p align="center">
  <img src="https://raw.githubusercontent.com/Starlitnightly/ImageStore/main/omicverse_img/Gemini_Generated_Image_xefpyexefpyexefp.png" width="400" alt="OmicClaw">
</p>

<p align="center">
  <strong>OmicClaw</strong><br>
  The gateway-first OmicVerse workspace for web UI, channels, notebooks, and agent workflows.
</p>

<p align="center">
  <a href="https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white"><img src="https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white" alt="Python 3.8+"></a>
  <a href="https://img.shields.io/badge/runtime-web%20gateway-0f766e"><img src="https://img.shields.io/badge/runtime-web%20gateway-0f766e" alt="Web gateway"></a>
  <a href="https://img.shields.io/badge/channels-telegram%20%7C%20discord%20%7C%20feishu%20%7C%20imessage%20%7C%20qq-2563eb"><img src="https://img.shields.io/badge/channels-telegram%20%7C%20discord%20%7C%20feishu%20%7C%20imessage%20%7C%20qq-2563eb" alt="Channels"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-green" alt="GPL-3.0"></a>
</p>

> Documentation:
> [English docs](https://omicclaw.readthedocs.io/en/) |
> [中文文档](https://omicclaw.readthedocs.io/zh-cn/)

---

## What This Repository Is

This repository is now the standalone web and gateway application behind **OmicClaw**.

If you want the full product walkthrough, use the Read the Docs links above instead of treating this README as an operations manual.

This repository is published and installed as **OmicClaw**.

In practice, this repo is the part of OmicClaw that provides:

- the authenticated web entrypoint
- the gateway UI for managing channels
- the browser workspace for files, notebooks, terminals, and code execution
- the frontend and backend glue between OmicVerse analysis flows and agent-driven workflows

If `omicverse` is the analysis engine and `omicclaw` is the skill and workflow layer, this repository is the **interactive runtime surface** users actually open.

---

## What OmicClaw Provides

### 1. Gateway and channel control

OmicClaw is no longer just a static analysis page. It is a gateway-first product that can:

- launch a branded login-protected web workspace
- manage channel lifecycles from the UI
- connect the same runtime to Telegram, Discord, Feishu, iMessage, and QQ
- keep web and channel sessions aligned through the gateway runtime

### 2. Browser workspace

The web application includes:

- a notebook-style code editor with movable cells
- file browser and upload flows
- terminal access
- runtime state and session management
- account/auth flows
- bilingual interface support

### 3. OmicVerse analysis interface

The product still exposes the OmicVerse analysis experience, including:

- preprocessing and QC
- visualization and clustering
- annotation and downstream analysis
- notebook execution and script-oriented workflows

The difference is that this analysis interface now lives inside the broader **OmicClaw** application shell rather than being documented as a standalone tutorial site.

---

## Installation

### Recommended product install

Install the OmicVerse runtime together with the web application:

```bash
pip install -U "omicverse[jarvis]" omicclaw
```

### Install from source

```bash
git clone https://github.com/Starlitnightly/omicclaw.git
cd omicclaw
pip install -e .
```

Current names:

- GitHub repository: `omicclaw`
- PyPI package: `omicclaw`
- Python package: `omicclaw`

---

## Launch Modes

There are now three common ways to launch the OmicClaw experience:

### Recommended: branded OmicClaw entry

```bash
omicclaw
```

Use this when you want the full OmicClaw-branded gateway with forced login behavior.

### Generic gateway entry

```bash
omicverse gateway
```

Use this when you want the same runtime without the OmicClaw-branded launcher name.

### Standalone web launcher from this repository

```bash
omicclaw
```

Use this when you are working directly with the standalone web package or developing the gateway UI itself.

---

## Where This Repo Fits

The current OmicClaw stack is split across three layers:

| Layer | Responsibility |
| --- | --- |
| `omicverse` | analysis engine, CLI entrypoints, channel runtime integration |
| `omicclaw` | skill library and workflow grounding for agent/code generation |
| `omicclaw` | OmicClaw web UI, gateway backend, account flows, browser workspace |

This repository should therefore be read as the **UI and gateway runtime** part of OmicClaw.

---

## Development Notes

Useful commands when working on this repository:

```bash
pip install -e .
omicclaw --help
```

If you are validating the full OmicClaw product flow, pair this repository with the main OmicVerse repo and launch through:

```bash
omicclaw
```

or:

```bash
omicverse gateway
```

---

## Repository Layout

```text
.
├── app.py
├── gateway/
├── routes/
├── services/
├── static/
├── single_cell_analysis_standalone.html
├── start_server.py
└── pyproject.toml
```

Key areas:

- `gateway/`: gateway routes, channel state, runtime coordination
- `services/`: backend services used by the workspace
- `static/`: frontend assets
- `single_cell_analysis_standalone.html`: the main OmicClaw application shell
- `start_server.py`: standalone launcher for this package

---

## Status

This repository should now be treated as **OmicClaw's web application**.
