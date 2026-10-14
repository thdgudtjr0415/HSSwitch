"""Windows 로그인 시 자동 실행 등록/해제. HKCU\\...\\CurrentVersion\\Run에 값을 추가/삭제한다(관리자 권한 불필요)."""

import sys
import winreg

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "HSSwitch"


def _executable_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --startup'
    return f'"{sys.executable}" "{sys.argv[0]}" --startup'


def is_startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except Exception:
        return False  # 값이 없거나(FileNotFoundError) 읽을 수 없는 경우


def set_startup_enabled(enabled: bool):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _executable_command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
    except Exception:
        pass
