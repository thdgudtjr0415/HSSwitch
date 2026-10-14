# HSSwitch 인수인계 자료

작성일: 2026-10-14 / 기준 버전: v1.1.10 / 작성: 송형석 (Claude와 함께 진행한 작업 전체 정리)

이 문서는 HSSwitch를 처음 맡는 사람(또는 새 Claude 세션)이 이 문서 하나만 읽고도 프로젝트를 이어받아 수정, 빌드, 릴리즈까지 할 수 있도록 지금까지의 작업 내용을 정리한 것입니다. 사용자용 설명은 `README.md`와 `docs/HSSwitch_소개_및_사용설명서.md`를 보세요.

---

## 1. 프로젝트 한눈에 보기

HSSwitch는 스피커/헤드셋/마이크 같은 Windows 오디오 장치를 클릭 한 번, 단축키 한 번으로 바꿔주는 트레이 상주 프로그램입니다. 취업 포트폴리오용 1인 프로젝트이고, 읽기 쉬운 단순한 파이썬 코드를 우선합니다.

| 항목 | 내용 |
|---|---|
| 저장소 | https://github.com/thdgudtjr0415/HSSwitch (Public, 브랜치는 `main` 하나로 운영) |
| 로컬 경로 | `C:\Users\SHS\Desktop\HSSwitch` |
| 언어/라이브러리 | Python 3.13, pycaw, comtypes, pystray, Pillow, keyboard, pywebview (tkinter는 표준 라이브러리) |
| 빌드 | PyInstaller `--onedir` (폴더 배포), 결과물 `dist\HSSwitch.zip` |
| 배포 | GitHub Releases (zip 첨부) + 저장소 루트 `version.json` |
| 자동 업데이트 | 앱이 `version.json`을 읽어 새 버전 확인 → zip 다운로드/검증 → 배치 스크립트로 교체 후 재시작 |
| 설정 파일 | `%APPDATA%\HSSwitch\config.json` |
| 오류 로그 | `%APPDATA%\HSSwitch\crash.log` (초기화/트레이 실패 시에만 생김) |
| 라이선스 | MIT |

---

## 2. 폴더/파일 구조

| 파일 | 역할 |
|---|---|
| `main.py` | 진입점. tkinter 메인 창(개별 전환/프로필/장치 별칭/설정 탭), pystray 트레이 아이콘 시작, 단축키 등록, 단일 인스턴스 제어, 자동 업데이트 확인 호출 |
| `audio_devices.py` | pycaw로 재생/녹음 장치 목록과 현재 기본 장치 조회. 호출마다 자체적으로 COM 초기화 |
| `policy_config.py` | 기본 장치를 실제로 전환(Console/Multimedia/Communications 세 역할 모두 갱신) |
| `volume_control.py` | 장치 ID별 볼륨/음소거 조회·설정. 호출마다 자체적으로 COM 초기화 |
| `tray_popup_web.py` | 트레이 좌클릭 시 뜨는 pywebview 팝업. HTML/CSS/JS를 문자열로 생성하고, `Api` 클래스가 JS↔Python 브리지 |
| `theme_manager.py` | 시스템/라이트/다크 테마 해석과 팔레트 제공 (트레이 팝업에만 적용) |
| `icon_art.py` | 트레이 아이콘 이미지를 PIL로 직접 그림 (헤드셋+마이크, 헤드셋, 스피커, 마이크) |
| `icon_store.py` | 프로필에 지정한 내 이미지를 64x64 PNG로 `%APPDATA%\HSSwitch\icons`에 저장/불러오기/삭제. 클립보드 이미지 읽기 |
| `config_manager.py` | config.json 읽기/쓰기. 프로필, 별칭, 테마, `auto_update_check`, 마지막으로 적용한 프로필(`last_profile`), "사용 중" 프로필 판별 |
| `startup_manager.py` | 레지스트리 Run 키로 Windows 부팅 시 자동 실행 등록/해제 (`--startup` 인자로 실행) |
| `updater.py` | 업데이트 확인, 다운로드, md5 검증, 배치 스크립트 생성/실행 |
| `version.py` | `APP_VERSION` (릴리즈 때마다 올림) |
| `version.json` | 업데이트 매니페스트 (`version`, `url`, `md5`, `notes`). 앱이 raw.githubusercontent.com에서 읽음 |
| `build.bat` | 정리 → 의존성 설치 → PyInstaller → zip 생성 |
| `assets/icon.ico` | exe 아이콘 + 창/작업 표시줄 아이콘 (`--add-data "assets;assets"`로 번들) |
| `CLAUDE.md` | Claude 작업 지침 (코딩 원칙, 스레딩 제약, 릴리즈 절차) |
| `README.md` | 사용자/개발자용 README |
| `docs/` | 기획 문서(`01_HSSwitch plan.md`), 이 인수인계 자료, 소개 및 사용설명서, 팝업 디자인 규칙(`DESIGN.md`) |
| `.gitignore` | `__pycache__/`, `*.pyc`, `build/`, `dist/`, `*.spec` |

