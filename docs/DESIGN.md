---
version: alpha
name: HSSwitch-tray-popup
description: >
  Windows 트레이에서 열리는 작은 오디오 전환 팝업(332px 폭, 프레임 없음)의 디자인 규칙.
  iOS 시스템 UI에 가까운 조용한 톤: 라이트는 #f6f6f8 바탕에 흰 카드, 다크는 #1c1c1e 바탕에
  #2c2c2e 카드. 강조색은 시스템 블루 하나(#007AFF / #0A84FF)뿐이고, 상태는 색 대신
  "사용 중" 같은 짧은 글자와 테두리로 알린다. 그림자와 장식은 거의 쓰지 않는다.
  이 문서는 새 디자인이 아니라 v1.1.10 이후 코드에 이미 있는 값을 정리한 것이다.

# 값의 출처: theme_manager.py (LIGHT / DARK). 새 색이 필요하면 두 딕셔너리에 같이 추가한다.
colors:
  popup-bg: "#f6f6f8"
  card-bg: "#ffffff"
  card-hover: "#efeff2"
  accent: "#007AFF"
  fg: "#1c1c1e"
  fg-muted: "#8a8a8e"
  fg-on-accent: "#ffffff"
  divider: "#e5e5ea"
  slider-track: "#e5e5ea"
colors-dark:
  popup-bg: "#1c1c1e"
  card-bg: "#2c2c2e"
  card-hover: "#3a3a3c"
  accent: "#0A84FF"
  fg: "#f2f2f2"
  fg-muted: "#9a9a9a"
  fg-on-accent: "#ffffff"
  divider: "#38383a"
  slider-track: "#3a3a3c"
# 팔레트에 없고 CSS에 직접 박혀 있는 색 (Known Gaps 참고)
colors-hardcoded:
  danger: "#e2534a"
  current-hint: "#3ddc97"
  overlay: "rgba(0,0,0,0.5)"
  slider-thumb: "white"

typography:
  family: "-apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif"
  section-label: { fontSize: 11px, fontWeight: 600, letterSpacing: 0.3px }
  tile-label: { fontSize: 10.5px }
  tile-state: { fontSize: 9.5px }
  row-label: { fontSize: 13px }
  form-title: { fontSize: 13px, fontWeight: 600 }
  field-label: { fontSize: 11px }
  input: { fontSize: 13px }
  button: { fontSize: 13px, fontWeight: 600 }
  caption: { fontSize: 11px }
  menu-item: { fontSize: 12px }

rounded:
  slider: 2px
  num-input: 6px
  input: 8px
  menu: 8px
  modal: 12px
  card: 14px
  tile: 16px
  window: 10px

spacing:
  popup-padding: 16px
  section-gap-top: 14px
  section-gap-bottom: 8px
  grid-gap: 10px
  row-padding: 10px 14px
  field-gap: 12px

layout:
  popup-width: 332px
  popup-height: 420px ~ 820px (프로필/장치 수로 계산, 열 때 한 번만)
  anchor: 화면 오른쪽 아래, 오른쪽 12px / 아래 16px
  tile-height: 76px
  tile-columns: 3
  auto-close: 4.5초 동안 마우스/키 입력이 없거나 창이 포커스를 잃으면 닫힘

components:
  tile:
    backgroundColor: "{colors.card-bg}"
    rounded: "{rounded.tile}"
    height: 76px
  tile-active:
    boxShadow: "inset 0 0 0 1.5px {colors.accent}"
    stateTextColor: "{colors.accent}"
  tile-offline:
    opacity: 0.55
  card:
    backgroundColor: "{colors.card-bg}"
    rounded: "{rounded.card}"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.fg-on-accent}"
    rounded: "{rounded.input}"
    padding: 9px
  input:
    backgroundColor: "{colors.card-bg}"
    textColor: "{colors.fg}"
    rounded: "{rounded.input}"
    padding: 8px 10px
---

# HSSwitch 트레이 팝업 디자인

## 개요

트레이 아이콘을 눌렀을 때 3초 안에 "지금 무엇이 켜져 있고, 한 번에 무엇으로 바꿀 수 있는지"를
보여주는 작은 팝업이다. 사용자는 하던 일을 멈추고 잠깐 보는 것이므로 **읽는 시간보다 누르는 시간이
짧아야** 한다. 그래서 장식은 줄이고, 눌러야 할 것(프로필 타일, 장치 행)과 지금 상태(사용 중, 체크,
볼륨)만 보이게 한다.

- 기준 감각: iOS 시스템 UI의 회색 계열과 시스템 블루. 특정 브랜드를 복제한 것은 아니다.
- 구조: `프로필 타일(3열)` → `재생 장치 카드 + 볼륨` → `녹음 장치 카드 + 볼륨`. 폼(추가/수정)은 같은 창 안에서 화면만 갈아끼운다.
- 한 곳에만 힘을 준다: **강조색은 "지금 상태"와 "저장" 버튼에만** 쓴다.

## 색

라이트/다크 모두 `theme_manager.py`의 팔레트에서 가져온다. CSS에서는 `{p['card_bg']}`처럼 참조하고
색 값을 직접 쓰지 않는다.

