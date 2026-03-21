# OmicClaw Installation

## Recommended Install

Install OmicClaw via pip:

```bash
pip install -U omicclaw
```

Using `uv`:

```bash
pip install uv
uv pip install omicclaw
```

## Source Install

For local development:

```bash
git clone https://github.com/Starlitnightly/omicclaw.git
cd omicclaw
pip install -e .
```

## Recommended Environment

Use a dedicated conda environment to avoid conflicting scientific Python dependencies:

```bash
conda create -n omicverse python=3.10
conda activate omicverse
pip install -U omicclaw
```

## Optional: Channel-Specific Prerequisites

For macOS iMessage workflows:

```bash
brew install steipete/tap/imsg
```

## Verify the Install

```bash
python -c "import omicclaw; print('omicclaw ok')"
omicclaw --help
```

## Related Reading

- [Quickstart](quickstart.md)
- [Setup and Auth](../interfaces/setup-auth.md)
