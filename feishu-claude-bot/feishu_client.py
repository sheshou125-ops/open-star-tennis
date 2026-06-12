"""飞书侧的封装：拿 token、发消息、解密加密推送、校验签名。"""
import base64
import hashlib
import json
import time
from typing import Optional

import httpx
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

import config

# tenant_access_token 有有效期（约 2 小时），缓存起来复用，到期前自动刷新。
_token_cache = {"token": "", "expire_at": 0.0}


async def get_tenant_access_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expire_at"] - 60:
        return _token_cache["token"]

    url = f"{config.FEISHU_BASE_URL}/open-apis/auth/v3/tenant_access_token/internal"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            url,
            json={
                "app_id": config.FEISHU_APP_ID,
                "app_secret": config.FEISHU_APP_SECRET,
            },
        )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败: {data}")

    _token_cache["token"] = data["tenant_access_token"]
    _token_cache["expire_at"] = now + data.get("expire", 7200)
    return _token_cache["token"]


async def reply_text(message_id: str, text: str) -> dict:
    """在原消息下回复一条文字（群里会形成话题/引用，体验更好）。"""
    token = await get_tenant_access_token()
    url = f"{config.FEISHU_BASE_URL}/open-apis/im/v1/messages/{message_id}/reply"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "msg_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
        )
    return resp.json()


async def send_text(receive_id: str, text: str, receive_id_type: str = "chat_id") -> dict:
    """主动给某个会话/用户发一条文字消息。"""
    token = await get_tenant_access_token()
    url = (
        f"{config.FEISHU_BASE_URL}/open-apis/im/v1/messages"
        f"?receive_id_type={receive_id_type}"
    )
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
        )
    return resp.json()


def decrypt(encrypt_key: str, encrypt_data: str) -> str:
    """解密飞书加密推送（AES-256-CBC）。仅在事件订阅开启了加密时用到。"""
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    raw = base64.b64decode(encrypt_data)
    iv, ciphertext = raw[:16], raw[16:]
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    pad_len = padded[-1]  # 去掉 PKCS#7 填充
    return padded[:-pad_len].decode("utf-8")


def verify_signature(
    timestamp: str, nonce: str, encrypt_key: str, body: bytes, signature: str
) -> bool:
    """校验飞书请求签名，确认请求确实来自飞书（加密模式下使用）。"""
    digest = hashlib.sha256(
        timestamp.encode() + nonce.encode() + encrypt_key.encode() + body
    ).hexdigest()
    return digest == signature
