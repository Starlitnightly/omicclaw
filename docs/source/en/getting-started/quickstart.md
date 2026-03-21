# OmicClaw Quickstart

The fastest path from installation to a working OmicClaw session.

## 1. Install

```bash
pip install -U omicclaw
```

## 2. Launch

```bash
omicclaw
```

The server starts at `http://localhost:5050` (auto-increments to 5051, 5052 … if the port is busy).
Open that URL in your browser to access the workspace.

## 3. Channel-Backed Mode

Start the workspace alongside a Telegram channel:

```bash
omicclaw --channel telegram --token "$TELEGRAM_BOT_TOKEN"
```

Replace `telegram` with `feishu`, `imessage`, or `qq` as needed.

## 4. First-Run Setup Wizard

To persist config and auth state:

```bash
omicclaw --setup --setup-language en
```

Runtime state is stored under:

```text
~/.ovjarvis/
├── config.json
├── auth.json
├── workspace/
├── sessions/
└── memory/
```

## 5. Remote Mode

On the remote server:

```bash
omicclaw --remote --no-debug
```

On your local machine, create an SSH tunnel:

```bash
ssh -L 5050:127.0.0.1:5050 username@your-server.com -N
```

Open `http://localhost:5050` in your local browser.

## 6. Next Steps

- [Workspace Tutorial](../interfaces/workspace.md)
- [Setup and Auth](../interfaces/setup-auth.md)
- [Launch Modes](../interfaces/launch-modes.md)
