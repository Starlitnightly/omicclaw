# OmicClaw Launch Modes

## Standard Launch

```bash
omicclaw
```

Starts the canonical OmicClaw web workspace at `http://localhost:5050`.

## Channel-Backed Mode

Start the workspace alongside a message channel:

```bash
omicclaw --channel telegram --token "$TELEGRAM_BOT_TOKEN"
```

Supported channels: `telegram`, `feishu`, `imessage`, `qq`.

```bash
omicclaw --channel feishu --feishu-connection-mode websocket
```

## Remote Access Mode

Bind to loopback only on a remote machine:

```bash
omicclaw --remote --no-debug
```

Forward the port locally:

```bash
ssh -L 5050:127.0.0.1:5050 username@your-server.com -N
```

Open `http://localhost:5050` in your local browser.

## Background (Persistent) Mode

Keep OmicClaw running after you close the terminal:

```bash
nohup omicclaw --remote --no-debug > omicclaw.log 2>&1 &
```

## How to Choose

| Goal | Command |
|------|---------|
| Normal daily use | `omicclaw` |
| With a message channel | `omicclaw --channel <name>` |
| Remote server deployment | `omicclaw --remote --no-debug` |
| Background process | `nohup omicclaw ... &` |

## Related Pages

- [Setup and Auth](setup-auth.md)
- [Quickstart](../getting-started/quickstart.md)
