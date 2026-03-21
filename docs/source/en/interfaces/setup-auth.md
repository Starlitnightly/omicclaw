# OmicClaw Setup and Auth

## Install

```bash
pip install -U omicclaw
```

For local development:

```bash
pip install -e .
```

For macOS iMessage support:

```bash
brew install steipete/tap/imsg
```

## First-Run Setup Wizard

Run the interactive setup wizard to configure the runtime and persist auth state:

```bash
omicclaw --setup --setup-language en
```

## Persisted Config

Runtime state lives in:

```text
~/.ovjarvis/
├── config.json
├── auth.json
├── workspace/
├── sessions/
└── memory/
```

Override the default paths at launch:

```bash
omicclaw \
  --config-file ~/.ovjarvis/config.json \
  --auth-file   ~/.ovjarvis/auth.json
```

## Auth Sources

The runtime accepts credentials from multiple sources:

| Source | How to use |
|--------|-----------|
| Environment variable | `export ANTHROPIC_API_KEY="sk-..."` |
| Setup wizard | Run `omicclaw --setup` and follow the prompts |
| `--api-key` flag | Pass the key directly on the command line |
| Custom endpoint | `--endpoint https://your-proxy.example.com/v1` |

Supported providers: **Anthropic Claude**, **OpenAI**, **Gemini**, and any OpenAI-compatible endpoint.

## Common Runtime Flags

| Flag | Description |
|------|-------------|
| `--channel` | Message channel: `telegram`, `feishu`, `imessage`, `qq` |
| `--model` | LLM model name, e.g. `claude-opus-4-6`, `gpt-4o` |
| `--api-key` | Explicit provider API key |
| `--endpoint` | Custom OpenAI-compatible base URL |
| `--auth-mode` | `environment` / `saved_api_key` / `no_auth` |
| `--session-dir` | Session root directory |
| `--max-prompts` | Prompt quota before kernel restart (`0` = disabled) |
| `--web-host` / `--web-port` | Web server bind settings |
| `--no-browser` | Disable browser auto-open on launch |
| `--remote` | Bind to loopback only (for SSH-tunnel deployments) |
| `--verbose` | Enable detailed logs |

## Usage Examples

Standard launch:

```bash
omicclaw
```

Launch with a Telegram channel and Claude:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
omicclaw --channel telegram --token "$TELEGRAM_BOT_TOKEN" --model claude-opus-4-6
```

Feishu with WebSocket connection mode:

```bash
omicclaw --channel feishu --feishu-connection-mode websocket
```

## Related Pages

- [Launch Modes](launch-modes.md)
- [Quickstart](../getting-started/quickstart.md)