---

## 3. 아키텍처와 스레드 구조 (가장 조심할 부분)

이 앱은 GUI 세 종류가 한 프로세스에서 같이 돌아가기 때문에 스레드 구조가 까다롭습니다. 이미 한 번씩 디버깅해서 안정화한 부분이라 임의로 합치거나 단순화하면 안 됩니다.

| 스레드 | 하는 일 | COM 초기화 |
|---|---|---|
| 진짜 메인 스레드 | pywebview 이벤트 루프 (`tray_popup_web.run_event_loop()`) | `main()`에서 `CoInitialize()` |
| `tk_thread` | tkinter `Tk()`와 mainloop, `HSSwitchApp` 생성 | 스레드 시작 시 `CoInitialize()` |
| pystray 스레드 | 트레이 아이콘 `Icon.run()` | `run_tray()` 안에서 `CoInitialize()`, 실패 시 2초 후 1회 재시도 |
| pywebview JS 브리지 콜백 스레드 | 팝업에서 JS가 호출하는 `Api` 메서드 실행 | `audio_devices.py`, `volume_control.py`가 호출마다 자체 초기화 |
| 업데이트 확인 워커 | 네트워크만 사용 (COM 없음) | 불필요 |

지켜야 할 규칙은 다음과 같습니다.

- pywebview는 반드시 메인 스레드에서만 창을 만들고 이벤트 루프를 돌립니다. 백그라운드 스레드에서 `webview.create_window()`를 호출하면 안 됩니다.
- pycaw(COM)를 건드리는 모든 스레드는 `CoInitialize()`를 해야 합니다. 그래서 `audio_devices.py`와 `volume_control.py`의 함수는 어떤 스레드에서 불려도 되도록 각자 초기화합니다. 이 호출을 제거하거나 합치지 마세요.
- pystray, tkinter, pywebview 세 루프는 서로 합치지 않습니다. 합쳐야 할 것 같으면 트레이드오프를 먼저 논의하세요.
- 팝업의 `Api` 메서드 중 오디오/설정을 바꾸는 것은 `self.app.root.after(0, ...)`로 tkinter 스레드에 넘겨서 처리합니다 (`switch_playback`, `apply_profile` 등). 프로필 저장/수정/삭제는 `config_manager`에 먼저 쓰고, `_refresh_app()`으로 `app.profiles` 갱신과 단축키 재등록을 tkinter 스레드에 요청합니다.

### 시작 흐름 (`main.py`)

