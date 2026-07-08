"""
HSSwitch 설정 저장/불러오기.

하나의 JSON 파일에 다음 두 가지를 함께 저장한다:
- profiles: 재생+녹음 장치 조합 프로필 목록
- aliases: 장치 ID -> 별칭(alias) 매핑 (Windows가 붙인 장치 이름 대신 표시)
"""

import json
import os

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HSSwitch")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

_DEFAULT_CONFIG = {"profiles": [], "aliases": {}, "theme": "system"}


def _ensure_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> dict:
    _ensure_dir()
    if not os.path.exists(CONFIG_PATH):
        return dict(_DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("profiles", [])
        data.setdefault("aliases", {})
        data.setdefault("theme", "system")
        return data
    except Exception:
        return dict(_DEFAULT_CONFIG)


def save_config(config: dict):
    _ensure_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ---------- 프로필 ----------
def load_profiles() -> list[dict]:
    return load_config()["profiles"]


def save_profiles(profiles: list[dict]):
    config = load_config()
    config["profiles"] = profiles
    save_config(config)


def add_profile(profile: dict):
    profiles = load_profiles()
    profiles.append(profile)
    save_profiles(profiles)


def update_profile(index: int, profile: dict):
    profiles = load_profiles()
    if 0 <= index < len(profiles):
        profiles[index] = profile
        save_profiles(profiles)


def delete_profile(index: int):
    profiles = load_profiles()
    if 0 <= index < len(profiles):
        profiles.pop(index)
        save_profiles(profiles)


# ---------- 장치 별칭 ----------
def load_aliases() -> dict:
    return load_config()["aliases"]


def set_alias(device_id: str, alias: str | None):
    config = load_config()
    if alias:
        config["aliases"][device_id] = alias
    else:
        config["aliases"].pop(device_id, None)
    save_config(config)


def get_display_name(device_id: str, fallback_name: str) -> str:
    aliases = load_aliases()
    return aliases.get(device_id) or fallback_name


# ---------- 테마 ----------
def load_theme() -> str:
    """'system' / 'light' / 'dark' 중 하나."""
    return load_config().get("theme", "system")


def set_theme(theme: str):
    if theme not in ("system", "light", "dark"):
        theme = "system"
    config = load_config()
    config["theme"] = theme
    save_config(config)
