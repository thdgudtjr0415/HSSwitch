"""
HSSwitch 자동 업데이트.

동작 순서:
1. UPDATE_MANIFEST_URL(저장소의 version.json)을 받아온다. 형식:
     {"version": "1.1.0", "url": "https://.../HSSwitch.zip", "md5": "(선택, 있으면 zip 검증)", "notes": "..."}
2. version이 현재 버전(version.py)보다 높으면 확인 창을 띄운다.
3. "예"면 zip을 임시 폴더에 받아(md5 검증) 풀고, 임시 배치 스크립트를 만든다.
4. 배치는 이 프로세스가 끝날 때까지 기다렸다가 robocopy로 설치 폴더를 덮어쓰고 앱을 다시 실행한다.
5. 앱은 정상 종료 절차(app.quit_app())를 밟는다.

릴리즈할 때는 dist\\HSSwitch.zip을 GitHub Release에 첨부하고 version.json(version/md5/notes)을 갱신해 push한다.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
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
    """새 버전이 있으면 manifest를, 없거나 실패하면 None을 반환한다. 네트워크를 쓰므로 백그라운드 스레드에서 호출할 것.
    오프라인 등 어떤 실패도 앱 실행에 영향을 주면 안 되어 예외는 삼킨다."""
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
    install_dir = os.path.dirname(current_exe)

    work_dir = tempfile.mkdtemp(prefix="hsswitch_update_")
    zip_path = os.path.join(work_dir, "HSSwitch_update.zip")

    urllib.request.urlretrieve(url, zip_path)

    expected_md5 = manifest.get("md5")
    if expected_md5 and not _verify_md5(zip_path, expected_md5):
        messagebox.showerror(APP_TITLE, "다운로드한 파일의 체크섬이 일치하지 않아요. 업데이트를 취소했어요.")
        return

    extract_dir = os.path.join(work_dir, "extracted")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    pid = os.getpid()
    batch_path = os.path.join(tempfile.gettempdir(), "hsswitch_update.bat")
    # 현재 프로세스가 끝날 때까지 최대 15초 기다리고, 그래도 살아 있으면 강제 종료한 뒤 교체한다
    # (프로세스가 파일을 잡고 있으면 교체가 실패하거나 반쯤 교체된 채로 실행되기 때문)
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
robocopy "{extract_dir}" "{install_dir}" /E /IS /IT /R:3 /W:1 /NFL /NDL /NJH /NJS >nul
rem Wait a moment before relaunching: launching immediately after replacing
rem files can race with real-time antivirus scanning of the fresh files.
timeout /t 3 /nobreak >nul
start "" "{current_exe}"
rmdir /s /q "{work_dir}" >nul 2>nul
del "%~f0"
"""
    # cmd.exe는 .bat을 ANSI 코드페이지로 읽으므로 UTF-8로 쓰면 한글 경로가 깨진다 -> "mbcs"
    with open(batch_path, "w", encoding="mbcs") as f:
        f.write(batch_content)

    subprocess.Popen(
        ["cmd", "/c", batch_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    app.quit_app()  # 배치가 이 프로세스의 종료를 기다리므로 트레이/단축키 정리까지 하는 정상 종료를 탄다
