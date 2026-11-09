"""색상, 폰트, 그리기 도우미."""
from functools import lru_cache
import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .themes import THEMES

THEME = "midnight"
_T = {}


def use(name):
    """테마를 바꾼다. 색 이름(S.INK 등)과 폰트, 배경, 카드 모양이 한꺼번에 바뀐다."""
    global THEME, _T
    if name not in THEMES:
        raise SystemExit(f"없는 테마: {name} (사용 가능: {', '.join(THEMES)})")
    THEME = name
    _T = THEMES[name]
    globals().update(_T["colors"])


def opt(key, default=None):
    return _T.get(key, default)


@lru_cache(maxsize=512)
def _font(path, index, size):
    return ImageFont.truetype(path, max(8, int(size)), index=index)


_FALLBACK = {
    False: ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 1),
    True: ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 1),
}


@lru_cache(maxsize=32)
def _cmap(path, index):
    """폰트에 들어 있는 글자 목록."""
    from fontTools.ttLib import TTFont
    f = TTFont(path, fontNumber=index, lazy=True)
    return frozenset(f.getBestCmap().keys())


def font(kind, size):
    path, index, scale = _T["fonts"][kind]
    f = _font(path, index, int(size * scale))
    if not hasattr(f, "_cmap"):
        f._cmap = _cmap(path, index)
        fp, fi = _FALLBACK["bold" in kind]
        f._fallback = _font(fp, fi, int(size * scale)) if fp != path else None
    return f


def _old_jamo(ch):
    """옛한글 조합용 자모 (ᄒ, ᆡ, ᆼ, ㆍ 방점 등). 글자 하나로 조합하려면 한 폰트로 그려야 한다."""
    o = ord(ch)
    return 0x1100 <= o <= 0x11FF or 0xA960 <= o <= 0xA97F or 0xD7B0 <= o <= 0xD7FF or o in (0x302E, 0x302F)


def _runs(s, fnt):
    """테마 폰트에 없는 글자는 대체 폰트로: [(글자들, 폰트), ...]
    옛한글(조합용 자모)은 테마 폰트가 조합하지 못하므로 대체 폰트로 그린다.
    '쥬ᇰ'처럼 완성형 뒤에 받침 자모가 붙으면 앞 글자도 같은 폰트로 묶는다."""
    cmap = getattr(fnt, "_cmap", None)
    fb = getattr(fnt, "_fallback", None)
    if not cmap or fb is None or all((ord(ch) in cmap and not _old_jamo(ch)) or ch == " " for ch in s):
        return [(s, fnt)]
    runs = []
    for i, ch in enumerate(s):
        nxt_jamo = i + 1 < len(s) and _old_jamo(s[i + 1]) and 0x1160 <= ord(s[i + 1]) <= 0x11FF
        own = (ord(ch) in cmap and not _old_jamo(ch) and not nxt_jamo) or ch == " "
        f = fnt if own else fb
        if runs and runs[-1][1] is f:
            runs[-1] = (runs[-1][0] + ch, f)
        else:
            runs.append((ch, f))
    return runs