1. `_ensure_single_instance()`: 이름 있는 뮤텍스(`Global\HSSwitchSingleInstanceMutex`)로 중복 실행을 막고, 이미 실행 중이면 그 창을 앞으로 가져온 뒤 종료
2. `tk_thread` 시작: `HSSwitchApp(root)` 생성. 이 안에서 UI 구성 → 장치 조회 → 단축키 등록 → 트레이 아이콘 시작 → 2초 뒤 자동 업데이트 확인(설정이 켜져 있을 때) 순서로 진행. 초기화에서 예외가 나도 `ready.set()`은 항상 호출되고, 실패 원인은 `crash.log`에 남음
3. `--startup`으로 실행되면 창을 숨기고 트레이로 시작. 부팅 직후 장치가 아직 안 잡혔을 수 있어 4초/10초 뒤 장치 목록이 비어 있으면 한 번씩 다시 조회
4. 메인 스레드에서 pywebview keep-alive 창을 만들고 이벤트 루프 시작

---

## 4. 현재 기능 목록 (v1.1.10 기준)

- 개별 전환 탭: 재생/녹음 장치를 목록에서 골라 즉시 전환
- 프로필: 재생+녹음 조합을 이름/아이콘/단축키와 함께 저장, 한 번에 전환
  - 메인 창 프로필 탭의 "현재 장치로 빠른 추가" 버튼 (지금 쓰는 장치로 미리 채워진 입력 창)
  - 트레이 팝업의 "+ 추가" 타일 → 팝업 안에서 입력 폼으로 전환, 현재 장치 자동 선택, 저장하면 목록으로 복귀
  - 트레이 팝업 프로필 타일 우클릭 → 수정/삭제 (삭제는 팝업 스타일의 자체 확인 모달)
- 글로벌 단축키로 프로필 전환
- 트레이 팝업: 프로필/장치 선택, 볼륨 슬라이더 + 숫자 직접 입력 칸, 음소거 토글, 4.5초 무조작 시 자동 닫힘, 포커스를 잃으면 닫힘
- 장치 별칭 (앱 안에서만 보이는 이름)
- 테마: 시스템/라이트/다크 (트레이 팝업에만 적용)
- Windows 부팅 시 자동 실행
- 자동 업데이트 + 설정 탭의 "시작할 때 자동으로 업데이트 확인" 체크박스 (꺼도 수동 "업데이트 확인" 버튼은 항상 동작)
- 중복 실행 방지, 창/작업 표시줄 아이콘을 앱 아이콘으로 표시

### 트레이 팝업 구현 메모

- HTML은 `_build_html()`이 한 번 만들어 창에 넣고, 이후 화면 전환(메인 ↔ 추가/수정 폼)은 JS가 `#root.innerHTML`을 갈아끼우는 방식입니다. 조각 HTML은 `_build_main_view_html()`, `_build_profile_form_html()`이 만듭니다.
- 폼은 추가/수정 겸용입니다. 숨은 입력 `add-edit-index`가 비어 있으면 추가, 값이 있으면 수정으로 저장합니다.
- 팝업 창의 크기와 위치는 처음 열 때 한 번만 계산합니다. 프로필을 추가/삭제할 때마다 `resize()+move()`를 다시 호출했더니 팝업이 튀어서 제거했습니다. 프로필이 아주 많아지면 아래쪽이 잘릴 수 있고, 그 경우는 고정 크기 정책을 다시 검토해야 합니다.
- 삭제 확인은 브라우저 기본 `confirm()`이 아니라 자체 모달입니다. 기본 `confirm()`은 프레임 없는 팝업 안에서 위치가 어긋나고 스타일이 안 맞았습니다.
- 볼륨 숫자 입력 칸은 `type="number"`가 아니라 `type="text" inputmode="numeric"`입니다. number 타입은 마우스를 올리면 스핀 버튼이 생겨서 뺐습니다.

---

## 5. 빌드와 릴리즈

### 빌드

`build.bat`은 `build/`, `dist/`, `HSSwitch.spec`을 지우고 → `pip install -r requirements.txt` → 아래 PyInstaller 명령 → `dist\HSSwitch\*`를 `dist\HSSwitch.zip`으로 압축합니다.

```
pyinstaller --windowed --icon=assets\icon.ico --add-data "assets;assets" --name HSSwitch --contents-directory HSSwitch_files main.py
```

