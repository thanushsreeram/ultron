from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    nvidia_api_key: str
    nvidia_base_url: str
    nvidia_model: str
    memory_file: Path
    workspace: Path
    storage_dir: Path
    allow_outside_workspace: bool
    voice_rate: int
    language_default: str
    default_browser: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    imap_host: str
    imap_port: int
    imap_user: str
    imap_password: str


def _as_bool(value: str, default: bool = False) -> bool:
    if value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    memory_file = Path(
        os.getenv("ULTRON_MEMORY_FILE", str(PROJECT_ROOT / "data" / "memory.txt"))
    ).expanduser()
    workspace = Path(
        os.getenv("ULTRON_WORKSPACE", str(PROJECT_ROOT / "workspace"))
    ).expanduser()
    storage_dir = Path(
        os.getenv("ULTRON_STORAGE_DIR", str(PROJECT_ROOT / "data" / "storage"))
    ).expanduser()
    if not memory_file.is_absolute():
        memory_file = PROJECT_ROOT / memory_file
    if not workspace.is_absolute():
        workspace = PROJECT_ROOT / workspace
    if not storage_dir.is_absolute():
        storage_dir = PROJECT_ROOT / storage_dir
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    storage_dir.mkdir(parents=True, exist_ok=True)
    memory_file.touch(exist_ok=True)

    return Settings(
        nvidia_api_key=os.getenv("NVIDIA_API_KEY", "").strip(),
        nvidia_base_url=os.getenv(
            "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
        ).rstrip("/"),
        nvidia_model=os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"),
        memory_file=memory_file.resolve(),
        workspace=workspace.resolve(),
        storage_dir=storage_dir.resolve(),
        allow_outside_workspace=_as_bool(
            os.getenv("ULTRON_ALLOW_OUTSIDE_WORKSPACE", "false")
        ),
        voice_rate=int(os.getenv("ULTRON_VOICE_RATE", "180")),
        language_default=os.getenv("ULTRON_LANGUAGE", "English").strip() or "English",
        default_browser=os.getenv("ULTRON_DEFAULT_BROWSER", "comet").strip() or "comet",
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")),
        imap_host=os.getenv("IMAP_HOST", ""),
        imap_port=int(os.getenv("IMAP_PORT", "993")),
        imap_user=os.getenv("IMAP_USER", ""),
        imap_password=os.getenv("IMAP_PASSWORD", ""),
    )
