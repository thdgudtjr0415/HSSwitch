# HSSwitch

스피커 / 헤드셋 / 마이크를 클릭 한 번, 단축키 한 번으로 빠르게 전환하는 Windows 트레이 상주 프로그램.

## 다운로드

바로 쓰고 싶다면 [최신 릴리즈](https://github.com/thdgudtjr0415/HSSwitch/releases/latest)에서 `HSSwitch.zip`을 받아서 원하는 폴더에 압축을 풀고, 그 안의 `HSSwitch.exe`를 실행하면 됩니다. 설치 프로그램이 아니라 포터블이에요. **압축을 푼 폴더 전체(`HSSwitch_files` 폴더 포함)를 그대로 유지해야** 정상 동작합니다 — `HSSwitch.exe`만 따로 빼서 옮기면 안 돼요.

> **처음 실행할 때 "Windows의 PC 보호" (SmartScreen) 경고가 뜰 수 있어요.**
> 코드에 문제가 있는 게 아니라, 서명 안 된 파일을 인터넷에서 받으면 Windows가 항상 띄우는 경고예요.
> 창에서 **"추가 정보"** → **"실행"**을 누르면 정상적으로 실행돼요.

이미 실행 중인데 exe를 또 실행해도 새 창이 중복으로 뜨지 않고, 기존에 열려 있던 창(또는 트레이 아이콘)이 앞으로 나옵니다.

## 주요 기능

- **개별 전환** — 메인 창에서 재생 장치(스피커/헤드셋)와 녹음 장치(마이크)를 목록에서 골라 즉시 전환
- **프로필** — 재생+녹음 장치 조합을 이름/아이콘/단축키와 함께 저장해서 한 번에 전환
  - 메인 창 프로필 탭의 **"현재 장치로 빠른 추가"** 버튼을 누르면 지금 실제로 쓰고 있는 재생/녹음 장치가 자동으로 채워진 채로 추가 창이 열려서, 이름만 입력하면 바로 저장돼요.
  - 트레이 팝업에서도 **"+ 추가"**를 누르면 별도 창 없이 팝업 안에서 바로 입력 폼으로 전환되고, 마찬가지로 현재 장치가 자동으로 채워져요. 저장하면 다시 프로필 목록 화면으로 돌아옵니다.
  - 트레이 팝업의 프로필 타일을 **우클릭**하면 수정/삭제 메뉴가 떠서, 메인 창을 열지 않고도 프로필을 관리할 수 있어요.
- **글로벌 단축키** — 앱을 열지 않고도 등록한 단축키로 프로필 전환
- **트레이 팝업** — 트레이 아이콘 좌클릭 시 화면 우측 하단에 뜨는 작은 팝업에서 프로필/장치 선택 및 볼륨·음소거 조절. 4.5초간 조작이 없으면 자동으로 닫힘
- **트레이 우클릭** — 열기(메인 창) / 종료
- **장치 별칭** — Windows가 붙인 복잡한 장치 이름 대신 원하는 이름으로 표시 (실제 장치 이름은 안 바뀜)
- **다크 모드** — 시스템 설정 따르기 / 라이트 / 다크 선택 (트레이 팝업에만 적용)
- **Windows 부팅 시 자동 실행**
- **자동 업데이트** — 실행 시 새 버전이 있는지 확인해서 알림을 띄우고, 확인을 누르면 자동으로 받아서 교체 후 재시작. 설정 탭의 체크박스로 시작할 때 자동 확인할지 켜고 끌 수 있고, 꺼두더라도 "업데이트 확인" 버튼으로는 언제든 직접 확인 가능
- **중복 실행 방지** — exe를 여러 번 실행해도 인스턴스가 하나만 유지됨

## 사용법

| 동작 | 결과 |
|---|---|
| 트레이 아이콘 좌클릭 | 빠른 전환 팝업 표시 |
| 트레이 아이콘 우클릭 | 열기 / 종료 메뉴 |
| 팝업의 "+ 추가" 타일 클릭 | 팝업 안에서 바로 프로필 추가 폼으로 전환 (현재 장치 자동 채움) |
| 팝업의 프로필 타일 우클릭 | 수정 / 삭제 메뉴 |
| 팝업의 볼륨 슬라이더 왼쪽 아이콘 클릭 | 해당 장치 음소거 토글 |
| 메인 창 - 개별 전환 탭 | 재생/녹음 장치를 각각 골라 전환 |
| 메인 창 - 프로필 탭 | 프로필 추가/빠른 추가/수정/삭제/전환, 단축키 등록 |
| 메인 창 - 장치 별칭 탭 | 장치별 표시 이름 지정 |
| 메인 창 - 설정 탭 | 테마, 자동 실행, 자동 업데이트 확인 켜기/끄기, 수동 업데이트 확인 |

## 개발 (소스에서 실행)

```powershell
git clone https://github.com/thdgudtjr0415/HSSwitch.git
cd HSSwitch
pip install -r requirements.txt
python main.py
```

## exe로 빌드

```powershell
.\build.bat
```

이 스크립트는 PyInstaller로 `dist\HSSwitch\` 폴더(exe + 의존 라이브러리가 담긴 `HSSwitch_files` 폴더)를 만들고,
그 폴더 전체를 `dist\HSSwitch.zip`으로 압축까지 해줍니다.

또는 수동으로:

```powershell
pip install pyinstaller
pyinstaller --windowed --icon=assets/icon.ico --name HSSwitch --contents-directory HSSwitch_files main.py
powershell -Command "Compress-Archive -Path 'dist\HSSwitch\*' -DestinationPath 'dist\HSSwitch.zip' -Force"
```

> **왜 `--onefile`이 아니라 `--onedir`(폴더)인가?** `--onefile`은 실행할 때마다 임시 폴더에
> 압축을 풀었다가 지우는 방식인데, 이 압축 해제 과정이 백신 실시간 검사와 자꾸 겹쳐서
> "Failed to load Python DLL" 같은 오류가 간헐적으로 발생했습니다. `--onedir`는 이 과정 자체가
> 없어서 훨씬 안정적입니다. `--contents-directory HSSwitch_files`는 기본값인 `_internal` 대신
> 알아보기 쉬운 폴더 이름을 쓰기 위한 옵션이에요.

`assets/icon.ico`는 헤드셋+마이크 라인 아이콘으로 미리 만들어둔 멀티 사이즈 아이콘이에요
(48px 이상은 "HS" 글자 배지 포함, 32px 이하는 아이콘만 — 작은 크기에서 글자가 뭉개지는 걸 방지).

## 새 버전 배포하기 (메인테이너용)

자동 업데이트는 이 저장소 루트의 `version.json`을 앱이 주기적으로 읽어서 동작합니다. 새 버전을 낼 때마다:

1. `version.py`의 `APP_VERSION`을 올린다 (예: `1.1.0` → `1.1.1`)
2. `.\build.bat`으로 다시 빌드 (`dist\HSSwitch.zip`까지 자동 생성됨)
3. `Get-FileHash dist\HSSwitch.zip -Algorithm MD5`로 **zip 파일**의 md5 계산
4. [새 릴리즈](https://github.com/thdgudtjr0415/HSSwitch/releases/new) 생성
   - Tag: `v1.1.1`처럼 버전에 맞게 (가급적 `version.py`와 동일한 숫자로 맞추기)
   - `dist\HSSwitch.zip`을 **파일명 그대로**(`HSSwitch.zip`) 첨부 — 파일명을 바꾸면
     `version.json`의 `url`(고정 링크: `.../releases/latest/download/HSSwitch.zip`)이 깨짐
   - **Publish release** (Draft로 남겨두면 고정 링크가 동작하지 않음)
5. 저장소 루트의 `version.json`을 새 버전/md5/notes로 갱신해서 push

```json
{
  "version": "1.1.1",
  "url": "https://github.com/thdgudtjr0415/HSSwitch/releases/latest/download/HSSwitch.zip",
  "md5": "새로_계산한_zip_MD5",
  "notes": "변경 사항 요약"
}
```

이렇게 하면 이전 버전을 쓰고 있는 사용자가 앱을 켤 때(자동 업데이트 확인이 켜져 있다면) 새 버전
알림을 받고, 확인을 누르면 새 zip을 받아서 풀고, 설치 폴더 위에 덮어쓴 뒤 재시작됩니다.

> **주의**: `UPDATE_MANIFEST_URL`이 비어있는 상태로 빌드된 exe(v1.0.0)는 업데이트 기능 자체가
> 꺼진 채로 굳어 있어서 자동으로 최신화되지 않습니다. 그 버전을 쓰는 사람은 한 번은 수동으로
> 새 버전을 받아야 그 다음부터 자동 업데이트가 이어집니다. 마찬가지로 onefile(v1.0.5 이하)에서
> onedir(v1.0.6 이상)로 넘어가는 첫 업데이트도, 실행 파일 위치 자체가 바뀌는 건 아니라서
> (같은 이름의 폴더에 그대로 풀림) 자동 업데이트로 자연스럽게 넘어갑니다.

## GitHub 저장소 공개 관련

이 저장소는 Public이라 누구나 Issue를 등록하거나 Pull Request를 보낼 수 있어요. 하지만 협업자로
초대하지 않은 이상 아무도 `main` 브랜치에 직접 push할 권한은 없고, PR도 메인테이너가 직접
Merge 버튼을 눌러야만 반영됩니다. 즉 남들은 의견/제안만 남길 수 있고, 실제로 코드에 반영할지는
항상 메인테이너가 검토 후 결정합니다.

## 참고 / 문제 해결

- 트레이 팝업은 pywebview로 렌더링돼요. Windows 10/11엔 보통 WebView2 런타임이
  이미 설치되어 있지만, 혹시 팝업이 안 뜨면
  https://developer.microsoft.com/microsoft-edge/webview2/ 에서 설치해보세요.
- 관리자 권한 없이 단축키가 안 먹으면 관리자 권한으로 실행해보세요.
- 설정은 `%APPDATA%\HSSwitch\config.json`에 저장됩니다.
- Phase 4(디스코드 등 특정 앱이 전환을 따라가게 하는 기능)는 아직 포함되지 않았어요.

## 라이선스

[MIT](LICENSE)