- `--onedir`를 쓰는 이유: onefile은 실행 때마다 임시 폴더에 압축을 푸는데, 백신 실시간 검사와 겹쳐 "Failed to load Python DLL" 오류가 간헐적으로 났습니다. 폴더 배포로 바꾸면서 구조적으로 사라졌습니다.
- `--contents-directory HSSwitch_files`: 기본 이름 `_internal` 대신 알아보기 쉬운 폴더명을 쓰기 위한 옵션입니다.
- `build.bat`은 ASCII 문자만 써야 합니다. 한글 주석이 들어가면 cmd가 ANSI 코드페이지로 해석하다가 깨진 명령어를 실행합니다.
- 빌드 전에 실행 중인 `HSSwitch.exe`를 반드시 종료하세요. 떠 있으면 `base_library.zip`이 잠겨서 zip 단계가 실패합니다.

### 릴리즈 절차 (CLAUDE.md의 Release Workflow와 동일)

셸을 섞지 마세요. git 명령은 git bash, 빌드와 해시는 PowerShell입니다 (`Get-FileHash`는 PowerShell 전용이라 git bash에서는 조용히 아무 일도 안 일어납니다).

1. 코드 수정 후 `version.py`의 `APP_VERSION`을 올립니다. 이미 게시된 버전 번호는 태그를 재사용할 수 없으니 반드시 새 번호를 씁니다. 매 수정마다 올리지 않고, 릴리즈하기로 했을 때만 올립니다.
2. git bash에서 변경 파일 add/commit/push (`git add -A`가 가장 덜 꼬임)
3. PowerShell에서 `cd "$env:USERPROFILE\Desktop\HSSwitch"` → `.\build.bat` → `Get-FileHash dist\HSSwitch.zip -Algorithm MD5`
4. `version.json`의 `version`, `md5`, `notes`를 갱신
5. GitHub에서 새 릴리즈 생성: 태그 `vX.Y.Z`, 타이틀 `HSSwitch vX.Y.Z`, 릴리즈 노트(한국어 한두 줄), `dist\HSSwitch.zip`을 파일명 그대로 첨부, 반드시 Publish (Draft로 두면 고정 다운로드 링크가 동작하지 않음)
6. `version.json`을 git bash에서 commit/push
7. 약 5분 기다린 뒤(raw.githubusercontent.com 캐시 지연) 구버전 앱에서 "업데이트 확인"으로 실제 업데이트가 되는지 확인

`version.json`의 `url`은 항상 `https://github.com/thdgudtjr0415/HSSwitch/releases/latest/download/HSSwitch.zip` 고정입니다. zip 파일명을 바꾸면 모든 구버전의 업데이트가 깨집니다.

---

## 6. 자동 업데이트 동작 방식

1. 앱이 `UPDATE_MANIFEST_URL`(`.../main/version.json`)을 읽습니다.
2. 원격 `version`이 `APP_VERSION`보다 크면 확인 창을 띄웁니다.
3. "예"를 누르면 zip을 임시 폴더에 받고, md5가 있으면 검증한 뒤 `extracted/`에 풉니다.
4. 임시 배치 파일을 만들어 실행합니다. 배치는 현재 PID가 끝날 때까지 최대 15초 기다리고(넘으면 `taskkill /F`), `robocopy ... /E /IS /IT`로 설치 폴더 위에 덮어쓴 뒤, 백신 검사와 겹치지 않도록 3초 기다렸다가 exe를 다시 실행하고 임시 파일을 정리합니다.
5. 앱은 `quit_app()`으로 정상 종료합니다.

주의할 점은 다음과 같습니다.

