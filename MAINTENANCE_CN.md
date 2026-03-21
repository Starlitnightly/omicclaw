# 维护与子模块同步指南

当前 `omicverse-web` 是一个独立仓库，同时也被主仓库 `omicverse` 作为 git 子模块引用。

## 1. 仓库关系

- 独立仓库：`analysis/omicverse-web`
- 主仓库：`analysis/omicverse`
- 主仓库中的子模块路径：`omicverse/omicverse_web`

推荐工作流：

1. 先在 `omicverse-web` 独立仓库中开发。
2. 在 `omicverse-web` 中提交并推送。
3. 回到 `omicverse` 主仓库更新子模块指针。

## 2. 在 `omicverse-web` 中日常开发

先进入独立仓库：

```bash
cd /Users/fernandozeng/Desktop/analysis/omicverse-web
git status
git checkout main
git pull origin main
```

修改完成后：

```bash
git add -A
git commit -m "Describe the web update"
git push origin main
```

## 3. 把最新提交同步回 `omicverse`

在 `omicverse-web` 推送后，回到主仓库更新子模块指针：

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

如果 `.gitmodules` 没有变化，只需要 `git add omicverse_web`。

## 4. 其他人在主仓库中如何同步子模块

别人拉取主仓库后，应该同时更新子模块：

```bash
cd /Users/fernandozeng/Desktop/analysis/omicverse
git pull --recurse-submodules
git submodule update --init --recursive
```

如果子模块目录已经存在，但版本落后：

```bash
cd /Users/fernandozeng/Desktop/analysis/omicverse/omicverse_web
git checkout main
git pull origin main
cd ..
git add omicverse_web
```

## 5. 从零克隆主仓库

如果要连同 `omicverse_web` 一起克隆：

```bash
git clone --recurse-submodules https://github.com/Starlitnightly/omicverse.git
```

如果之前没有带子模块：

```bash
cd omicverse
git submodule update --init --recursive
```

## 6. 常见问题

- 不要只在 `omicverse` 里更新子模块指针，却忘了先把真正的代码提交推送到 `omicverse-web`。
- 不要长期直接在 `omicverse/omicverse_web` 里开发，`analysis/omicverse-web` 才是主开发仓库。
- 如果子模块目录处于 detached HEAD，先在子模块里执行 `git checkout main`，再继续 `git pull`。
