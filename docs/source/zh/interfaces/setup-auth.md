---
orphan: true
---

# OmicClaw 设置与认证

## 安装

```bash
pip install -U omicclaw
```

本地开发：

```bash
pip install -e .
```

macOS iMessage 支持：

```bash
brew install steipete/tap/imsg
```

## 首次配置向导

运行交互式向导，配置运行时并持久化认证状态：

```bash
omicclaw --setup --setup-language zh
```

## 持久化配置

运行状态存储在：

```text
~/.ovjarvis/
├── config.json
├── auth.json
├── workspace/
├── sessions/
└── memory/
```

启动时覆盖默认路径：

```bash
omicclaw \
  --config-file ~/.ovjarvis/config.json \
  --auth-file   ~/.ovjarvis/auth.json
```

## 认证来源

运行时支持多种认证方式：

| 方式 | 用法 |
|------|------|
| 环境变量 | `export ANTHROPIC_API_KEY="sk-..."` |
| 配置向导 | 运行 `omicclaw --setup` 并按提示操作 |
| `--api-key` 参数 | 在命令行直接传入密钥 |
| 自定义端点 | `--endpoint https://your-proxy.example.com/v1` |

支持的服务商：**Anthropic Claude**、**OpenAI**、**Gemini** 及任何兼容 OpenAI 格式的端点。

## 常用运行参数

| 参数 | 说明 |
|------|------|
| `--channel` | 消息频道：`telegram`、`feishu`、`imessage`、`qq` |
| `--model` | LLM 模型名称，如 `claude-opus-4-6`、`gpt-4o` |
| `--api-key` | 显式传入服务商 API Key |
| `--endpoint` | 自定义 OpenAI 兼容端点 URL |
| `--auth-mode` | `environment` / `saved_api_key` / `no_auth` |
| `--session-dir` | 会话根目录 |
| `--max-prompts` | 内核重启前的提示词配额（`0` = 禁用） |
| `--web-host` / `--web-port` | Web 服务器绑定设置 |
| `--no-browser` | 禁止启动时自动打开浏览器 |
| `--remote` | 仅监听本地回环（适用于 SSH 隧道部署） |
| `--verbose` | 启用详细日志 |

## 使用示例

标准启动：

```bash
omicclaw
```

带 Telegram 频道和 Claude 启动：

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
omicclaw --channel telegram --token "$TELEGRAM_BOT_TOKEN" --model claude-opus-4-6
```

飞书 WebSocket 模式：

```bash
omicclaw --channel feishu --feishu-connection-mode websocket
```

## 相关页面

- [启动模式](launch-modes.md)
- [快速上手](../getting-started/quickstart.md)
