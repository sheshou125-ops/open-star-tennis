"""配置：全部从环境变量读取，密钥不要写死在代码里。"""
import os


# ---- 飞书自建应用 ----
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
# 事件订阅里的「Verification Token」，用于校验请求来源（可选但推荐）
FEISHU_VERIFICATION_TOKEN = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")
# 事件订阅里的「Encrypt Key」，只有在开启了加密推送时才需要填
FEISHU_ENCRYPT_KEY = os.environ.get("FEISHU_ENCRYPT_KEY", "")
# 飞书：https://open.feishu.cn ；Lark（国际版）：https://open.larksuite.com
FEISHU_BASE_URL = os.environ.get("FEISHU_BASE_URL", "https://open.feishu.cn")

# ---- Claude API ----
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")
# 系统提示词：定义机器人的人设与回答风格
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "你是一个运行在飞书里的智能助手，由 Claude 提供能力。"
    "回答简洁、清晰、友好，默认使用中文。",
)

# 每个会话保留多少轮历史（user+assistant 各算一条）
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "20"))


def assert_config() -> None:
    """启动时检查必填项，缺了就直接报错，避免运行到一半才发现。"""
    missing = [
        name
        for name in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "ANTHROPIC_API_KEY")
        if not globals()[name]
    ]
    if missing:
        raise RuntimeError(
            "缺少必填环境变量: " + ", ".join(missing) + "（请参考 .env.example 配置）"
        )
