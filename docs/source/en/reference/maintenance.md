# Maintenance Guide

This repository is maintained as the standalone `omicclaw` package and is also consumed from the main `omicverse` repository as a git submodule.

## 1. Repository Relationship

- Standalone repo: `analysis/omicclaw`
- Parent repo: `analysis/omicverse`
- Legacy submodule path inside parent repo: `omicverse/omicverse_web`

The normal rule is:

1. Make changes in `omicclaw`.
2. Commit and push in `omicclaw`.
3. Update the submodule pointer in `omicverse`.

## 2. Daily Development In `omicclaw`

Work in the standalone repository first:

```bash
cd /Users/fernandozeng/Desktop/analysis/omicclaw
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

After you push `omicclaw`, update the parent repository's submodule pointer:

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

- Do not edit only the submodule pointer in `omicverse` and forget to push the real commit in `omicclaw`.
- Do not develop long-term inside `omicverse/omicverse_web`; use the standalone `analysis/omicclaw` repo as the source of truth.
- If `omicverse_web` shows a detached HEAD inside the parent repo, run `git checkout main` inside the submodule before pulling.
