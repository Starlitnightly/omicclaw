<p align="center">
  <img src="https://raw.githubusercontent.com/Starlitnightly/ImageStore/main/omicverse_img/Gemini_Generated_Image_xefpyexefpyexefp.png" width="400" alt="OmicClaw">
</p>

<p align="center">
  <strong>OmicClaw</strong><br>
  一个以 gateway 为核心的 OmicVerse 工作台，统一承载 Web UI、消息通道、Notebook 与 agent 工作流。
</p>

<p align="center">
  <a href="https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white"><img src="https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white" alt="Python 3.8+"></a>
  <a href="https://img.shields.io/badge/runtime-web%20gateway-0f766e"><img src="https://img.shields.io/badge/runtime-web%20gateway-0f766e" alt="Web gateway"></a>
  <a href="https://img.shields.io/badge/channels-telegram%20%7C%20feishu%20%7C%20imessage%20%7C%20qq-2563eb"><img src="https://img.shields.io/badge/channels-telegram%20%7C%20feishu%20%7C%20imessage%20%7C%20qq-2563eb" alt="Channels"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-green" alt="GPL-3.0"></a>
</p>

> 文档入口：
> [English docs](https://omicclaw.readthedocs.io/en/) |
> [中文文档](https://omicclaw.readthedocs.io/zh-cn/)

---

## 这个仓库现在是什么

这个仓库现在就是 **OmicClaw 的独立 Web / Gateway 应用**。

如果你想看完整产品文档，请直接使用上面的 Read the Docs 链接，而不是把这份 README 当作步骤手册。

这个仓库现在直接以 **OmicClaw** 的名字发布和安装。

这个仓库现在主要负责：

- 登录保护后的 Web 入口
- gateway 页面与 channel 生命周期管理
- 浏览器内文件、Notebook、终端与代码执行工作区
- OmicVerse 分析流程与 agent 工作流之间的前后端衔接

如果说 `omicverse` 是分析引擎，`omicclaw` 是技能和工作流层，那么这个仓库就是 OmicClaw 面向用户的 **交互运行界面**。

---

## OmicClaw 现在提供什么

### 1. Gateway 与消息通道控制

OmicClaw 不再只是一个静态分析页面，而是一个 gateway-first 产品，可以：

- 启动带登录约束的 OmicClaw Web 工作台
- 在界面里管理 channel 的启动、停止与状态
- 将同一个 runtime 连接到 Telegram、Feishu、iMessage、QQ
- 让 Web 与消息通道共享同一套 gateway 运行时

### 2. 浏览器工作区

当前 Web 应用提供：

- 类 notebook 的代码编辑器，并支持 cell 上下移动
- 文件浏览与上传
- 浏览器终端
- session 与运行状态管理
- account / auth 流程
- 中英文双语界面

### 3. OmicVerse 分析界面

OmicVerse 原有的分析能力仍然保留，包括：

- 预处理与 QC
- 可视化与聚类
- 注释与下游分析
- Notebook 执行与脚本工作流

区别在于，这些分析能力现在不再被单独描述成一个 “Web 教程网站”，而是被整合进 **OmicClaw** 的统一产品外壳里。

---

## 安装

### 推荐安装方式

将 OmicVerse 运行时与 Web 应用一起安装：

```bash
pip install -U "omicverse[jarvis]" omicclaw
```

### 从源码安装

```bash
git clone https://github.com/Starlitnightly/omicclaw.git
cd omicclaw
pip install -e .
```

当前名称为：

- GitHub 仓库：`omicclaw`
- PyPI 包：`omicclaw`
- Python 包：`omicclaw`

---

## 启动方式

现在有三种常见的启动入口：

### 推荐入口：OmicClaw 品牌启动

```bash
omicclaw
```

这是最推荐的入口，会进入 OmicClaw 品牌化的 gateway，并启用强制登录流程。

### 通用 gateway 入口

```bash
omicverse gateway
```

当你需要相同 runtime，但不强调 OmicClaw 品牌入口时，使用这个命令。

### 本仓库自带的独立 Web 启动器

```bash
omicclaw
```

当你直接开发这个仓库，或者只安装了独立 web 包时，可以用这个命令启动。

---

## 这个仓库在整体架构里的位置

当前 OmicClaw 体系大致分成三层：

| 层 | 责任 |
| --- | --- |
| `omicverse` | 分析引擎、CLI 入口、channel runtime 集成 |
| `omicclaw` | skill 库、agent workflow grounding、代码生成支撑 |
| `omicclaw` | OmicClaw 的 Web UI、gateway backend、账号流程、浏览器工作区 |

所以这个仓库应当被理解为 **OmicClaw 的 UI 与 gateway runtime 仓库**。

---

## 开发说明

在这个仓库里常用的命令：

```bash
pip install -e .
omicclaw --help
```

如果你要验证完整的 OmicClaw 产品链路，建议配合主仓库后，通过以下入口启动：

```bash
omicclaw
```

或者：

```bash
omicverse gateway
```

---

## 仓库结构

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

关键目录：

- `gateway/`：gateway 路由、channel 状态与运行时协调
- `services/`：工作区后端服务
- `static/`：前端静态资源
- `single_cell_analysis_standalone.html`：OmicClaw 主应用壳
- `start_server.py`：本仓库的独立启动器

---

## 当前定位

这个仓库现在应该被直接视为 **OmicClaw 的 Web 应用仓库**。
