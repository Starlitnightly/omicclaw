# Docs Deployment

This repository is configured for:

- GitHub Pages, deployed from GitHub Actions
- Read the Docs English project
- Read the Docs Simplified Chinese translation project

## GitHub Pages

The workflow is defined in `.github/workflows/docs.yml`.

Required repository setting:

1. Open `Settings -> Pages`.
2. Set `Source` to `GitHub Actions`.

The workflow builds `docs/source` with the default Sphinx config and deploys `docs/_build/dirhtml`.

## Read the Docs

### English project

Create or import the main Read the Docs project from:

- Repository: `Starlitnightly/omicclaw`
- Language: `English`
- Config file: `.readthedocs.yaml`

This uses `docs/source/conf_en.py`, so the main Read the Docs site is English-first.

### Chinese project

Create a second Read the Docs project from the same repository:

- Repository: `Starlitnightly/omicclaw`
- Language: `Chinese (Simplified)`
- Custom config path: `docs/readthedocs-zh/.readthedocs.yaml`

This uses `docs/source/conf_zh.py`, so the translation project builds only the Chinese tree.

### Enable bilingual mode on Read the Docs

After both projects exist:

1. Open the English project in Read the Docs.
2. Go to `Admin -> Translations`.
3. Add the Chinese project as the translation for Simplified Chinese.

That translation relationship is what enables the Read the Docs language switcher and translation-aware routing.

## GitHub Actions -> Read the Docs trigger

The workflow can trigger both Read the Docs projects after a successful push to `main`.

Configure these repository settings:

- Secret: `READTHEDOCS_TOKEN`
- Variable: `READTHEDOCS_EN_PROJECT`
- Variable: `READTHEDOCS_ZH_PROJECT`
- Optional variable: `READTHEDOCS_API_BASE`

For Read the Docs Community, leave `READTHEDOCS_API_BASE` unset or use:

- `https://app.readthedocs.org/api/v3`

For Read the Docs for Business, use:

- `https://app.readthedocs.com/api/v3`

Example project variables:

- `READTHEDOCS_EN_PROJECT=omicclaw`
- `READTHEDOCS_ZH_PROJECT=omicclaw-zh`
