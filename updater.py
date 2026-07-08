"""
HSSwitch 자동 업데이트 모듈.

FanControl(Rem0o/FanControl.Releases)의 배포 방식을 참고했다:
  - 저장소에 작은 JSON 매니페스트 파일 하나(version.json 등)를 올려두고
  - 앱은 그 파일만 확인해서 새 버전 여부를 판단하고
  - 실제 교체는 앱 본체가 아니라 별도의 업데이터가 담당한다.
    (FanControl은 Updater.exe라는 별도 실행파일을 쓰지만,
     우리는 별도 exe를 만들 필요 없이 임시 배치 스크립트로 같은 역할을 한다)

동작 순서:
1. UPDATE_MANIFEST_URL 에서 JSON 하나를 받아온다.
   기대 형식:
     {
       "version": "1.1.0",
       "url": "https://.../HSSwitch.exe",
       "md5": "27e4bef5ab961ddc93b2faf6ce6900d2",   # 선택. 있으면 검증한다.
       "notes": "- 버그 수정\\n- 기능 추가"
     }
2. manifest의 version이 현재 실행 중인 버전(version.py)보다 높으면 사용자에게 확인 창을 띄운다.
3. "예"를 누르면 새 exe를 임시 폴더에 내려받고(+ md5 있으면 검증),
   배치 스크립트를 하나 생성해서 "현재 프로세스가 완전히 종료될 때까지 대기 ->
   기존 exe를 새 exe로 교체 -> 재실행 -> 자기 자신(배치 파일) 삭제" 를 수행하게 한다.
4. 배치 스크립트를 백그라운드로 띄우고, 앱은 정상 종료 절차(app.quit_app())를 밟는다.

호스팅 위치는 아직 정해지지 않았으므로 UPDATE_MANIFEST_URL만 나중에 채우면 된다.
GitHub Releases를 쓰기로 하면, 릴리즈 노트에 exe를 올리고 raw.githubusercontent.com
경로의 update.json 파일 하나를 새 버전 낼 때마다 갱신하는 식으로 운영하면 된다.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from tkinter import messagebox

from version import APP_VERSION

UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/thdgudtjr0415/HSSwitch/main/version.json"

APP_TITLE = "HSSwitch"
_REQUEST_TIMEOUT = 5


def _parse_version(v: str):
    try:
        return tuple(int(p) for p in str(v).strip().split("."))
    except Exception:
        return (0,)


def check_for_update() -> dict | None:
    """
    네트워크 호출이 있으므로 반드시 백그라운드 스레드에서 호출할 것.
    새 버전이 있으면 manifest dict를, 없거나 실패하면 None을 반환한다.
    (URL 미설정/오프라인/서버 오류 등 어떤 이유로든 앱 실행에 지장을 주면 안 되므로
    전부 조용히 삼킨다)
    """
    if not UPDATE_MANIFEST_URL:
        return None
    try:
        with urllib.request.urlopen(UPDATE_MANIFEST_URL, timeout=_REQUEST_TIMEOUT) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
        remote_version = manifest.get("version", "")
        if manifest.get("url") and _parse_version(remote_version) > _parse_version(APP_VERSION):
            return manifest
    except Exception:
        pass
    return None


def prompt_and_update(app, manifest: dict):
    """메인 tkinter 스레드에서 호출. 사용자 확인 후 업데이트를 진행한다."""
    version = manifest.get("version", "?")
    notes = manifest.get("notes", "")
    message = f"새 버전 {version}이(가) 있어요 (현재: {APP_VERSION}).\n지금 업데이트할까요?"
    if notes:
        message += f"\n\n{notes}"
    if not messagebox.askyesno(APP_TITLE, message):
        return
    try:
        _download_and_apply(app, manifest)
    except Exception as e:
        messagebox.showerror(APP_TITLE, f"업데이트 중 문제가 생겼어요:\n{e}")


def _verify_md5(path: str, expected: str) -> bool:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()


def _download_and_apply(app, manifest: dict):
    if not getattr(sys, "frozen", False):
        messagebox.showinfo(
            APP_TITLE, "개발 모드(python main.py 실행)에서는 자동 업데이트를 지원하지 않아요.\nexe로 빌드된 배포판에서만 동작해요."
        )
        return

    url = manifest["url"]
    current_exe = sys.executable
    new_exe_path = os.path.join(tempfile.gettempdir(), "HSSwitch_update.exe")

    urllib.request.urlretrieve(url, new_exe_path)

    expected_md5 = manifest.get("md5")
    if expected_md5 and not _verify_md5(new_exe_path, expected_md5):
        try:
            os.remove(new_exe_path)
        except Exception:
            pass
        messagebox.showerror(APP_TITLE, "다운로드한 파일의 체크섬이 일치하지 않아요. 업데이트를 취소했어요.")
        return

    pid = os.getpid()
    batch_path = os.path.join(tempfile.gettempdir(), "hsswitch_update.bat")
    # 현재 프로세스(pid)가 완전히 죽을 때까지 기다렸다가 exe를 교체하고 재실행한다.
    # 무한 대기를 방지하기 위해 최대 15초(WAIT_LIMIT회)만 기다리고,
    # 그래도 안 죽어있으면 강제 종료 후 진행한다. (좀비 프로세스가 파일을
    # 잠그고 있으면 교체가 계속 실패하거나, 절반만 교체된 채로 새 인스턴스가
    # 실행돼서 "Failed to load Python DLL" 같은 오류가 나는 걸 방지)
    batch_content = f"""@echo off
setlocal enabledelayedexpansion
set count=0
:wait
tasklist /fi "PID eq {pid}" 2>nul | find "{pid}" >nul
if not errorlevel 1 (
  set /a count+=1
  if !count! geq 15 (
    taskkill /F /PID {pid} >nul 2>nul
    timeout /t 1 /nobreak >nul
    goto after_wait
  )
  timeout /t 1 /nobreak >nul
  goto wait
)
:after_wait
move /y "{new_exe_path}" "{current_exe}" >nul
if not exist "{current_exe}" (
  goto end
)
start "" "{current_exe}"
:end
del "%~f0"
"""
    with open(batch_path, "w", encoding="utf-8") as f:
        f.write(batch_content)

    subprocess.Popen(
        ["cmd", "/c", batch_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    # 배치가 대기할 대상은 "이 프로세스가 완전히 죽는 것"이므로,
    # 트레이 아이콘/단축키 정리까지 포함된 정상 종료 절차를 그대로 탄다.
    app.quit_app()
