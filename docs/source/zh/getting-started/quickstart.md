---
orphan: true
---

# OmicClaw 快速上手

从安装到启动 OmicClaw 的最快路径。

## 1. 安装

```bash
pip install -U omicclaw
```

## 2. 启动

```bash
omicclaw
```

服务默认在 `http://localhost:5050` 启动（端口被占用时自动顺延至 5051、5052 …）。
在浏览器中打开该地址即可进入工作区。

## 3. 频道集成模式

同时启动工作区和 Telegram 频道：

```bash
omicclaw --channel telegram --token "$TELEGRAM_BOT_TOKEN"
```

可将 `telegram` 替换为 `discord`、`feishu`、`imessage` 或 `qq`。

## 4. 首次配置向导

如需持久化配置和认证状态：

```bash
omicclaw --setup --setup-language zh
```

运行状态存储在：

```text
~/.ovjarvis/
├── config.json
├── auth.json
├── workspace/
├── sessions/
└── memory/
```

## 5. 远程模式

在远程服务器上启动：

```bash
omicclaw --remote --no-debug
```

在本地创建 SSH 隧道：

```bash
ssh -L 5050:127.0.0.1:5050 username@your-server.com -N
```

在本地浏览器中打开 `http://localhost:5050`。

## 6. 下一步

- [工作区图文教程](../interfaces/workspace.md)
- [设置与认证](../interfaces/setup-auth.md)
- [启动模式](../interfaces/launch-modes.md)
