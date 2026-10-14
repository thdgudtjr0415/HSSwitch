"""
프로필에 지정하는 사용자 아이콘 이미지를 저장하고 불러오는 모듈.

고른 이미지는 정사각형 64x64 PNG로 다시 저장해서 %APPDATA%\\HSSwitch\\icons 에 둔다.
(원본 파일 형식/크기와 무관하게 항상 같은 형태가 되고, config.json에는 파일 이름만 기록한다.
업데이트는 설치 폴더만 덮어쓰므로 이 폴더의 이미지는 업데이트 후에도 남는다.)
"""

import base64
import io
import os
import uuid

from PIL import Image, ImageGrab

ICON_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "HSSwitch", "icons"
)
ICON_SIZE = 64


def _path(name: str) -> str:
    return os.path.join(ICON_DIR, os.path.basename(name))  # config가 손상돼도 폴더 밖은 못 건드리게


def save_icon_image(image: Image.Image) -> str:
    """이미지를 비율 유지한 채 64x64 투명 캔버스 가운데에 맞춰 저장하고 파일 이름을 돌려준다."""
    image = image.convert("RGBA")
    image.thumbnail((ICON_SIZE, ICON_SIZE))
    canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    canvas.paste(image, ((ICON_SIZE - image.width) // 2, (ICON_SIZE - image.height) // 2))
    os.makedirs(ICON_DIR, exist_ok=True)
    name = f"{uuid.uuid4().hex}.png"
    canvas.save(_path(name))
    return name


def load_icon_image(name: str | None) -> Image.Image | None:
    """저장된 아이콘을 불러온다. 파일이 없거나 깨졌으면 None."""
    if not name:
        return None
    try:
        with Image.open(_path(name)) as img:
            return img.convert("RGBA")
    except Exception:
        return None


def delete_icon_image(name: str | None):
    if not name:
        return
    try:
        os.remove(_path(name))
    except OSError:
        pass  # 이미 없으면 그대로 둔다


def icon_data_uri(name: str | None) -> str | None:
    """팝업(HTML)의 <img src>에 넣을 data URI. 이미지가 없으면 None."""
    img = load_icon_image(name)
    if img is None:
        return None
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def open_image_file(path: str) -> Image.Image:
    """파일을 이미지로 연다. 이미지가 아니면 예외가 난다."""
    with Image.open(path) as img:
        return img.convert("RGBA")


def get_clipboard_image() -> Image.Image | None:
    """클립보드의 이미지(캡처 등) 또는 탐색기에서 복사한 이미지 파일을 가져온다. 없으면 None."""
    try:
        content = ImageGrab.grabclipboard()
        if isinstance(content, list):  # 파일을 복사한 경우: 경로 목록
            return open_image_file(content[0])
        if isinstance(content, Image.Image):
            return content.convert("RGBA")
    except Exception:
        pass
    return None
