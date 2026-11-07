"""색상, 폰트, 그리기 도우미."""
from functools import lru_cache
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 색상 팔레트: 오래된 지도와 사전의 느낌 (짙은 남색 + 호박색)
BG_TOP = (14, 22, 38)
BG_BOTTOM = (8, 12, 22)
INK = (245, 240, 230)        # 본문 글자
MUTED = (150, 160, 180)      # 보조 글자
ACCENT = (242, 181, 68)      # 강조 (호박색)
ACCENT2 = (90, 200, 190)     # 보조 강조 (청록)
RED = (230, 95, 80)
LAND = (34, 48, 74)
LAND_EDGE = (52, 70, 102)
LAND_HI = (120, 92, 44)
CARD = (24, 34, 56)
CARD_EDGE = (60, 78, 112)

_NOTO = "/usr/share/fonts/opentype/noto/"
FONTS = {
    "sans": (_NOTO + "NotoSansCJK-Regular.ttc", 1),
    "sans_bold": (_NOTO + "NotoSansCJK-Bold.ttc", 1),
    "serif": (_NOTO + "NotoSerifCJK-Regular.ttc", 1),
    "serif_bold": (_NOTO + "NotoSerifCJK-Bold.ttc", 1),
}


@lru_cache(maxsize=256)
def font(kind, size):
    path, index = FONTS[kind]
    return ImageFont.truetype(path, max(8, int(size)), index=index)


# ---------- 이징 ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def appear(t, start, dur=0.5):
    """start 시점부터 dur 동안 0→1."""
    return ease_out((t - start) / dur) if dur > 0 else float(t >= start)


def lerp(a, b, x):
    return a + (b - a) * x


def mix(c1, c2, x):
    return tuple(int(lerp(a, b, x)) for a, b in zip(c1, c2))


# ---------- 배경 ----------
@lru_cache(maxsize=4)
def background(w, h):
    """세로 그라데이션 + 비네팅 배경."""
    grad = Image.linear_gradient("L").resize((w, h))
    top = Image.new("RGB", (w, h), BG_TOP)
    bottom = Image.new("RGB", (w, h), BG_BOTTOM)
    img = Image.composite(bottom, top, grad)
    # 비네팅
    vig = Image.radial_gradient("L").resize((w, h))
    dark = Image.new("RGB", (w, h), (3, 5, 10))
    vig = vig.point(lambda v: int(clamp((v - 140) / 115) * 170))
    img = Image.composite(dark, img, vig)
    return img


# ---------- 글자 ----------
def text_size(s, fnt):
    l, t, r, b = fnt.getbbox(s)
    return r - l, b - t


def draw_text(img, xy, s, fnt, fill=INK, alpha=1.0, anchor="mm", dy=0.0, shadow=False):
    """알파(투명도)와 세로 이동(dy)을 지원하는 글자 그리기."""
    if alpha <= 0.01 or not s:
        return
    x, y = xy[0], xy[1] + dy
    if alpha >= 0.99 and not shadow:
        ImageDraw.Draw(img).text((x, y), s, font=fnt, fill=fill, anchor=anchor)
        return
    l, t, r, b = ImageDraw.Draw(img).textbbox((x, y), s, font=fnt, anchor=anchor)
    pad = 12
    box = (int(l) - pad, int(t) - pad, int(r) + pad, int(b) + pad)
    layer = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if shadow:
        d.text((x - box[0] + 3, y - box[1] + 4), s, font=fnt, fill=(0, 0, 0, 160), anchor=anchor)
    d.text((x - box[0], y - box[1]), s, font=fnt, fill=fill + (255,), anchor=anchor)
    if alpha < 0.99:
        a = layer.getchannel("A").point(lambda v: int(v * alpha))
        layer.putalpha(a)
    img.paste(layer, (box[0], box[1]), layer)


def wrap(s, fnt, max_w):
    """단어(공백) 단위로 줄바꿈. 한 단어가 너무 길면 글자 단위로 자른다."""
    lines, cur = [], ""
    for word in s.split(" "):
        cand = word if not cur else cur + " " + word
        if text_size(cand, fnt)[0] <= max_w:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = word
        while text_size(cur, fnt)[0] > max_w and len(cur) > 1:
            cut = len(cur)
            while cut > 1 and text_size(cur[:cut], fnt)[0] > max_w:
                cut -= 1
            lines.append(cur[:cut])
            cur = cur[cut:]
    if cur:
        lines.append(cur)
    return lines


def rounded_box(img, box, radius, fill, outline=None, width=2, alpha=1.0):
    if alpha <= 0.01:
        return
    x0, y0, x1, y1 = [int(v) for v in box]
    layer = Image.new("RGBA", (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    d.rounded_rectangle((0, 0, x1 - x0, y1 - y0), radius, fill=fill + (a,),
                        outline=(outline + (a,)) if outline else None, width=width)
    img.paste(layer, (x0, y0), layer)


def glow(img, center, radius, color, alpha=1.0):
    """부드러운 빛 번짐 효과."""
    if alpha <= 0.01:
        return
    r = int(radius)
    size = r * 2
    layer = Image.new("L", (size, size), 0)
    ImageDraw.Draw(layer).ellipse((r * 0.5, r * 0.5, r * 1.5, r * 1.5), fill=int(150 * alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.3))
    col = Image.new("RGB", (size, size), color)
    img.paste(col, (int(center[0] - r), int(center[1] - r)), layer)


def arrow(draw, p0, p1, color, width, head=None):
    head = head or width * 4
    draw.line([p0, p1], fill=color, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    left = (p1[0] - head * math.cos(ang - 0.45), p1[1] - head * math.sin(ang - 0.45))
    right = (p1[0] - head * math.cos(ang + 0.45), p1[1] - head * math.sin(ang + 0.45))
    draw.polygon([p1, left, right], fill=color)
