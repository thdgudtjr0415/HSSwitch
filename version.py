"""
HSSwitch 버전 정보.

배포(exe 빌드)할 때마다 이 값을 올려야 한다. 동시에 updater.py가 읽어오는
manifest(update.json 등)의 "version" 값도 함께 올려야 자동 업데이트 알림이 뜬다.
버전 비교는 "1.2.3" 처럼 점으로 구분된 숫자 형식이어야 한다(updater.py 참고).
"""

APP_VERSION = "1.0.5"
