"""AIConfig — 所有可注入的設定。from_env() 從環境變數建立。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# 無預設端點：有 API key 時必須明確指定 VLLM_BASE_URL
DEFAULT_BASE_URL = ""
DEFAULT_MODEL = ""


def load_project_env() -> None:
    """從 cwd 或套件往上找專案根目錄的 .env，不覆蓋已存在的環境變數。"""
    seen: set[Path] = set()
    env_path: Path | None = None
    for start in (Path.cwd(), Path(__file__).resolve().parent):
        for directory in (start, *start.parents):
            resolved = directory.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidate = resolved / ".env"
            if candidate.is_file():
                env_path = candidate
                break
        if env_path is not None:
            break
    if env_path is None:
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        trimmed = raw.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        eq_idx = trimmed.find("=")
        if eq_idx == -1:
            continue
        key = trimmed[:eq_idx].strip()
        value = trimmed[eq_idx + 1 :].strip()
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class AIConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    max_tokens: int = 4096
    timeout: float = 120.0
    system_prompt: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "AIConfig":
        load_project_env()
        api_key = os.getenv("VLLM_API_KEY", "")
        base_url = os.getenv("VLLM_BASE_URL", DEFAULT_BASE_URL)
        model = os.getenv("VLLM_MODEL", DEFAULT_MODEL)
        if api_key and not base_url:
            raise ValueError(
                "已設定 VLLM_API_KEY 但未設定 VLLM_BASE_URL。"
                "請指定 OpenAI 相容端點（例如 https://your-host/v1）。"
            )
        return cls(api_key=api_key, base_url=base_url, model=model)