def _render_runs(runs, fill):
    asc = max(f.getmetrics()[0] for _, f in runs)
    desc = max(f.getmetrics()[1] for _, f in runs)
    width = sum(f.getlength(t) for t, f in runs)
    im = Image.new("RGBA", (int(width) + 8, asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 4
    for t, f in runs:
        d.text((x, 4 + asc), t, font=f, fill=fill + (255,), anchor="ls")
        x += f.getlength(t)
    return im


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
def background(w, h):
    return _background(THEME, w, h)


@lru_cache(maxsize=8)
def _background(theme, w, h):
    import numpy as np
    kind = _T.get("bg", "gradient")
    grad = Image.linear_gradient("L").resize((w, h))
    img = Image.composite(Image.new("RGB", (w, h), BG_BOTTOM), Image.new("RGB", (w, h), BG_TOP), grad)
    rng = np.random.default_rng(7)
    if kind in ("paper", "chalk"):
        # 종이 결 / 분필 가루: 거친 노이즈 + 큰 얼룩
        fine = rng.normal(0, 1, (h, w))
        blot = Image.fromarray((rng.random((h // 40 + 1, w // 40 + 1)) * 255).astype("uint8")).resize(
            (w, h), Image.BICUBIC)
        blot = (np.asarray(blot, dtype=np.float32) / 255 - 0.5)
        k = (6, 22) if kind == "paper" else (5, 14)
        arr = np.asarray(img, dtype=np.float32) + fine[..., None] * k[0] + blot[..., None] * k[1]
        img = Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))
    if kind == "dots":
        d = ImageDraw.Draw(img)
        step = 34
        col = _T.get("pattern", (0, 0, 0))
        for y in range(0, h + step, step):
            for x in range((y // step % 2) * step // 2, w + step, step):
                d.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), fill=col)
    if kind == "grid":
        d = ImageDraw.Draw(img)
        col = _T.get("pattern", (255, 255, 255))
        for i, step in enumerate((40, 200)):
            c = mix(BG_TOP, col, 0.08 if i == 0 else 0.18)
            for x in range(0, w, step):
                d.line([(x, 0), (x, h)], fill=c, width=1 + i)
            for y in range(0, h, step):
                d.line([(0, y), (w, y)], fill=c, width=1 + i)
    vig_amt = _T.get("vignette", 170)
    if vig_amt:
        vig = Image.radial_gradient("L").resize((w, h)).point(
            lambda v: int(clamp((v - 140) / 115) * vig_amt))
        img = Image.composite(Image.new("RGB", (w, h), _T.get("vignette_color", (3, 5, 10))), img, vig)
    return img


# ---------- 글자 ----------
def text_size(s, fnt):
    runs = _runs(s, fnt)
    if len(runs) > 1 or runs[0][1] is not fnt:
        asc = max(f.getmetrics()[0] for _, f in runs)
        desc = max(f.getmetrics()[1] for _, f in runs)
        return int(sum(f.getlength(t) for t, f in runs)), int((asc + desc) * 0.8)
    l, t, r, b = fnt.getbbox(s)
    return r - l, b - t


def draw_text(img, xy, s, fnt, fill=None, alpha=1.0, anchor="mm", dy=0.0, shadow=False):
    """알파(투명도)와 세로 이동(dy)을 지원하는 글자 그리기."""
    fill = fill or INK
    if alpha <= 0.01 or not s:
        return
    shadow = shadow and _T.get("text_shadow", True)
    x, y = xy[0], xy[1] + dy
    runs = _runs(s, fnt)
    if len(runs) > 1 or runs[0][1] is not fnt:
        # 대체 폰트가 섞인 글자: 따로 그려서 anchor 에 맞춰 붙인다
        im = _render_runs(runs, fill)
        h_anchor, v_anchor = anchor[0], anchor[1]
        px = x - (im.width / 2 if h_anchor == "m" else im.width if h_anchor == "r" else 0)
        py = y - (im.height / 2 if v_anchor == "m" else im.height if v_anchor in "bd" else 0)
        if alpha < 0.99:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        img.paste(im, (int(px), int(py)), im)
        return
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


def _greedy(words, fnt, max_w):
    lines, cur = [], ""
    for word in words:
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


def wrap(s, fnt, max_w, balance=True):
    """줄바꿈.
    - 대본의 줄바꿈(\n)은 그대로 지킨다
    - 화살표(→)는 앞뒤 단어와 붙여서 줄 처음이나 끝에 혼자 남지 않게 한다
    - balance: 줄 수는 그대로 두고 줄 길이를 고르게 (마지막 줄에 한두 단어만 남는 것 방지)
    """
    out = []
    for para in str(s).split("\n"):
        words = para.split(" ")
        glued = []
        for wd in words:
            if glued and (wd == "→" or glued[-1].endswith("→")):
                glued[-1] = glued[-1] + "\u00a0" + wd
            else:
                glued.append(wd)
        # 붙인 덩어리가 한 줄보다 길면 화살표 앞에서 끊을 수 있게 다시 푼다
        fixed = []
        for g in glued:
            if "\u00a0" in g and text_size(g.replace("\u00a0", " "), fnt)[0] > max_w:
                bits = g.split("\u00a0")
                cur = bits[0]
                for b in bits[1:]:
                    if b == "→":
                        fixed.append(cur)
                        cur = b
                    else:
                        cur += "\u00a0" + b
                fixed.append(cur)
            else:
                fixed.append(g)
        glued = fixed
        lines = _greedy(glued, fnt, max_w)
        if balance and len(lines) > 1:
            lo, hi = max_w * 0.4, max_w
            for _ in range(12):
                mid = (lo + hi) / 2
                if len(_greedy(glued, fnt, mid)) <= len(lines):
                    hi = mid
                else:
                    lo = mid
            lines = _greedy(glued, fnt, hi)
        out += [ln.replace("\u00a0", " ") for ln in lines]
    return out


def draw_arrow(img, start, length, color, size, direction="right", alpha=1.0):
    """글자 대신 직접 그리는 깔끔한 화살표. size = 글자 크기 기준 두께."""
    if alpha <= 0.01:
        return
    w = max(2, int(size * 0.09))
    head = size * 0.32
    x, y = start
    layer = Image.new("RGBA", img.size if False else (int(length + head * 2 + 8), int(length + head * 2 + 8)),
                      (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = color + (int(255 * alpha),)
    o = head + 4
    if direction == "right":
        p0, p1 = (o, o), (o + length, o)
        d.line([p0, (p1[0] - w * 0.5, p1[1])], fill=c, width=w)
        d.line([(p1[0] - head, p1[1] - head), p1, (p1[0] - head, p1[1] + head)], fill=c, width=w,
               joint="curve")
        img.paste(layer, (int(x - o), int(y - o)), layer)
    else:  # down
        p0, p1 = (o, o), (o, o + length)
        d.line([p0, (p1[0], p1[1] - w * 0.5)], fill=c, width=w)
        d.line([(p1[0] - head, p1[1] - head), p1, (p1[0] + head, p1[1] - head)], fill=c, width=w,
               joint="curve")
        img.paste(layer, (int(x - o), int(y - o)), layer)


def path_parts(text):
    return [p.strip() for p in str(text).split("→")]


def path_width(parts, fnt, size):
    arrow_w = size * 0.9
    return sum(text_size(p, fnt)[0] for p in parts) + (len(parts) - 1) * (arrow_w + size * 0.7)


def draw_path(img, xy, text, fnt, color, size, alpha=1.0, anchor="lm", arrow_color=None):
    """'A → B → C' 를 글자 화살표 대신 그린 화살표로."""
    parts = path_parts(text)
    total = path_width(parts, fnt, size)
    x, y = xy
    if anchor[0] == "r":
        x -= total
    elif anchor[0] == "m":
        x -= total / 2
    gap = size * 0.35
    for i, p in enumerate(parts):
        draw_text(img, (x, y), p, fnt, color, alpha, anchor="lm")
        x += text_size(p, fnt)[0]
        if i + 1 < len(parts):
            draw_arrow(img, (x + gap, y + size * 0.04), size * 0.9, arrow_color or color, size, alpha=alpha)
            x += size * 0.9 + gap * 2


def rounded_box(img, box, radius, fill, outline=None, width=2, alpha=1.0):
    if alpha <= 0.01:
        return
    radius = int(radius * _T.get("radius", 1.0))
    if outline is not None:
        width = max(1, int(width * _T.get("border", 1.0)))
    off = _T.get("offset_shadow", 0)
    if off and outline is not None:
        x0, y0, x1, y1 = box
        _box(img, (x0 + off, y0 + off, x1 + off, y1 + off), radius, _T.get("shadow_color", (0, 0, 0)),
             None, 0, alpha)
    _box(img, box, radius, fill, outline, width, alpha)


def _box(img, box, radius, fill, outline, width, alpha):
    x0, y0, x1, y1 = [int(v) for v in box]
    layer = Image.new("RGBA", (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    d.rounded_rectangle((0, 0, x1 - x0, y1 - y0), max(0, radius), fill=fill + (a,),
                        outline=(outline + (a,)) if outline else None, width=width)
    img.paste(layer, (x0, y0), layer)


def glow(img, center, radius, color, alpha=1.0):
    """부드러운 빛 번짐 효과."""
    alpha *= _T.get("glow", 1.0)
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


use("midnight")
