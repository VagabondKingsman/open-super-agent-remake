import os
from pathlib import Path
import yaml
from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / os.environ.get("OSA_CONFIG", "config.yaml")).read_text())

# 数据目录：数据库、密钥、自己加的应用清单、工作目录都在这里，默认是仓库里的 data/。
# 桌面版的代码目录是只读的，用 OSA_DATA_DIR 指到用户自己的目录；这时相对路径的 memory.db 只取文件名，放进这个目录
DATA = Path(os.environ["OSA_DATA_DIR"]).expanduser() if os.environ.get("OSA_DATA_DIR") else ROOT / "data"


def _db_path() -> Path:
    db = Path(CFG["memory"]["db"])
    if db.is_absolute():
        return db
    return DATA / db.name if os.environ.get("OSA_DATA_DIR") else ROOT / db


DB_PATH = _db_path()


def db_outside_data_dir() -> bool:
    """OSA_DATA_DIR is set but an absolute memory.db points elsewhere (OSA-015). Kept as-is; startup warns."""
    if not os.environ.get("OSA_DATA_DIR"):
        return False
    return not DB_PATH.resolve().is_relative_to(DATA.resolve())


def client_for(role: str) -> tuple[AsyncOpenAI, str]:
    """返回某个角色（router/worker/reviewer/filter）对应的客户端和模型名。"""
    from . import providers
    r = CFG["roles"][role]
    return providers.client(r["provider"]), r["model"]


def _spec_kwargs(spec: dict) -> dict:
    """一份角色设置（或它的备用模型）要带的额外参数：thinking: false 关掉思考模式，reasoning_effort 指定强度。"""
    kw = {}
    if spec.get("thinking") is False:
        kw["extra_body"] = {"thinking": {"type": "disabled"}}
    if spec.get("reasoning_effort"):
        kw["reasoning_effort"] = spec["reasoning_effort"]
    # C26：思考的 token 也算在输出的上限里。不给上限时，服务端的默认值可能很小，思考一长，
    # 正文就被截在 half（finish_reason=length），模型只好再说一遍——一条消息里同一段话两次。
    if spec.get("max_tokens"):
        kw["max_tokens"] = int(spec["max_tokens"])
    return kw


def call_kwargs(role: str) -> dict:
    """某个角色调用模型时的额外参数。config.yaml 里可以给角色加 thinking: false 或 reasoning_effort。"""
    return _spec_kwargs(CFG["roles"][role])


def fallback_for(role: str, model: str = "") -> tuple[AsyncOpenAI, str, dict] | None:
    """这个角色的备用模型（config.yaml 的 roles.<role>.fallback: {model: ..., provider: ...}），返回（客户端、模型名、参数）。

    主模型连着卡住、重来也没用的时候换它把这一轮做完，任务不至于整个失败。没配、配的还是主模型、
    或者那个服务不在 providers 里，都返回 None。备用模型可以自己写 thinking / reasoning_effort。"""
    from . import providers
    spec = CFG["roles"].get(role) or {}
    fb = spec.get("fallback") or {}
    if not fb.get("model") or fb["model"] == (model or spec.get("model")):
        return None
    provider = fb.get("provider") or spec.get("provider")
    if provider not in (CFG.get("providers") or {}):
        return None
    return providers.client(provider), fb["model"], _spec_kwargs(fb)
