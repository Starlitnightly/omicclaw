---
orphan: true
---

# OmicClaw 启动模式

## 标准启动

```bash
omicclaw
```

在 `http://localhost:5050` 启动标准 OmicClaw Web 工作区。

## 频道集成模式

同时启动工作区和消息频道：

```bash
omicclaw --channel telegram --token "$TELEGRAM_BOT_TOKEN"
```

支持的频道：`telegram`、`feishu`、`imessage`、`qq`。

```bash
omicclaw --channel feishu --feishu-connection-mode websocket
```

## 远程访问模式

在远程机器上绑定本地回环地址：

```bash
omicclaw --remote --no-debug
```

在本地转发端口：

```bash
ssh -L 5050:127.0.0.1:5050 username@your-server.com -N
```

在本地浏览器打开 `http://localhost:5050`。

## 后台持久运行

关闭终端后保持 OmicClaw 运行：

```bash
nohup omicclaw --remote --no-debug > omicclaw.log 2>&1 &
```

## 如何选择

| 目标 | 命令 |
|------|------|
| 日常使用 | `omicclaw` |
| 接入消息频道 | `omicclaw --channel <频道名>` |
| 远程服务器部署 | `omicclaw --remote --no-debug` |
| 后台进程 | `nohup omicclaw ... &` |

## 相关页面

- [设置与认证](setup-auth.md)
- [快速上手](../getting-started/quickstart.md)
