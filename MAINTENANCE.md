# Maintenance Guide

This repository is maintained as a standalone project and is also consumed from the main `omicverse` repository as a git submodule.

## 1. Repository Relationship

- Standalone repo: `analysis/omicverse-web`
- Parent repo: `analysis/omicverse`
- Submodule path inside parent repo: `omicverse/omicverse_web`

The normal rule is:

1. Make changes in `omicverse-web`.
2. Commit and push in `omicverse-web`.
3. Update the submodule pointer in `omicverse`.

## 2. Daily Development In `omicverse-web`

Work in the standalone repository first:

```bash
cd /Users/fernandozeng/Desktop/analysis/omicverse-web
git status
git checkout main
git pull origin main
```

After editing:

```bash
git add -A
git commit -m "Describe the web update"
git push origin main
```

## 3. Sync The New Commit Back To `omicverse`

After you push `omicverse-web`, update the parent repository's submodule pointer:

```bash
cd /Users/fernandozeng/Desktop/analysis/omicverse
git submodule update --init --recursive
cd omicverse_web
git checkout main
git pull origin main
cd ..
git add omicverse_web .gitmodules
git commit -m "Update omicverse_web submodule"
git push
```

If `.gitmodules` did not change, `git add omicverse_web` is enough.

## 4. How Another Clone Updates The Submodule

When someone pulls the main repository, they should also refresh the submodule:

```bash
cd /Users/fernandozeng/Desktop/analysis/omicverse
git pull --recurse-submodules
git submodule update --init --recursive
```

If the submodule already exists but is behind:

```bash
cd /Users/fernandozeng/Desktop/analysis/omicverse/omicverse_web
git checkout main
git pull origin main
cd ..
git add omicverse_web
```

## 5. Clone From Scratch

To clone the parent repository together with `omicverse_web`:

```bash
git clone --recurse-submodules https://github.com/Starlitnightly/omicverse.git
```

If you already cloned without submodules:

```bash
cd omicverse
git submodule update --init --recursive
```

## 6. Common Pitfalls

- Do not edit only the submodule pointer in `omicverse` and forget to push the real commit in `omicverse-web`.
- Do not develop long-term inside `omicverse/omicverse_web`; use the standalone `analysis/omicverse-web` repo as the source of truth.
- If `omicverse_web` shows a detached HEAD inside the parent repo, run `git checkout main` inside the submodule before pulling.