| 역할 | 라이트 | 다크 | 어디에 |
|---|---|---|---|
| popup-bg | `#f6f6f8` | `#1c1c1e` | 팝업 바탕 |
| card-bg | `#ffffff` | `#2c2c2e` | 타일, 장치 카드, 입력칸, 메뉴, 모달 |
| card-hover | `#efeff2` | `#3a3a3c` | 타일/행 마우스 올림, 모달 취소 버튼 |
| accent | `#007AFF` | `#0A84FF` | 체크, "사용 중" 테두리와 글자, 음소거 아이콘, 볼륨 말풍선, 저장 버튼 |
| fg / fg-muted | `#1c1c1e` / `#8a8a8e` | `#f2f2f2` / `#9a9a9a` | 본문 / 보조 글자, 섹션 제목, 아이콘 |
| divider | `#e5e5ea` | `#38383a` | 장치 행 사이 0.5px 선 |
| slider-track | `#e5e5ea` | `#3a3a3c` | 볼륨 슬라이더 바 |

- 위험(삭제, 오류)은 `#e2534a`, 현재 선택 표시는 `#3ddc97`이다. 두 색은 아직 팔레트에 없다 (Known Gaps).
- 색만으로 상태를 알리지 않는다. "사용 중", "장치 없음", 체크 아이콘을 항상 같이 쓴다.

## 글꼴

`-apple-system, 'Segoe UI', 'Helvetica Neue', sans-serif` 한 가지만 쓴다. Windows에서는 Segoe UI로 표시된다.
크기는 9.5px~13px의 작은 범위이고, 굵기 변화는 두 단계(400 / 600)가 기본이다.

| 쓰임 | 크기 / 굵기 |
|---|---|
| 섹션 제목 ("프로필", "재생 장치") | 11px / 600, 자간 0.3px, 보조색 |
| 장치 이름, 입력칸 글자 | 13px |
| 폼 제목, 저장 버튼 | 13px / 600 |
| 프로필 타일 이름 | 10.5px |
| 타일 상태 ("사용 중", "장치 없음") | 9.5px, 사용 중은 600 + 강조색 |
| 필드 라벨, 오류/안내 문구 | 11px |
| 메뉴 항목, 모달 버튼 | 12px |

장치 이름은 길어서(예: "헤드셋 이어폰(CORSAIR HS80 RGB Wireless Gaming Headset)") 두 줄로 줄바꿈된다.
잘라내지 말고 줄바꿈한다.

## 모양과 간격

- 모서리: 타일 16, 카드 14, 모달 12, 입력/메뉴/버튼 8, 숫자칸 6, 슬라이더 2. 창 자체는 GDI로 약 10px 둥글게 자른다.
- 바깥 여백 16px. 섹션 제목은 위 14px / 아래 8px(맨 위 제목만 위 0). 타일 간격 10px, 필드 사이 12px.
- 장치 행: 위아래 10px, 좌우 14px, 아이콘과 글자 사이 10px, 행 사이 0.5px 구분선.
- 깊이는 그림자가 아니라 **바탕(popup-bg)과 카드(card-bg)의 명도 차**로 만든다. 그림자는 우클릭 메뉴(`0 4px 16px rgba(0,0,0,.35)`)와 슬라이더 손잡이에만 있다.

## 컴포넌트

**프로필 타일** (76px, 3열). 아이콘 20px 위, 이름 아래.
- 기본: card-bg, 마우스 올리면 card-hover (0.1초).
- 사용 중: 안쪽 1.5px 강조색 테두리 + 이름 아래 "사용 중" (강조색, 600).
- 장치 없음: 불투명도 0.55 + "장치 없음" (보조색). 눌러도 시도는 하고, 실패하면 안내가 뜬다.
- 추가: 점선이 아니라 같은 타일에 `+` 아이콘, 보조색.
- 우클릭: "수정 / 삭제" 메뉴(최소 폭 96px, 삭제는 `danger`색).

**장치 카드.** 장치 행 목록. 지금 기본 장치는 오른쪽에 강조색 체크(15px). 행 전체가 눌리는 영역이다.

**볼륨 줄.** `[스피커 아이콘] [슬라이더] [숫자칸 34px]`.
- 슬라이더 바 4px, 손잡이 흰색 16px 원. 드래그 중에만 위에 값 말풍선(강조색 바탕)이 뜨고 놓은 뒤 0.5초 뒤 사라진다.
- 음소거면 아이콘이 X 모양으로 바뀌고 강조색이 된다.
- 숫자칸은 `type="text" inputmode="numeric"`. `type="number"`는 스핀 버튼이 생겨서 쓰지 않는다. 0~100으로 자른다.

**폼 (추가/수정).** 헤더 `‹ 뒤로` + 제목, 필드(이름, 아이콘, 재생 장치, 녹음 장치, 단축키), 전체 폭 저장 버튼.
- 입력칸은 테두리 없이 card-bg 바탕. 포커스는 이름 칸에 자동으로 준다.
- 추가 모드는 지금 쓰는 장치를 미리 선택하고 라벨 옆에 "· 현재 사용 중"을 붙인다.
- 아이콘 선택은 한글 이름(기본/헤드셋/스피커/마이크)으로 보인다. 저장되는 값은 영문 키다.