- 배치 파일은 `encoding="mbcs"`로 씁니다. UTF-8로 쓰면 한글 사용자 폴더 경로나 주석이 cmd에서 깨집니다. 배치 안 주석은 영어만 씁니다.
- 개발 모드(`python main.py`)에서는 자동 업데이트가 비활성입니다 (`sys.frozen` 확인).
- v1.0.0은 업데이트 URL이 비어 있어 업데이트 기능이 꺼진 채로 배포됐습니다. 그 버전 사용자는 한 번 수동으로 받아야 합니다.
- v1.1.5 이하 빌드에는 트레이 아이콘 초기화 버그가 있어서, 그 버전에서 업데이트하면 "'HSSwitchApp' object has no attribute 'tray_icon'" 오류창이 한 번 뜹니다. 배치가 15초 뒤 강제 종료하고 교체를 이어가므로 업데이트 자체는 완료됩니다. v1.1.6부터는 발생하지 않습니다.
- 서명 안 된 exe라 첫 실행 때 Windows SmartScreen 경고가 뜹니다 ("추가 정보" → "실행"). 코드 서명은 아직 안 했습니다.

---

## 7. 버전 이력

| 버전 | 주요 내용 |
|---|---|
| 1.0.0 | 최초 배포 (onefile, 업데이트 URL 비어 있음) |
| 1.0.1~1.0.3 | 자동 업데이트 도입과 안정화 (체크섬 검증, 대기/강제 종료 로직) |
| 1.0.4 | 업데이트 후 재실행 지연 추가 (백신 검사와의 경합 방지) |
| 1.0.5 | 중복 실행 방지 (뮤텍스) |
| 1.0.6 | onefile → onedir 폴더 배포 전환, zip 업데이트 방식 |
| 1.0.7 | 내부 폴더명 `_internal` → `HSSwitch_files` |
| 1.0.8 | "시작할 때 자동으로 업데이트 확인" 체크박스 |
| (태그 v1.0.9) | 태그 충돌로 v1.0.9로 올렸으나 zip 안 `APP_VERSION`은 1.0.8. 기능에는 영향 없음 |
| 1.1.0 | 프로필 빠른 추가 (메인 창 버튼 + 트레이 팝업 인라인 폼) |
| 1.1.1 | 트레이 팝업 프로필 우클릭 수정/삭제 |
| 1.1.3 | 삭제 확인 모달 교체, 팝업 위치 튀는 문제 수정 (1.1.2는 게시하지 않고 건너뜀) |
| 1.1.4 | 부팅 직후 오디오 장치 미준비로 앱이 멈추던 문제 방어 |
| 1.1.5 | 트레이 아이콘 등록 실패 방어와 재시도 |
| 1.1.6 | 트레이 초기화 코드가 `__init__` 밖으로 잘못 들어간 버그 수정 |
| 1.1.7 | 창/작업 표시줄 아이콘을 `assets/icon.ico`로 교체 |
| 1.1.8 | `audio_devices.py`에 호출별 COM 초기화 추가 |
| 1.1.9 | 볼륨 숫자 직접 입력 칸 |
| 1.1.10 | 숫자 입력 칸 스핀 버튼 제거, 가운데 정렬 |

---

## 8. 겪은 문제와 해결 (재발 시 참고)

