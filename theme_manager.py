"""
Windows 시스템의 라이트/다크 모드를 감지하고, 사용자가 수동으로 선택한 테마와
합쳐서 최종 적용할 테마를 결정하는 모듈.
"""

import winreg

import config_manager

LIGHT = {
    "card_bg": "#ffffff",
    "card_hover": "#efeff2",
    "accent": "#007AFF",
    "fg": "#1c1c1e",
    "fg_muted": "#8a8a8e",
    "fg_on_accent": "#ffffff",
    "divider": "#e5e5ea",
    "popup_bg": "#f6f6f8",
    "slider_track": "#e5e5ea",
}

DARK = {
    "card_bg": "#2c2c2e",
    "card_hover": "#3a3a3c",
    "accent": "#0A84FF",
    "fg": "#f2f2f2",
    "fg_muted": "#9a9a9a",
    "fg_on_accent": "#ffffff",
    "divider": "#38383a",
    "popup_bg": "#1c1c1e",
    "slider_track": "#3a3a3c",
}


def get_system_theme() -> str:
    """Windows 레지스트리에서 앱의 라이트/다크 모드 설정을 읽어온다."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if value == 1 else "dark"
    except Exception:
        return "light"


def resolve_theme() -> str:
    """
    사용자가 설정에서 고른 테마("system"/"light"/"dark")를 읽어서
    실제로 적용할 테마("light"/"dark")를 반환.
    """
    setting = config_manager.load_theme()
    if setting == "system":
        return get_system_theme()
    return setting


def get_palette(resolved_theme: str) -> dict:
    return DARK if resolved_theme == "dark" else LIGHT
