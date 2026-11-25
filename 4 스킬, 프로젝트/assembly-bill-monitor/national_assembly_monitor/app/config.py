"""설정 로드: .env(인증키 등)와 config/keywords.yaml(관심 키워드 등)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip().strip('"').strip("'")
    return values


@dataclass
class Settings:
    assembly_api_key: str = ""
    assembly_api_base_url: str = "https://open.assembly.go.kr/portal/openapi/"
    likms_base_url: str = "https://likms.assembly.go.kr/bill/bi"
    database_path: Path = ROOT / "data" / "bills.db"
    keywords_file: Path = ROOT / "config" / "keywords.yaml"
    api_timeout: float = 30.0
    api_retry_waits: tuple[float, ...] = (2.0, 5.0)  # 1차 실패 후 2초, 2차 실패 후 5초
    keywords: list[str] = field(default_factory=list)
    age: int = 22
    new_days: int = 7
    detail_delay_seconds: float = 0.5
    auto_sync: bool = False
    sync_interval_minutes: int = 60
    save_raw_response: bool = False


def load_settings() -> Settings:
    env = {**_load_env(ROOT / ".env"), **{k: v for k, v in os.environ.items() if k.startswith("ASSEMBLY_")}}
    s = Settings()
    s.assembly_api_key = env.get("ASSEMBLY_API_KEY", "")
    if env.get("ASSEMBLY_SAMPLE_MODE") == "1":  # 개발·점검용: 키 없이 샘플(키워드당 5건)만 조회
        s.assembly_api_key = ""
    if env.get("ASSEMBLY_API_BASE_URL"):
        s.assembly_api_base_url = env["ASSEMBLY_API_BASE_URL"]
    if env.get("ASSEMBLY_DATABASE_PATH"):
        s.database_path = Path(env["ASSEMBLY_DATABASE_PATH"])
    if env.get("ASSEMBLY_KEYWORDS_FILE"):
        s.keywords_file = Path(env["ASSEMBLY_KEYWORDS_FILE"])

    data = {}
    if s.keywords_file.exists():
        data = yaml.safe_load(s.keywords_file.read_text(encoding="utf-8")) or {}
    s.keywords = [str(k).strip() for k in data.get("keywords") or [] if str(k).strip()]
    s.age = int(data.get("age", s.age))
    s.new_days = int(data.get("new_days", s.new_days))
    s.detail_delay_seconds = float(data.get("detail_delay_seconds", s.detail_delay_seconds))
    s.auto_sync = bool(data.get("auto_sync", s.auto_sync))
    s.sync_interval_minutes = int(data.get("sync_interval_minutes", s.sync_interval_minutes))
    s.save_raw_response = bool(data.get("save_raw_response", s.save_raw_response))
    return s