| 증상 | 원인 | 해결 |
|---|---|---|
| "Failed to load Python DLL" 반복 | onefile의 임시 폴더 압축 해제가 백신 검사와 경합, 빌드 도중 exe를 실행해본 경우도 있었음 | onedir로 전환. 빌드가 끝난 뒤에만 실행 |
| 업데이트 배치가 엉뚱한 명령 실행 | .bat의 한글 주석이 ANSI 코드페이지로 해석되며 깨짐 | 배치/빌드 스크립트는 ASCII 주석, 생성 배치는 mbcs 인코딩 |
| 트레이 아이콘이 3개 | 중복 실행 방지 없음 | 이름 있는 뮤텍스 |
| 팝업이 가끔 앞으로 안 나옴 | 포그라운드 락, 창 제목 충돌 | 팝업 타이틀 `HSSwitchPopup`으로 분리, ALT 키 트릭 + `SetForegroundWindow` |
| 업데이트 후 "체크섬이 일치하지 않아요" | `raw.githubusercontent.com` 캐시 지연 | 푸시 후 5분 정도 기다림 |
| 업데이트 확인했는데 "최신 버전" | `version.json` push 전이거나 캐시 지연 | 릴리즈 publish + push 둘 다 끝났는지 확인 후 대기 |
| 부팅 후 프로그램이 안 뜸 | 오디오 장치 열거 예외로 초기화 스레드가 죽고 `ready.wait()`에서 영원히 대기 | 열거 예외 방어, 초기화 실패해도 `ready.set()`, `crash.log` 기록 |
| 트레이 아이콘이 안 생김 | 수정 중 `self.tray_icon = None`과 시작 코드가 다른 메서드 안으로 들어감 | `__init__`으로 복귀 (v1.1.6) |
| 빌드 중 zip 단계 실패 | 실행 중인 HSSwitch.exe가 `base_library.zip`을 잡고 있음 | exe 종료 후 재빌드 |
| GitHub Draft 발행 시 "tag name has already been taken" | GitHub UI 오류 | 새로고침 후 재시도, 안 되면 태그 번호를 올려 새로 발행 |
| `git add`가 안 먹음 | 명령 앞에 `~`가 붙어 `~git`으로 입력, 또는 한글 파일명 입력 실수 | 다시 입력, 가장 안전한 방법은 `git add -A` |
| 팝업이 프로필 추가/삭제 때 튐 | 리사이즈+이동을 매번 다시 호출 | 처음 계산한 크기/위치 유지 |

---

## 9. 알려진 한계와 확인이 필요한 항목

아래는 지금 시점에서 완료로 확인하지 못했거나, 판단이 필요한 항목입니다.

- v1.1.10 릴리즈: 빌드와 `version.json` 갱신까지 끝났고 해시는 `91FFB27F0541F190CDE0E30022DF4CC9`입니다. GitHub Release publish와 `version.json` push, 구버전에서의 업데이트 확인은 사용자가 마무리했는지 확인되지 않았습니다. `https://github.com/thdgudtjr0415/HSSwitch/releases/latest`가 v1.1.10을 가리키는지 먼저 확인하세요.
- `.claude/` 폴더가 저장소에 올라갔는지 확인하세요. 한때 untracked 상태였고 이후 `git add -A`를 안내했기 때문에 같이 커밋됐을 수 있습니다. 올리고 싶지 않다면 `.gitignore`에 추가하세요.
- `LICENSE` 파일에 줄바꿈(LF→CRLF)만 바뀐 변경이 한 번 잡혔습니다. 내용은 동일해서 무해합니다.
- CLAUDE.md는 COM/스레딩 관련 수정 후 "앱이 유휴 상태였다가, 또는 절전 복귀 후에도 장치 전환이 잘 되는지" 수동 확인을 요구합니다. v1.1.8의 `audio_devices.py` COM 초기화 변경에 대해서는 이 확인을 명시적으로 기록하지 못했습니다. 다음 작업 전에 한 번 확인하세요.
- **USB 동글 방식 무선 헤드셋(예: CORSAIR HS80 Wireless)은 헤드셋 전원을 꺼도 Windows가 장치를 계속 "활성"으로 보고합니다.** 실제로 전원을 끄고 확인했을 때 장치 목록은 켰을 때와 같았고, 헤드셋 프로필을 누르면 에러 없이 기본 장치가 꺼진 헤드셋으로 바뀌었습니다(소리가 안 남). 앱이 알 수 있는 정보가 없어서 팝업의 "장치 없음" 표시와 전환 실패 알림은 이 경우 동작하지 않습니다. 장치가 목록에서 사라지거나 전환이 에러를 내는 경우(동글/유선 장치를 뽑은 경우)에만 동작합니다. 소리가 안 나면 헤드셋 전원을 먼저 확인하세요.
- 프로필이 많아지면 팝업 높이가 고정이라 아래쪽이 잘릴 수 있습니다.
- 코드 서명이 없어 SmartScreen 경고가 계속 뜹니다. 유료 인증서나 오픈소스용 무료 서명 서비스(SignPath.io 등) 검토가 필요하면 별도 작업입니다.
- 디스코드 같은 특정 앱의 출력 장치까지 따라가게 하는 기능(기획서의 Phase 4)은 구현하지 않았습니다.
- 자동화 테스트가 없습니다. 기능 추가 때는 짧은 수동 체크리스트로 검증해왔습니다.

