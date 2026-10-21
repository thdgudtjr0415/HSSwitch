"""
앱이 갑자기 꺼졌을 때 원인을 찾을 수 있도록 %APPDATA%\\HSSwitch\\hsswitch.log에 기록을 남긴다.

- 처리되지 않은 오류(메인/다른 스레드/tkinter 콜백)의 traceback
- 파이썬이 죽는 치명적 충돌(COM·ctypes·Tk 안에서 나는 것)의 스레드별 호출 스택(faulthandler)
- 시작과 정상 종료 줄: 로그가 "시작"으로 끝나고 "종료"가 없으면 비정상 종료였다는 뜻이다.
기록 실패가 앱 동작을 막으면 안 되므로 모든 파일 작업은 실패해도 조용히 넘어간다.
"""

import atexit
import datetime
import faulthandler
import os
import sys
import threading
import traceback

LOG_PATH = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "HSSwitch", "hsswitch.log")
_MAX_BYTES = 200 * 1024  # 넘으면 이전 기록은 .old로 넘기고 새로 시작(파일이 계속 커지지 않게)
_file = None


def log(message: str):
    if _file is None:
        return
    try:
        _file.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")
    except Exception:
        pass


def log_exception(exc_type, exc_value, exc_tb, where: str):
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log(f"오류 ({where})\n{text}")


def setup(version: str):
    global _file
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > _MAX_BYTES:
            os.replace(LOG_PATH, LOG_PATH + ".old")
        _file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
    except OSError:
        return

    # 창 없는 exe는 stderr가 없으니 파일을 직접 넘긴다. 이 파일은 프로세스가 끝날 때까지 열어 둬야 한다
    faulthandler.enable(_file, all_threads=True)
    sys.excepthook = lambda t, v, tb: log_exception(t, v, tb, "메인 스레드")
    threading.excepthook = lambda args: log_exception(
        args.exc_type, args.exc_value, args.exc_traceback, f"스레드 {args.thread.name if args.thread else '?'}"
    )
    atexit.register(log, "종료 (정상)")
    log(f"시작 v{version} pid={os.getpid()} 인자={sys.argv[1:]}")
