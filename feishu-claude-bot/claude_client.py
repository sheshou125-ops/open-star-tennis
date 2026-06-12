"""Claude 侧的封装：把对话历史发给 Claude API，取回文字回复。"""
from typing import List, Dict

import anthropic

import config

# 异步客户端，配合 FastAPI 的事件循环使用。
_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)


async def ask_claude(messages: List[Dict[str, str]]) -> str:
    """
    messages: [{"role": "user"/"assistant", "content": "..."}, ...]
    返回：Claude 的纯文字回复。
    """
    response = await _client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4096,
        system=config.SYSTEM_PROMPT,
        thinking={"type": "adaptive"},  # 让模型按需思考，复杂问题答得更好
        messages=messages,
    )

    # 安全分类器可能拒答（HTTP 200 但 stop_reason 为 refusal）
    if response.stop_reason == "refusal":
        return "抱歉，这个请求我没法处理。"

    # 只取文本块拼成回复（thinking 块的可见文本默认为空，直接跳过）
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip() or "（模型没有返回内容）"