### 보류 중인 아이디어: 릴리즈 자동화

수동 릴리즈에서 실수(셸 혼동, Draft 방치, 해시 오기입, 태그 충돌)가 잦아서 GitHub Actions로 자동화하는 안을 논의했고 "잠깐 대기" 상태입니다. 구상은 다음과 같습니다.

- `v*.*.*` 태그를 push하면 `windows-latest` 러너가 PyInstaller 빌드 → zip → md5 계산 → Release 생성 및 zip 첨부 → `version.json` 자동 갱신 후 `main`에 커밋
- 이렇게 되면 사람이 하는 일은 `version.py` 수정, 커밋, 태그 push뿐
- 대안으로는 로컬 스크립트 하나로 빌드+해시+`version.json` 작성까지 묶고, Release 생성만 수동으로 두는 방법이 있음

---

## 10. GitHub 운영 방침

- 저장소는 Public입니다. 무료 자동 업데이트(`raw.githubusercontent.com`, `releases/latest/download`)가 인증 없이 동작하려면 Public이어야 하므로 Private으로 바꾸면 업데이트가 깨집니다.
- 누구나 이슈나 PR을 올릴 수 있지만, 협업자로 초대하지 않는 한 `main`에 직접 push할 수 없고 PR은 메인테이너가 Merge해야 반영됩니다. 그래서 외부 제안은 받되 수용 여부는 항상 메인테이너가 결정합니다.
- 소스는 공개 상태이므로 누구나 포크해서 가져갈 수 있고, 이는 MIT 라이선스가 허용하는 범위입니다. 재사용을 제한하고 싶다면 라이선스를 바꾸는 별도 결정이 필요합니다.
- 브랜치는 따로 만들지 않고 `main`에 바로 커밋해왔습니다. 외부 PR은 기여자가 자기 포크의 브랜치로 보내므로 따로 준비할 것은 없습니다. 실험적인 작업을 하면서 `main`을 안정적으로 두고 싶을 때만 브랜치를 사용하세요.

---

## 11. Claude와 계속 작업할 때

- 프로젝트 루트의 `CLAUDE.md`를 먼저 읽게 하세요. 코딩 원칙(단순하게, 필요한 부분만 수정, 검증 기준 정하기), 스레딩 제약, 릴리즈 절차가 들어 있습니다.
- 릴리즈를 요청할 때는 "릴리즈하자"라고 말하면 됩니다. 버전은 그때 올립니다. 해시를 알려주면 `version.json`을 갱신하고, 태그/타이틀/릴리즈 노트를 정해진 형식으로 줍니다.
- 윈도우 폴더를 Claude의 리눅스 샌드박스(bash)에서 `cat`이나 `wc`로 확인하면 오래된 내용이 보일 때가 있었습니다. 파일 내용 확인은 Read/Edit 도구 결과를 기준으로 삼으세요.
- git, 빌드, 해시 명령은 Claude가 직접 실행하지 않고 사용자 PC에서 실행하도록 안내하는 방식으로 진행해왔습니다.

### 새 세션 시작용 한 줄 요약 (붙여넣기용)

> HSSwitch는 pycaw/tkinter/pystray/pywebview 기반 Windows 오디오 장치 전환 트레이 앱입니다. 저장소는 C:\Users\SHS\Desktop\HSSwitch, 현재 버전은 v1.1.10입니다. 먼저 CLAUDE.md와 docs\HSSwitch_인수인계_자료.md를 읽고, 스레딩/COM 제약을 지키면서 최소한의 수정만 해주세요. 릴리즈는 내가 "릴리즈하자"고 할 때만 진행합니다.
