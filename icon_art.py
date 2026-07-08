"""
헤드셋+마이크 결합 아이콘을 PIL로 그리는 공용 모듈.
트레이 아이콘(작게, 글자 없이)과 exe 아이콘(크게, HS 글자 포함) 양쪽에서 재사용한다.
"""

from PIL import Image, ImageDraw, ImageFont

ACCENT = (10, 132, 255, 255)


def draw_headset_mic(size: int, color=ACCENT) -> Image.Image:
    """배경 없이 선(line)으로만 그린 헤드셋+마이크 아이콘. 트레이 아이콘용."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w = max(2, round(size * 0.06))

    band_box = (size * 0.18, size * 0.10, size * 0.82, size * 0.62)
    draw.arc(band_box, start=200, end=340, fill=color, width=w)

    cup_w, cup_h = size * 0.16, size * 0.24
    cup_y = size * 0.42
    draw.rounded_rectangle(
        (size * 0.13, cup_y, size * 0.13 + cup_w, cup_y + cup_h),
        radius=cup_w * 0.4, outline=color, width=w,
    )
    draw.rounded_rectangle(
        (size * 0.87 - cup_w, cup_y, size * 0.87, cup_y + cup_h),
        radius=cup_w * 0.4, outline=color, width=w,
    )

    boom_start = (size * 0.87 - cup_w * 0.3, cup_y + cup_h * 0.7)
    boom_mid = (size * 0.66, size * 0.80)
    boom_end = (size * 0.50, size * 0.82)
    draw.line([boom_start, boom_mid, boom_end], fill=color, width=max(2, round(w * 0.75)), joint="curve")

    mic_r = size * 0.045
    draw.ellipse(
        (boom_end[0] - mic_r, boom_end[1] - mic_r, boom_end[0] + mic_r, boom_end[1] + mic_r),
        outline=color, width=max(2, round(w * 0.75)),
    )
    return img


def draw_app_icon(size: int, with_badge: bool = True) -> Image.Image:
    """exe/앱 아이콘용. 큰 사이즈에서만 우측 하단에 HS 글자 배지를 추가한다."""
    img = draw_headset_mic(size, color=ACCENT)

    if with_badge:
        draw = ImageDraw.Draw(img)
        badge_r = size * 0.24
        cx, cy = size * 0.78, size * 0.78
        draw.ellipse(
            (cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r),
            fill=(255, 255, 255, 255),
        )
        draw.ellipse(
            (cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r),
            outline=ACCENT, width=max(2, round(size * 0.012)),
        )
        try:
            font = ImageFont.truetype("arialbd.ttf", round(badge_r * 0.85))
        except Exception:
            font = ImageFont.load_default()
        text = "HS"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]), text, fill=ACCENT, font=font
        )

    return img
