"""그림 불러오기: 아이콘, 국기, 직접 그린 일러스트, (나중에) AI 이미지.

대본에서는 이렇게 쓴다.
    icon:bread       → assets/icons/bread.svg      (Fluent Emoji, MIT)
    flag:pt          → assets/flags/pt.svg         (flag-icons, MIT)
    custom:carrack   → assets/custom/carrack.svg   (이 저장소에서 직접 그림)
    photo:a.jpg      → assets/photos/a.jpg         (실제 사진: 둥근 모서리 + 흰 테두리, 출처는 SOURCE.txt)
    logo:dcinside    → assets/photos/dcinside.svg  (로고: 흰 판 위에 올림, 출처는 SOURCE.txt)
    episodes/.../img/scene1.png                   → 그 밖의 경로는 파일 그대로 (AI 이미지 등)
"""
import io
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
PREFIX = {"icon": "assets/icons", "flag": "assets/flags", "custom": "assets/custom"}


def resolve(name):
    if ":" in name:
        kind, key = name.split(":", 1)
        if kind in PREFIX:
            return ROOT / PREFIX[kind] / f"{key}.svg"
        if kind == "photo":
            return ROOT / "assets/photos" / key
        if kind == "logo":
            return ROOT / "assets/photos" / f"{key}.svg"
    return ROOT / name


@lru_cache(maxsize=512)
def image(name, size, flip=False):
    """name 그림을 긴 변이 size 픽셀이 되도록 RGBA 로 반환."""
    size = max(4, int(size))
    path = resolve(name)
    if path.suffix == ".svg":
        import cairosvg
        png = cairosvg.svg2png(url=str(path), output_width=size * 2)
        im = Image.open(io.BytesIO(png)).convert("RGBA")
    else:
        im = Image.open(path).convert("RGBA")
    w, h = im.size
    k = size / max(w, h)
    im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    if name.startswith("flag:"):
        im = _flag_style(im)
    elif name.startswith("photo:"):
        im = _photo_style(im)
    elif name.startswith("logo:"):
        im = _logo_style(im)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im


def _photo_style(im):
    """실제 사진: 흰 테두리 + 둥근 모서리 (어두운 배경 위에서 '사진'으로 읽히게)."""
    w, h = im.size
    b = max(3, int(max(w, h) * 0.018))
    r = max(3, int(min(w, h) * 0.04))
    out = Image.new("RGBA", (w + b * 2, h + b * 2), (0, 0, 0, 0))
    ImageDraw.Draw(out).rounded_rectangle((0, 0, out.width - 1, out.height - 1), r + b, fill=(242, 242, 238, 255))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    out.paste(im, (b, b), mask)
    return out


def _logo_style(im):
    """로고: 원래 색이 어두운 배경에 묻히지 않게 흰 판 위에 올린다."""
    w, h = im.size
    px, py = int(w * 0.08), int(h * 0.22)
    out = Image.new("RGBA", (w + px * 2, h + py * 2), (0, 0, 0, 0))
    ImageDraw.Draw(out).rounded_rectangle((0, 0, out.width - 1, out.height - 1),
                                          int(min(out.size) * 0.18), fill=(250, 250, 250, 255))
    out.alpha_composite(im, (px, py))
    return out


def _flag_style(im):
    """국기: 둥근 모서리 + 얇은 테두리 (흰 바탕 국기가 배경에 묻히지 않게)."""
    w, h = im.size
    r = max(2, int(min(w, h) * 0.12))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    ImageDraw.Draw(out).rounded_rectangle((0, 0, w - 1, h - 1), r, outline=(255, 255, 255, 90),
                                          width=max(1, w // 60))
    return out


@lru_cache(maxsize=256)
def _shadow(name, size, flip):
    im = image(name, size, flip)
    pad = int(size * 0.12)
    sh = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    a = im.getchannel("A").point(lambda v: int(v * 0.45))
    sh.paste((0, 0, 0, 255), (pad, pad), a)
    return sh.filter(ImageFilter.GaussianBlur(pad / 2.5)), pad


def place(img, name, center, size, alpha=1.0, flip=False, shadow=True, rotate=0.0):
    """그림을 center 에 그린다. 크기는 정수로 반올림해 캐시를 재사용한다."""
    if alpha <= 0.01 or size < 4:
        return
    size = int(round(size / 2) * 2)
    im = image(name, size, flip)
    if shadow and not name.startswith("flag:"):
        sh, pad = _shadow(name, size, flip)
        # 그림자는 그림보다 늦게 나타나게 (반투명 그림 뒤로 그림자가 비쳐 탁해 보이는 것 방지)
        _paste(img, sh, (center[0] + size * 0.03, center[1] + size * 0.06), alpha ** 3 * 0.8, rotate)
    _paste(img, im, center, alpha, rotate)


def _paste(img, im, center, alpha, rotate):
    if rotate:
        im = im.rotate(rotate, expand=True, resample=Image.BICUBIC)
    if alpha < 0.99:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    # 소수점 위치까지 반영 (정수로 자르면 느린 움직임이 '움직임-멈춤'으로 끊겨 보인다)
    x = center[0] - im.width / 2
    y = center[1] - im.height / 2
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    if fx > 0.02 or fy > 0.02:
        im = im.transform((im.width + 1, im.height + 1), Image.AFFINE, (1, 0, -fx, 0, 1, -fy),
                          resample=Image.BILINEAR)
    img.paste(im, (ix, iy), im)
