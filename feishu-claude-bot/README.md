# 飞书 × Claude 机器人

把 Claude 接进飞书：在飞书群里 @ 机器人、或私聊机器人，就能和 Claude 对话。

```
飞书群/私聊  →  飞书自建机器人(webhook)  →  本服务  →  Claude API  →  回复发回飞书
```

## 一、准备工作

1. **飞书自建应用**：到 [飞书开放平台](https://open.feishu.cn) → 创建企业自建应用，记下 `App ID`、`App Secret`。
2. **Claude API Key**：到 [platform.claude.com](https://platform.claude.com) 申请（付费）。

## 二、本地运行

```bash
cd feishu-claude-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # 填入你的密钥
set -a; source .env; set +a # 把 .env 导入环境变量

uvicorn app:app --host 0.0.0.0 --port 8000
```

服务起来后，`GET http://localhost:8000/` 返回 `{"status":"ok"}` 即正常。

## 三、让飞书能回调到你（公网地址）

飞书的事件回调必须能访问到你的服务。本地调试可以用内网穿透：

```bash
# 任选其一，把本地 8000 端口暴露成公网地址
ngrok http 8000
# 或 cloudflared tunnel --url http://localhost:8000
```

拿到公网地址后，回调地址就是 `https://你的域名/feishu/event`。

## 四、在飞书开放平台配置应用

在应用管理后台依次配置：

1. **添加「机器人」能力**：左侧「应用能力」→「机器人」→ 启用。
2. **权限管理**（开通以下权限，然后发布版本）：
   - `im:message`（获取与发送单聊、群组消息）
   - `im:message.group_at_msg`（接收群里 @ 机器人的消息）
   - `im:message.p2p_msg`（接收用户发给机器人的私聊消息）
3. **事件订阅**：
   - 「请求地址」填 `https://你的域名/feishu/event`
   - 填好地址保存时，飞书会发一次 URL 验证握手，本服务会自动应答（无需手动操作）。
   - 把页面上的 **Verification Token** 填到 `.env` 的 `FEISHU_VERIFICATION_TOKEN`；若开启了「加密」，再把 **Encrypt Key** 填到 `FEISHU_ENCRYPT_KEY`，然后重启服务。
   - 添加事件：**接收消息 `im.message.receive_v1`**。
4. **发布应用**：创建版本并发布（企业内可用即可）。

## 五、试一下

- **私聊**：在飞书里搜到你的机器人，直接发消息，它会回复。
- **群聊**：把机器人拉进群，然后 `@机器人 你的问题`（群里默认只在被 @ 时回复）。

## 行为说明 / 可调项

- **群聊只在被 @ 时回复**，私聊总是回复（见 `app.py` 里的判断）。
- **多轮上下文**：按会话在内存里保留最近 `MAX_HISTORY` 轮，服务重启即清空。多实例部署请换成 Redis。
- **去重**：靠飞书 `event_id` 在内存里去重，防止重推导致重复回答。
- **模型**：默认 `claude-opus-4-8`，开启了 adaptive thinking。想更快可在 `claude_client.py` 里调整。

## 部署到生产

- 用 `uvicorn`/`gunicorn` 常驻，前面挂 Nginx 或直接用云厂商的反向代理，确保 HTTPS。
- 密钥用环境变量或密钥管理服务注入，**不要**把 `.env` 提交到仓库。
- 注意飞书要求回调在 ~3 秒内返回；如果 Claude 偶尔较慢，可把 `app.py` 里 `_handle_message` 改成后台任务并先返回 200。