**삭제 확인 모달.** 브라우저 `confirm()`이 아니라 자체 모달(폭 230px, 취소 / 삭제). `confirm()`은 프레임 없는 창에서 위치와 스타일이 어긋난다.

**아이콘.** 인라인 SVG, `viewBox 0 0 24 24`, 선 두께 1.8, 둥근 끝, `currentColor`. 타일 20px, 행 16px, 체크/볼륨 15px. 종류: headset, speaker, speaker_muted, mic, plus, check, default. 새 아이콘도 같은 선 규격을 쓴다.

## 글(카피)

- 문장은 해요체, 문장 부호는 마침표. 버튼과 라벨은 짧은 명사/동사: 저장, 삭제, 추가, 수정, 취소, 뒤로.
- 같은 동작은 화면 어디서나 같은 이름. "프로필", "재생 장치", "녹음 장치", "사용 중", "장치 없음"을 바꿔 쓰지 않는다.
- 오류는 **무슨 일이 생겼는지와 무엇을 하면 되는지**를 말한다. 사과하지 않는다.
  예: "재생 장치를 바꾸지 못했어요. 장치가 켜져 있고 연결돼 있는지 확인해 주세요."
- 빈 화면은 할 일을 알려준다: "저장된 프로필이 없어요. 눌러서 추가해보세요."

## 움직임

사용자 동작에 대한 반응만 있다: 타일/행 hover 0.1초, 볼륨 말풍선 투명도 0.15초.
혼자 움직이는 연출은 쓰지 않는다. 팝업은 4.5초 동안 입력이 없거나 포커스를 잃으면 닫히므로,
**팝업 안에서 사용자가 오래 머물러야 하는 새 기능**(긴 입력 등)을 넣을 때는 이 닫힘 규칙부터 검토한다.

## Do / Don't

Do
- 색은 `theme_manager.py`의 팔레트 키로만 쓰고, 새 색은 LIGHT와 DARK에 함께 추가한다.
- 상태는 글자 + 테두리/아이콘으로 알린다 (색만으로 알리지 않는다).
- 오류와 실패는 사용자가 닫은 뒤에도 알 수 있게 상태바나 트레이 알림으로도 남긴다.
- 팝업 크기와 위치는 열 때 한 번만 계산한다. 프로필을 추가/삭제해도 다시 계산하지 않는다.

Don't
- 브라우저 기본 `confirm()`/`alert()`, `type="number"` 입력을 쓰지 않는다.
- 강조색을 장식으로 쓰지 않는다. "지금 상태"와 "주 동작" 둘에만 쓴다.
- 카드마다 그림자를 넣거나 그라디언트를 쓰지 않는다.
- 팝업 UI 때문에 pywebview를 백그라운드 스레드에서 다루지 않는다 (CLAUDE.md의 스레딩 제약).
- 트레이 팝업의 스타일을 메인 창(tkinter)에 억지로 맞추지 않는다. 메인 창은 Windows 기본(vista) 테마를 쓴다.

## 반응형 / 화면

고정 폭 332px의 팝업이라 반응형 규칙은 없다. 높이는 `_compute_geometry`가 프로필 줄 수와 장치 수로
계산하며 420~820px로 제한한다. 프로필이 매우 많으면 아래쪽이 잘릴 수 있다.

## Known Gaps (확인된 빈틈)

값은 직접 계산한 근사치이며 도구로 재검증한 것은 아니다.

1. **팔레트 밖의 색**: `#e2534a`(위험), `#3ddc97`(현재 선택), 모달 오버레이가 CSS에 직접 박혀 있다. 팔레트로 옮기면 라이트/다크를 따로 조정할 수 있다.
2. **라이트 모드 대비 부족**: "· 현재 사용 중" 글자(`#3ddc97`)는 밝은 바탕에서 대비가 약 1.6:1로 매우 낮다. 보조 글자색 `#8a8a8e`도 `#f6f6f8` 위에서 약 3.2:1이라 작은 글자 기준(4.5:1)에 못 미친다. 저장 버튼의 흰 글자(`#007AFF` 위)도 약 4:1이다.
3. **키보드 접근성**: 타일과 장치 행이 `div + onclick`이라 Tab으로 이동할 수 없고, 입력칸은 `outline: none`이라 포커스 표시가 없다.
4. **높이 고정**: 프로필이 많아질 때의 스크롤 정책이 없다.
5. **메인 창(tkinter)**: 이 문서의 범위 밖이다. 별도 스타일 규칙이 없고, 편집창의 "현재 사용 중" 글자색(`#0f6e56`)만 팝업과 다르다.
6. **글꼴 확인**: 실제로 어떤 글꼴로 그려지는지는 사용자 PC에 따라 다르다. Windows에서는 Segoe UI가 쓰일 것으로 보지만 화면 확인은 하지 않았다.
