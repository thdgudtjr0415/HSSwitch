"""
HSSwitch 설정(%APPDATA%\\HSSwitch\\config.json) 저장/불러오기.

- profiles: 재생+녹음 장치 조합 프로필 목록
- aliases: 장치 ID -> 별칭 (Windows 장치 이름 대신 앱 안에서만 표시)
- theme, auto_update_check, last_profile: 팝업 테마, 시작 시 업데이트 확인 여부, 마지막으로 적용한 프로필 이름
"""

import json
import os

import icon_store

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HSSwitch")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

_DEFAULT_CONFIG = {"profiles": [], "aliases": {}, "theme": "system", "auto_update_check": True}


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
        data.setdefault("auto_update_check", True)
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
        old_image = profiles[index].get("icon_image")
        profiles[index] = profile
        save_profiles(profiles)
        if old_image != profile.get("icon_image"):
            icon_store.delete_icon_image(old_image)  # 바뀌거나 지워진 이미지는 파일도 정리


def delete_profile(index: int):
    profiles = load_profiles()
    if 0 <= index < len(profiles):
        removed = profiles.pop(index)
        save_profiles(profiles)
        icon_store.delete_icon_image(removed.get("icon_image"))


def relink_profiles(profiles: list[dict], playback_devices: list, recording_devices: list) -> bool:
    """저장된 장치 ID가 목록에서 사라졌으면(Windows 업데이트·드라이버 재설치로 ID가 바뀌는 경우) 같은 이름의
    장치를 찾아 ID를 새로 잇는다. 이름이 같은 장치가 정확히 하나일 때만 잇고, 바뀐 게 있으면 True.
    ID가 그대로인 프로필에는 나중을 위해 장치 원래 이름을 채워 둔다."""
    changed = False
    for profile in profiles:
        for kind, devices in (("playback", playback_devices), ("recording", recording_devices)):
            id_key, device_name_key = f"{kind}_id", f"{kind}_device_name"
            device_id = profile.get(id_key)
            if not device_id:
                continue
            current = next((d for d in devices if d.id == device_id), None)
            if current:
                if profile.get(device_name_key) != current.name:
                    profile[device_name_key] = current.name
                    changed = True
                continue
            names = {profile.get(device_name_key), profile.get(f"{kind}_name")}
            found = [d for d in devices if d.name in names or get_display_name(d.id, d.name) in names]
            if len(found) == 1:
                profile[id_key] = found[0].id
                profile[device_name_key] = found[0].name
                changed = True
    return changed


def find_active_profile(profiles: list[dict], playback_id: str | None, recording_id: str | None) -> int | None:
    """지금 "사용 중"인 프로필의 번호를 하나만 돌려준다(없으면 None).
    프로필에 지정된 장치가 모두 지금 기본 장치이면 해당한다. 장치 조합이 같은 프로필이 여럿이면
    장치 상태로는 구별할 수 없으니 마지막으로 적용한 프로필을, 아니면 목록에서 가장 앞의 것을 고른다."""
    matches = []
    for i, p in enumerate(profiles):
        p_id, r_id = p.get("playback_id"), p.get("recording_id")
        if (p_id or r_id) and (not p_id or p_id == playback_id) and (not r_id or r_id == recording_id):
            matches.append(i)
    if not matches:
        return None
    last = load_config().get("last_profile")
    return next((i for i in matches if profiles[i].get("name") == last), matches[0])


def set_last_profile(name: str):
    config = load_config()
    config["last_profile"] = name
    save_config(config)


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


# ---------- 자동 업데이트 알림 ----------
def load_auto_update_check() -> bool:
    """True면 시작할 때 자동으로 새 버전을 확인한다."""
    return bool(load_config().get("auto_update_check", True))


def set_auto_update_check(enabled: bool):
    config = load_config()
    config["auto_update_check"] = bool(enabled)
    save_config(config)
