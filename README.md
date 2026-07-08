# HSSwitch

스피커 / 헤드셋 / 마이크를 클릭 한 번, 단축키 한 번으로 빠르게 전환하는 Windows 트레이 상주 프로그램.

## 다운로드 (일반 사용자)

바로 쓰고 싶다면 [최신 릴리즈](https://github.com/thdgudtjr0415/HSSwitch/releases/latest)에서 `HSSwitch.exe`만 받으면 됩니다. 설치 프로그램이 아니라 포터블이라 원하는 폴더에 두고 실행하면 끝이에요.

- **트레이 아이콘 좌클릭**: 화면 우측 하단에 프로필/재생장치/녹음장치 팝업이 뜸.
  원하는 항목 클릭하면 즉시 전환. 4.5초간 아무 조작이 없으면 자동으로 닫힘.
- **트레이 아이콘 우클릭**: 열기(메인 창) / 종료
- **볼륨 슬라이더 왼쪽 아이콘**: 클릭하면 해당 장치 음소거 토글 (재생/녹음 둘 다 지원)
- **메인 창 - 개별 전환 탭**: 재생/녹음 장치를 각각 골라 전환
- **메인 창 - 프로필 탭**: 재생+녹음 조합을 이름/아이콘/단축키와 함께 저장, 전환
- **메인 창 - 장치 별칭 탭**: Windows가 붙인 장치 이름 대신 보여줄 별명 지정
- **메인 창 - 설정 탭**: 라이트/다크 모드 선택 (트레이 팝업에만 적용되고, 메인 창
  자체 모양은 바뀌지 않음), Windows 부팅 시 자동 실행 켜기/끄기, 업데이트 확인
- **자동 업데이트**: 새 버전이 올라오면 실행 시 알림이 뜨고, 확인을 누르면 자동으로
  받아서 교체 후 재시작됩니다.

## 개발 (소스에서 실행)

```powershell
git clone https://github.com/thdgudtjr0415/HSSwitch.git
cd HSSwitch
pip install -r requirements.txt
python main.py
```

## exe로 빌드

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/icon.ico --name HSSwitch main.py
```

`assets/icon.ico`는 헤드셋+마이크 라인 아이콘으로 미리 만들어둔 멀티 사이즈 아이콘이에요
(48px 이상은 "HS" 글자 배지 포함, 32px 이하는 아이콘만 — 작은 크기에서 글자가
뭉개지는 걸 방지).

## 참고

- 트레이 팝업은 pywebview로 렌더링돼요. Windows 10/11엔 보통 WebView2 런타임이
  이미 설치되어 있지만, 혹시 팝업이 안 뜨면
  https://developer.microsoft.com/microsoft-edge/webview2/ 에서 설치해보세요.
- 관리자 권한 없이 단축키가 안 먹으면 관리자 권한으로 실행해보세요.
- 설정은 `%APPDATA%\HSSwitch\config.json`에 저장됩니다.
- Phase 4(디스코드 등 특정 앱이 전환을 따라가게 하는 기능)는 아직 포함되지 않았어요.
