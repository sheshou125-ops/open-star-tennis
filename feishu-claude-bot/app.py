"""
飞书 ↔ Claude 桥接服务。

消息流向：
  飞书群/私聊 → 飞书机器人 → 本服务(/feishu/event) → Claude API → 把回复发回飞书

启动：
  uvicorn app:app --host 0.0.0.0 --port 8000
"""
import json
import re
from collections import OrderedDict, defaultdict, deque

from fastapi import FastAPI, Request

import config
from claude_client import ask_claude
from feishu_client import decrypt, reply_text, verify_signature

config.assert_config()

app = FastAPI(title="Feishu × Claude Bot")

# 简单的内存去重：飞书在 3 秒内没收到 200 会重推同一事件，靠 event_id 防重复处理。
# 生产环境若多实例部署，建议换成 Redis。
_seen_events: "OrderedDict[str, bool]" = OrderedDict()
_SEEN_MAX = 2000

# 每个会话的对话历史（chat_id -> 最近若干轮）。重启即清空，够用即可。
_history: "defaultdict[str, deque]" = defaultdict(lambda: deque(maxlen=config.MAX_HISTORY))

# 去掉飞书在文本里塞的 @ 占位符，例如 "@_user_1 你好" -> "你好"
_MENTION_RE = re.compile(r"@_user_\d+")


def _already_seen(event_id: str) -> bool:
    if not event_id:
        return False
    if event_id in _seen_events:
        return True
    _seen_events[event_id] = True
    while len(_seen_events) > _SEEN_MAX:
        _seen_events.popitem(last=False)
    return False


@app.get("/")
async def health():
    return {"status": "ok", "service": "feishu-claude-bot"}


@app.post("/feishu/event")
async def feishu_event(request: Request):
    raw = await request.body()
    payload = json.loads(raw)

    # 1) 加密推送：先解密，再校验签名
    if "encrypt" in payload:
        if config.FEISHU_ENCRYPT_KEY:
            sig = request.headers.get("X-Lark-Signature", "")
            ts = request.headers.get("X-Lark-Request-Timestamp", "")
            nonce = request.headers.get("X-Lark-Request-Nonce", "")
            if sig and not verify_signature(ts, nonce, config.FEISHU_ENCRYPT_KEY, raw, sig):
                return {"code": 403, "msg": "签名校验失败"}
        payload = json.loads(decrypt(config.FEISHU_ENCRYPT_KEY, payload["encrypt"]))

    # 2) 配置回调地址时飞书会发的 URL 验证握手
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    header = payload.get("header", {})

    # 3) 校验 Verification Token（明文模式下用它确认来源）
    if config.FEISHU_VERIFICATION_TOKEN:
        token = header.get("token") or payload.get("token")
        if token and token != config.FEISHU_VERIFICATION_TOKEN:
            return {"code": 403, "msg": "token 校验失败"}

    # 4) 事件去重
    if _already_seen(header.get("event_id", "")):
        return {"code": 0}

    # 5) 只处理「收到消息」事件，其余忽略
    if header.get("event_type") == "im.message.receive_v1":
        # 同步处理：在 await ask_claude 期间 FastAPI 不会阻塞其他请求，
        # 但若担心超过飞书 3 秒重推窗口，可改为后台任务 + 立即返回 200。
        await _handle_message(payload)

    return {"code": 0}


async def _handle_message(payload: dict) -> None:
    event = payload.get("event", {})
    message = event.get("message", {})
    chat_id = message.get("chat_id", "")
    message_id = message.get("message_id", "")
    chat_type = message.get("chat_type", "")  # "p2p"(私聊) / "group"(群聊)

    # 群里只在被 @ 时才回复，避免刷屏；私聊则总是回复。
    if chat_type == "group" and not message.get("mentions"):
        return

    if message.get("message_type") != "text":
        await reply_text(message_id, "目前我只能看懂文字消息哦~")
        return

    text = json.loads(message.get("content", "{}")).get("text", "")
    text = _MENTION_RE.sub("", text).strip()
    if not text:
        return

    convo = _history[chat_id]
    convo.append({"role": "user", "content": text})

    try:
        answer = await ask_claude(list(convo))
    except Exception as exc:  # noqa: BLE001 — 把错误回传给用户，方便排查
        await reply_text(message_id, f"调用 Claude 出错了：{exc}")
        return

    convo.append({"role": "assistant", "content": answer})
    await reply_text(message_id, answer)
