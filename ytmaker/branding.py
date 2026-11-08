"""채널 프로필 사진과 배너 만들기 (매거진 반전 테마와 같은 색, 같은 글꼴).

    python3 -m ytmaker.branding

결과: output/branding/
- profile_a.png, profile_b.png, profile_c.png (800x800, 유튜브가 원으로 잘라 보여줌)
- banner.png (2560x1440)
- check_*.png  (원형으로 잘린 모습, 기기별로 보이는 영역 확인용)
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "output" / "branding"

BG = (16, 16, 16)
INK = (245, 245, 242)
RED = (240, 62, 50)
MUTED = (150, 150, 150)

NAME = "단어해체소"
ACCENT_FROM = 2          # '해체소'부터 빨강 (인트로와 같음)


def font(size, weight="Black"):
    return ImageFont.truetype(str(FONTS / f"Pretendard-{weight}.otf"), int(size))


def glyph(ch, size, color, weight="Black"):
    """글자 하나를 여백 없이 잘라낸 투명 이미지."""
    f = font(size, weight)
    l, t, r, b = f.getbbox(ch)
    im = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - l, 2 - t), ch, font=f, fill=color)
    return im


def paste_center(base, im, cx, cy, angle=0.0):
    if angle:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    base.alpha_composite(im, (int(round(cx - im.width / 2)), int(round(cy - im.height / 2))))


def name_line(size, gap=0.02):
    """'단어해체소' 한 줄 (단어 흰색, 해체소 빨강)."""
    f = font(size)
    parts = [(ch, INK if i < ACCENT_FROM else RED) for i, ch in enumerate(NAME)]
    widths = [f.getlength(ch) for ch, _ in parts]
    g = size * gap
    w = int(sum(widths) + g * (len(parts) - 1)) + 8
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (w, asc + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 4
    for (ch, col), cw in zip(parts, widths):
        d.text((x, 0), ch, font=f, fill=col)
        x += cw + g
    return im.crop(im.getbbox())


def _jamo(ch):
    from .scenes import jamo
    return [j for j, _ in jamo(ch)]


# ------------------------------------------------------------------ 프로필
def profile_a(n=800):
    """두 줄 글자: 단어 / 해체소."""
    im = Image.new("RGBA", (n, n), BG + (255,))
    top = glyph("단어", 0.30 * n, INK)
    bot = glyph("해체소", 0.30 * n, RED)
    # 원 안에 들어가도록 폭 맞춤
    k = min(1.0, 0.70 * n / max(top.width, bot.width))
    top = top.resize((int(top.width * k), int(top.height * k)), Image.LANCZOS)
    bot = bot.resize((int(bot.width * k), int(bot.height * k)), Image.LANCZOS)
    gap = 0.05 * n
    h = top.height + gap + bot.height
    y0 = (n - h) / 2
    paste_center(im, top, n / 2, y0 + top.height / 2)
    paste_center(im, bot, n / 2, y0 + top.height + gap + bot.height / 2)
    return im


def profile_b(n=800):
    """'단'이 자음·모음(ㄷ ㅏ ㄴ)으로 벌어진 모습. 받침 ㄴ만 빨강."""
    im = Image.new("RGBA", (n, n), BG + (255,))
    s = 0.40 * n
    paste_center(im, glyph("ㄷ", s, INK), n * 0.38, n * 0.36, angle=6)
    paste_center(im, glyph("ㅏ", s * 1.15, INK), n * 0.66, n * 0.40, angle=-5)
    paste_center(im, glyph("ㄴ", s, RED), n * 0.47, n * 0.68, angle=-9)
    return im


def profile_c(n=800):
    """'해'를 대각선으로 잘라 두 조각이 어긋난 모습. 잘린 틈에 빨간 선."""
    im = Image.new("RGBA", (n, n), BG + (255,))
    g = glyph("해", 0.62 * n, INK)
    layer = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    paste_center(layer, g, n / 2, n / 2)
    # 왼쪽 아래 → 오른쪽 위로 자르는 선
    p0, p1 = (0.10 * n, 0.78 * n), (0.90 * n, 0.26 * n)
    upper = Image.new("L", (n, n), 0)
    ImageDraw.Draw(upper).polygon([p0, p1, (n, 0), (n, -n), (0, -n), (0, 0), (0, p0[1])], fill=255)
    lower = ImageChops.invert(upper)
    a = layer.copy()
    a.putalpha(ImageChops.multiply(layer.getchannel("A"), upper))
    b = layer.copy()
    b.putalpha(ImageChops.multiply(layer.getchannel("A"), lower))
    # 선에 수직 방향으로 벌림
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    nx, ny = dy / L, -dx / L          # 위쪽 법선
    off = 0.022 * n
    im.alpha_composite(a, (int(round(nx * off)), int(round(ny * off))))
    im.alpha_composite(b, (int(round(-nx * off)), int(round(-ny * off))))
    d = ImageDraw.Draw(im)
    ext = 0.05
    q0 = (p0[0] - dx * ext, p0[1] - dy * ext)
    q1 = (p1[0] + dx * ext, p1[1] + dy * ext)
    d.line([q0, q1], fill=RED, width=max(3, int(0.012 * n)))
    return im


# ------------------------------------------------------------------ 배너
SAFE = (507, 508, 2053, 931)          # 모든 기기에서 보이는 영역 1546x423
DESKTOP = (0, 508, 2560, 931)         # 컴퓨터 화면에서 보이는 띠


def banner(w=2560, h=1440):
    im = Image.new("RGBA", (w, h), BG + (255,))
    rnd = random.Random(7)
    pieces = [j for ch in NAME for j in _jamo(ch)]

    def outside_safe(x, y, r):
        x0, y0, x1, y1 = SAFE
        return x + r < x0 - 40 or x - r > x1 + 40 or y + r < y0 - 30 or y - r > y1 + 30

    # 흩어진 자모 조각: 가운데(모든 기기 영역)는 비워 두고 바깥에만
    placed = []
    tries = 0
    while len(placed) < 52 and tries < 8000:
        tries += 1
        # 처음 14개는 컴퓨터 화면 띠(가운데 가로줄) 안에 먼저 깔아 양옆이 비어 보이지 않게
        y_lo, y_hi = (DESKTOP[1] + 60, DESKTOP[3] - 60) if len(placed) < 14 else (-40, h + 40)
        x, y = rnd.uniform(-40, w + 40), rnd.uniform(y_lo, y_hi)
        size = rnd.uniform(90, 230)
        r = size * 0.55
        if not outside_safe(x, y, r):
            continue
        if any(math.hypot(x - px, y - py) < (r + pr) * 0.9 for px, py, pr in placed):
            continue
        placed.append((x, y, r))
        red = rnd.random() < 0.12
        col = (92, 34, 30) if red else (rnd.randint(38, 52),) * 3
        paste_center(im, glyph(rnd.choice(pieces), size, col), x, y, angle=rnd.uniform(-35, 35))

    # 로고와 한 줄 소개
    logo = name_line(230)
    cx, cy = w / 2, 672
    paste_center(im, logo, cx, cy)
    tag = glyph("매일 쓰는 단어, 어디서 왔을까?", 58, MUTED, weight="Bold")
    paste_center(im, tag, cx, cy + logo.height / 2 + 92)
    d = ImageDraw.Draw(im)
    lw = 120
    ly = cy + logo.height / 2 + 34
    d.line([(cx - lw / 2, ly), (cx + lw / 2, ly)], fill=RED, width=6)
    return im


# ------------------------------------------------------------------ 확인용
def circle_check(imgs, labels):
    """원으로 잘린 큰 모습 + 실제 크기(98px, 36px)를 나란히."""
    cell = 420
    out = Image.new("RGB", (cell * len(imgs), cell + 170), (30, 30, 30))
    f = font(30, "Bold")
    d = ImageDraw.Draw(out)
    for i, (im, lab) in enumerate(zip(imgs, labels)):
        x0 = i * cell
        for size, (ox, oy) in ((360, (30, 20)), (98, (40, 390)), (36, (170, 420))):
            s = im.resize((size, size), Image.LANCZOS)
            m = Image.new("L", (size * 4, size * 4), 0)
            ImageDraw.Draw(m).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
            out.paste(s.convert("RGB"), (x0 + ox, oy), m.resize((size, size), Image.LANCZOS))
        d.text((x0 + 250, 420), lab, font=f, fill=(220, 220, 220))
    return out


def banner_check(b):
    im = b.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    d.rectangle(DESKTOP, outline=(90, 140, 255), width=6)
    d.rectangle(SAFE, outline=(255, 210, 60), width=6)
    f = font(40, "Bold")
    d.text((DESKTOP[0] + 20, DESKTOP[1] - 56), "컴퓨터에서 보이는 영역", font=f, fill=(90, 140, 255))
    d.text((SAFE[0] + 20, SAFE[3] + 14), "모든 기기에서 보이는 영역 (휴대폰)", font=f, fill=(255, 210, 60))
    d.text((24, 20), "TV에서는 전체가 보임", font=f, fill=(200, 200, 200))
    return im.resize((1280, 720), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    profs = [profile_a(), profile_b(), profile_c()]
    for p, k in zip(profs, "abc"):
        p.convert("RGB").save(OUT / f"profile_{k}.png")
    circle_check(profs, ["A", "B", "C"]).save(OUT / "check_profile.png")
    b = banner()
    b.convert("RGB").save(OUT / "banner.png")
    banner_check(b).save(OUT / "check_banner.png")
    # 휴대폰에서 실제로 보이는 부분만 잘라서
    b.convert("RGB").crop(SAFE).save(OUT / "check_banner_mobile.png")
    print("저장:", OUT)


if __name__ == "__main__":
    main()
