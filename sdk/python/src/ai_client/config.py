"""AIConfig — 所有可注入的設定。from_env() 從環境變數建立。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_URL = "https://chatapi.ntubimdbirc.tw/v1"
DEFAULT_MODEL = "Gemma4-31B"


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
        return cls(
            api_key=os.getenv("VLLM_API_KEY", ""),
            base_url=os.getenv("VLLM_BASE_URL", DEFAULT_BASE_URL),
            model=os.getenv("VLLM_MODEL", DEFAULT_MODEL),
        )
