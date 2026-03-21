---
orphan: true
---

# OmicClaw 安装指南

## 推荐安装

通过 pip 安装 OmicClaw：

```bash
pip install -U omicclaw
```

使用 `uv`：

```bash
pip install uv
uv pip install omicclaw
```

## 源码安装

本地开发时可从源码安装：

```bash
git clone https://github.com/Starlitnightly/omicclaw.git
cd omicclaw
pip install -e .
```

## 推荐环境

建议使用独立的 conda 环境，以避免科学计算依赖冲突：

```bash
conda create -n omicverse python=3.10
conda activate omicverse
pip install -U omicclaw
```

## 可选：消息频道依赖

如需支持 macOS iMessage 工作流：

```bash
brew install steipete/tap/imsg
```

## 验证安装

```bash
python -c "import omicclaw; print('omicclaw ok')"
omicclaw --help
```

## 相关阅读

- [快速上手](quickstart.md)
- [设置与认证](../interfaces/setup-auth.md)
