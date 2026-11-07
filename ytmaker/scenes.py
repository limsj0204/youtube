"""장면 종류별 그리기.

모든 장면은 `prepare(layout)` 로 무거운 준비(지도 등)를 한 번 하고,
`draw(img, c)` 로 매 프레임을 그린다. c 는 Clock (장면 안 시간 + 문장 타이밍).
"""
import math

from PIL import Image, ImageDraw

from . import geo
from . import style as S
from .style import appear, draw_text, font


class Layout:
    """화면 비율별 배치. long=1920x1080 가로, short=1080x1920 세로."""

    def __init__(self, short=False):
        self.short = short
        if short:
            self.W, self.H, self.s = 1080, 1920, 1.0
            self.stage = (60, 330, 960, 1060)      # x, y, w, h
            self.sub_y = 1560
        else:
            self.W, self.H, self.s = 1920, 1080, 1.0
            self.stage = (100, 70, 1720, 800)
            self.sub_y = 975

    @property
    def cx(self):
        x, _, w, _ = self.stage
        return x + w / 2

    @property
    def cy(self):
        _, y, _, h = self.stage
        return y + h / 2


class Clock:
    def __init__(self, t, dur, sents):
        self.t, self.dur, self.sents = t, dur, sents

    def at(self, x):
        """문장 번호(소수 가능) → 장면 안 시각. 0.5 = 0번 문장의 중간."""
        if not self.sents:
            return x
        i = int(math.floor(x))
        frac = x - i
        if i >= len(self.sents):
            return self.dur
        a, b = self.sents[i]
        return a + (b - a) * frac

    def end_of(self, i):
        if not self.sents:
            return self.dur
        return self.sents[min(i, len(self.sents) - 1)][1]

    def p(self, x, dur=0.5):
        return appear(self.t, self.at(x), dur)


def _default_reveal(n, sents):
    """reveal 지정이 없으면 문장 수에 맞춰 고르게 나눈다."""
    m = max(1, len(sents))
    return [min(m - 1, i * m / n) for i in range(n)]


class Scene:
    def __init__(self, data):
        self.d = data

    def prepare(self, L):
        self.L = L

    def draw(self, img, c):
        raise NotImplementedError

    def title(self, img, c, text):
        """장면 위쪽 제목."""
        if not text:
            return
        L = self.L
        x, y, w, _ = L.stage
        a = c.p(0, 0.6) if c.sents else appear(c.t, 0)
        f = font("sans_bold", 54 * L.s)
        draw_text(img, (L.cx, y + 40 * L.s), text, f, S.INK, a, dy=(1 - a) * 20)
        lw = S.text_size(text, f)[0] * a
        ImageDraw.Draw(img).line([(L.cx - lw / 2, y + 85 * L.s), (L.cx + lw / 2, y + 85 * L.s)],
                                 fill=S.ACCENT, width=max(2, int(4 * L.s)))


# ---------------------------------------------------------------- 장면들
class Hook(Scene):
    """큰 글자 하나로 시작하는 도입부."""

    def draw(self, img, c):
        L, d = self.L, self.d
        e = appear(c.t, 0.1, 0.9)
        size = 330 * L.s * (0.82 + 0.18 * e)
        cy = L.cy - 90 * L.s
        S.glow(img, (L.cx, cy), 330 * L.s, S.ACCENT, 0.35 * e)
        draw_text(img, (L.cx, cy), d["word"], font("serif_bold", size), S.INK, e, shadow=True)
        # 지워지는 후보들 (예: 한국어? 영어?)
        tags = d.get("strike", [])
        if tags:
            f = font("sans_bold", 64 * L.s)
            gap = 60 * L.s
            widths = [S.text_size(t, f)[0] for t in tags]
            total = sum(widths) + gap * (len(tags) - 1)
            x = L.cx - total / 2
            y = cy + 260 * L.s
            base = d.get("strike_at", 1)
            for i, (t, w) in enumerate(zip(tags, widths)):
                a = c.p(base + i * 0.35, 0.4)
                draw_text(img, (x + w / 2, y), t, f, S.MUTED, a)
                k = c.p(base + i * 0.35 + 0.3, 0.35)
                if k > 0:
                    ImageDraw.Draw(img).line([(x - 10, y), (x - 10 + (w + 20) * k, y)],
                                             fill=S.RED, width=int(7 * L.s))
                x += w + gap
        if d.get("reveal"):
            a = c.p(d.get("reveal_at", 2), 0.6)
            draw_text(img, (L.cx, cy + 380 * L.s), d["reveal"], font("serif_bold", 76 * L.s),
                      S.ACCENT, a, dy=(1 - a) * 30)


class Title(Scene):
    def draw(self, img, c):
        L, d = self.L, self.d
        a1 = appear(c.t, 0.1, 0.6)
        a2 = appear(c.t, 0.4, 0.8)
        a3 = appear(c.t, 0.9, 0.6)
        if d.get("kicker"):
            draw_text(img, (L.cx, L.cy - 170 * L.s), d["kicker"], font("sans_bold", 40 * L.s),
                      S.ACCENT, a1, dy=(1 - a1) * 15)
        lines = d["title"].split("\n")
        f = font("serif_bold", 120 * L.s)
        for i, line in enumerate(lines):
            draw_text(img, (L.cx, L.cy - 40 * L.s + i * 140 * L.s), line, f, S.INK, a2,
                      dy=(1 - a2) * 30, shadow=True)
        y = L.cy + 60 * L.s + (len(lines) - 1) * 140 * L.s
        w = 520 * L.s * a3
        ImageDraw.Draw(img).line([(L.cx - w / 2, y), (L.cx + w / 2, y)], fill=S.ACCENT,
                                 width=int(4 * L.s))
        if d.get("subtitle"):
            draw_text(img, (L.cx, y + 70 * L.s), d["subtitle"], font("sans", 46 * L.s),
                      S.MUTED, a3)


class Chapter(Scene):
    def draw(self, img, c):
        L, d = self.L, self.d
        a = appear(c.t, 0.05, 0.6)
        b = appear(c.t, 0.3, 0.7)
        num = f"{d.get('num', 1):02d}"
        draw_text(img, (L.cx, L.cy - 120 * L.s), num, font("serif_bold", 150 * L.s), S.ACCENT, a,
                  dy=(1 - a) * -30)
        draw_text(img, (L.cx, L.cy + 60 * L.s), d["title"], font("serif_bold", 120 * L.s), S.INK,
                  b, dy=(1 - b) * 30, shadow=True)
        if d.get("subtitle"):
            draw_text(img, (L.cx, L.cy + 190 * L.s), d["subtitle"], font("sans", 44 * L.s),
                      S.MUTED, appear(c.t, 0.6, 0.6))


class Chain(Scene):
    """어원 사슬: pão → パン → 빵 처럼 단어가 변해온 단계를 카드로 보여준다."""

    def draw(self, img, c):
        L, d = self.L, self.d
        steps = d["steps"]
        n = len(steps)
        reveal = d.get("reveal") or _default_reveal(n, c.sents)
        self.title(img, c, d.get("title"))
        x0, y0, w, h = L.stage
        top = y0 + 140 * L.s
        dr = ImageDraw.Draw(img)
        if L.short:
            gap = 70 * L.s
            ch = min(250 * L.s, (h - 160 * L.s - gap * (n - 1)) / n)
            cw = w * 0.9
            boxes = [(L.cx - cw / 2, top + i * (ch + gap), cw, ch) for i in range(n)]
        else:
            gap = 90 * L.s
            cw = min(380 * L.s, (w - gap * (n - 1)) / n)
            ch = 360 * L.s
            total = cw * n + gap * (n - 1)
            cy = top + (h - 140 * L.s) / 2 - ch / 2
            boxes = [(L.cx - total / 2 + i * (cw + gap), cy, cw, ch) for i in range(n)]

        shown = [c.p(r, 0.55) for r in reveal]
        latest = max([i for i, a in enumerate(shown) if a > 0], default=-1)
        for i, (step, (bx, by, bw, bh), a) in enumerate(zip(steps, boxes, shown)):
            if a <= 0:
                continue
            off = (1 - a) * 40 * L.s
            if L.short:
                bx += off
            else:
                by += off
            cur = i == latest
            S.rounded_box(img, (bx, by, bx + bw, by + bh), int(22 * L.s), S.CARD,
                          S.ACCENT if cur else S.CARD_EDGE, width=max(2, int(4 * L.s)), alpha=a)
            # 언어 표시
            ft = font("sans_bold", 32 * L.s)
            lang = step.get("lang", "")
            tw = S.text_size(lang, ft)[0] + 36 * L.s
            if L.short:
                lx, ly = bx + 40 * L.s + tw / 2, by + bh / 2
                wx = bx + 40 * L.s + tw + (bw - 40 * L.s - tw) / 2
                wy, ry = by + bh / 2 - 22 * L.s, by + bh / 2 + 62 * L.s
                max_word_w = bw - tw - 120 * L.s
            else:
                lx, ly = bx + bw / 2, by + 50 * L.s
                wx, wy, ry = bx + bw / 2, by + bh / 2 + 5 * L.s, by + bh - 55 * L.s
                max_word_w = bw - 50 * L.s
            tag_col = S.ACCENT if cur else S.CARD_EDGE
            S.rounded_box(img, (lx - tw / 2, ly - 26 * L.s, lx + tw / 2, ly + 26 * L.s),
                          int(26 * L.s), tag_col, alpha=a)
            draw_text(img, (lx, ly), lang, ft, S.BG_BOTTOM if cur else S.INK, a)
            # 단어 (카드 폭에 맞게 크기 자동 조절)
            size = 120 * L.s
            while size > 30 and S.text_size(step["word"], font("serif_bold", size))[0] > max_word_w:
                size -= 4
            draw_text(img, (wx, wy), step["word"], font("serif_bold", size), S.INK, a)
            if step.get("reading"):
                draw_text(img, (wx, ry), step["reading"], font("sans", 34 * L.s), S.MUTED, a)
            # 다음 카드로 가는 화살표
            if i + 1 < n and shown[i + 1] > 0:
                k = S.ease_out(shown[i + 1])
                nx, ny, nw, nh = boxes[i + 1]
                if L.short:
                    p0 = (L.cx, by + bh + 10 * L.s)
                    p1 = (L.cx, p0[1] + (ny - by - bh - 20 * L.s) * k)
                else:
                    p0 = (bx + bw + 12 * L.s, by + bh / 2 - off)
                    p1 = (p0[0] + (nx - bx - bw - 24 * L.s) * k, p0[1])
                S.arrow(dr, p0, p1, S.ACCENT, max(3, int(6 * L.s)), head=int(22 * L.s))
        if d.get("note"):
            a = c.p(d.get("note_at", len(c.sents) - 1), 0.6)
            y = (boxes[-1][1] + boxes[-1][3] + 70 * L.s) if L.short else (boxes[0][1] + ch + 80 * L.s)
            draw_text(img, (L.cx, y), d["note"], font("sans", 38 * L.s), S.MUTED, a)


class Map(Scene):
    """지도 위 항로/전파 경로 애니메이션."""

    def prepare(self, L):
        super().prepare(L)
        d = self.d
        view = d.get("view_short", d["view"]) if L.short else d["view"]
        box = (0, 280, L.W, 1180) if L.short else (0, 0, L.W, L.H)
        self.proj = geo.Projection(view, box, fit=L.short)
        self.base = geo.base_map((L.W, L.H), self.proj, set(d.get("highlight", [])))
        # 아래쪽 자막 영역을 살짝 어둡게
        shade = Image.linear_gradient("L").resize((L.W, L.H)).point(
            lambda v: int(max(0, v - 150) * 1.6))
        self.base.paste(Image.new("RGBA", (L.W, L.H), S.BG_BOTTOM + (255,)), (0, 0), shade)
        self.routes = []
        for r in d.get("routes", []):
            pts = [self.proj(lon, lat) for lon, lat in r["via"]]
            pts = _smooth(pts)
            seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
            self.routes.append((r, pts, seg, sum(seg)))

    def draw(self, img, c):
        L, d = self.L, self.d
        img.paste(self.base, (0, 0), self.base)
        dr = ImageDraw.Draw(img)
        heads = []
        for r, pts, seg, total in self.routes:
            t0 = c.at(r.get("start", 0))
            t1 = c.end_of(r.get("end", r.get("start", 0)))
            p = S.ease_in_out((c.t - t0) / max(0.1, t1 - t0))
            if p <= 0:
                continue
            col = tuple(r.get("color", S.ACCENT)) if not isinstance(r.get("color"), str) \
                else getattr(S, r["color"].upper())
            width = max(3, int(7 * L.s))
            path = _partial(pts, seg, total * p)
            if r.get("dashed"):
                _dashed(dr, path, col, width, 26 * L.s, 16 * L.s)
            else:
                dr.line(path, fill=col, width=width, joint="curve")
            if p < 1:
                heads.append((path[-1], col))
        for pos, col in heads:
            S.glow(img, pos, 60 * L.s, col, 0.9)
            r = 10 * L.s
            dr.ellipse((pos[0] - r, pos[1] - r, pos[0] + r, pos[1] + r), fill=S.INK)
        # 지명 핀
        for pin in d.get("pins", []):
            a = c.p(pin.get("at", 0), 0.4)
            if a <= 0:
                continue
            x, y = self.proj(pin["lon"], pin["lat"])
            col = getattr(S, pin.get("color", "accent").upper())
            r = 11 * L.s * (0.6 + 0.4 * a)
            dr.ellipse((x - r, y - r, x + r, y + r), fill=col, outline=S.INK, width=max(2, int(3 * L.s)))
            dx, dy = pin.get("dx", 0) * L.s, pin.get("dy", -50) * L.s
            f = font("sans_bold", pin.get("size", 40) * L.s)
            tw, th = S.text_size(pin["name"], f)
            lx, ly = x + dx, y + dy
            S.rounded_box(img, (lx - tw / 2 - 16 * L.s, ly - th / 2 - 14 * L.s,
                                lx + tw / 2 + 16 * L.s, ly + th / 2 + 14 * L.s),
                          int(12 * L.s), S.BG_BOTTOM, col, width=2, alpha=0.85 * a)
            draw_text(img, (lx, ly), pin["name"], f, S.INK, a)
            if pin.get("caption"):
                draw_text(img, (lx, ly + th / 2 + 36 * L.s), pin["caption"],
                          font("sans", 30 * L.s), S.INK, a)
        if d.get("title"):
            f = font("sans_bold", 46 * L.s)
            a = appear(c.t, 0.1, 0.6)
            if L.short:
                pos = (L.W / 2, 300)
                anchor = "mm"
            else:
                pos = (80, 70)
                anchor = "lm"
            tw, th = S.text_size(d["title"], f)
            bx = pos[0] - (tw / 2 if anchor == "mm" else 0)
            S.rounded_box(img, (bx - 24, pos[1] - th / 2 - 18, bx + tw + 24, pos[1] + th / 2 + 18),
                          14, S.BG_BOTTOM, S.ACCENT, width=2, alpha=0.85 * a)
            draw_text(img, pos, d["title"], f, S.INK, a, anchor=anchor)


def _smooth(pts, n=12):
    """캣멀-롬 스플라인으로 경유점을 부드러운 곡선으로."""
    if len(pts) < 3:
        return pts
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t
                                    + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                             for j in range(2)))
    out.append(pts[-1])
    return out


def _partial(pts, seg, length):
    out = [pts[0]]
    acc = 0
    for i, s in enumerate(seg):
        if acc + s >= length:
            k = (length - acc) / s if s else 0
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k,
                        pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k))
            return out
        acc += s
        out.append(pts[i + 1])
    return out


def _dashed(dr, path, col, width, on, off):
    pos, draw_on, left = 0, True, on
    for a, b in zip(path, path[1:]):
        seg = math.dist(a, b)
        start = 0
        while start < seg:
            step = min(left, seg - start)
            if draw_on:
                k0, k1 = start / seg, (start + step) / seg
                dr.line([(a[0] + (b[0] - a[0]) * k0, a[1] + (b[1] - a[1]) * k0),
                         (a[0] + (b[0] - a[0]) * k1, a[1] + (b[1] - a[1]) * k1)],
                        fill=col, width=width)
            start += step
            left -= step
            if left <= 0:
                draw_on = not draw_on
                left = on if draw_on else off
        pos += seg


class Timeline(Scene):
    def draw(self, img, c):
        L, d = self.L, self.d
        ev = d["events"]
        n = len(ev)
        reveal = [e.get("at") for e in ev]
        if None in reveal:
            reveal = _default_reveal(n, c.sents)
        self.title(img, c, d.get("title"))
        x0, y0, w, h = L.stage
        dr = ImageDraw.Draw(img)
        line_a = appear(c.t, 0.1, 0.8)
        shown = [c.p(r, 0.5) for r in reveal]
        latest = max([i for i, a in enumerate(shown) if a > 0], default=-1)
        if L.short:
            lx = x0 + 170 * L.s
            ya, yb = y0 + 190 * L.s, y0 + h - 40 * L.s
            dr.line([(lx, ya), (lx, ya + (yb - ya) * line_a)], fill=S.CARD_EDGE, width=int(6 * L.s))
            pos = [(lx, ya + (yb - ya) * (i + 0.5) / n) for i in range(n)]
        else:
            ly = y0 + h * 0.52
            xa, xb = x0 + 60, x0 + w - 60
            dr.line([(xa, ly), (xa + (xb - xa) * line_a, ly)], fill=S.CARD_EDGE, width=6)
            pos = [(xa + (xb - xa) * (i + 0.5) / n, ly) for i in range(n)]
        for i, (e, (x, y), a) in enumerate(zip(ev, pos, shown)):
            if a <= 0:
                continue
            cur = i == latest
            col = S.ACCENT if cur else S.MUTED
            r = 16 * L.s * (0.5 + 0.5 * a)
            if cur:
                S.glow(img, (x, y), 70 * L.s, S.ACCENT, 0.6 * a)
            dr.ellipse((x - r, y - r, x + r, y + r), fill=col)
            fy = font("serif_bold", 64 * L.s)
            fl = font("sans", 34 * L.s)
            if L.short:
                draw_text(img, (x + 50 * L.s, y - 30 * L.s), e["year"], fy, col, a, anchor="lm")
                for k, line in enumerate(S.wrap(e["label"], fl, w - 260 * L.s)):
                    draw_text(img, (x + 50 * L.s, y + 30 * L.s + k * 46 * L.s), line, fl, S.INK, a,
                              anchor="lm")
            else:
                draw_text(img, (x, y - 80), e["year"], fy, col, a, dy=(1 - a) * -20)
                for k, line in enumerate(S.wrap(e["label"], fl, w / n - 30)):
                    draw_text(img, (x, y + 70 + k * 48), line, fl, S.INK, a, dy=(1 - a) * 20)


class Theories(Scene):
    """정설이 없을 때: 여러 설을 나란히 보여주고 '정설 없음' 도장을 찍는다."""

    def draw(self, img, c):
        L, d = self.L, self.d
        cards = d["cards"]
        n = len(cards)
        self.title(img, c, d.get("title"))
        x0, y0, w, h = L.stage
        top = y0 + 150 * L.s
        if L.short:
            gap = 40 * L.s
            ch = (h - 170 * L.s - gap * (n - 1)) / n
            boxes = [(x0, top + i * (ch + gap), w, ch) for i in range(n)]
        else:
            gap = 50
            cw = (w - gap * (n - 1)) / n
            boxes = [(x0 + i * (cw + gap), top, cw, h - 200) for i in range(n)]
        for i, (card, (bx, by, bw, bh)) in enumerate(zip(cards, boxes)):
            a = c.p(card.get("at", i), 0.5)
            if a <= 0:
                continue
            by += (1 - a) * 40 * L.s
            S.rounded_box(img, (bx, by, bx + bw, by + bh), int(22 * L.s), S.CARD, S.CARD_EDGE,
                          width=3, alpha=a)
            draw_text(img, (bx + 40 * L.s, by + 60 * L.s), card["label"], font("sans_bold", 32 * L.s),
                      S.ACCENT, a, anchor="lm")
            draw_text(img, (bx + 40 * L.s, by + 130 * L.s), card["head"],
                      font("serif_bold", 64 * L.s), S.INK, a, anchor="lm")
            fb = font("sans", 36 * L.s)
            for k, line in enumerate(S.wrap(card.get("body", ""), fb, bw - 80 * L.s)):
                draw_text(img, (bx + 40 * L.s, by + 210 * L.s + k * 52 * L.s), line, fb, S.MUTED, a,
                          anchor="lm")
        st = d.get("stamp")
        if st:
            a = c.p(st.get("at", n), 0.35)
            if a > 0:
                scale = 1.6 - 0.6 * a
                f = font("serif_bold", 96 * L.s * scale)
                tw, th = S.text_size(st["text"], f)
                pad = 40 * L.s
                layer = Image.new("RGBA", (int(tw + pad * 2), int(th + pad * 2.2)), (0, 0, 0, 0))
                ld = ImageDraw.Draw(layer)
                ld.rounded_rectangle((6, 6, layer.width - 6, layer.height - 6), int(18 * L.s),
                                     outline=S.RED + (255,), width=int(9 * L.s * scale))
                ld.text((layer.width / 2, layer.height / 2), st["text"], font=f,
                        fill=S.RED + (255,), anchor="mm")
                layer = layer.rotate(-8, expand=True, resample=Image.BICUBIC)
                layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a * 0.95)))
                cx, cy = L.cx, (boxes[-1][1] + boxes[-1][3] * 0.55) if L.short else top + (h - 200) * 0.72
                img.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)


class Summary(Scene):
    def draw(self, img, c):
        L, d = self.L, self.d
        rows = d["rows"]
        n = len(rows)
        reveal = [r.get("at") for r in rows]
        if None in reveal:
            reveal = _default_reveal(n, c.sents)
        self.title(img, c, d.get("title"))
        x0, y0, w, h = L.stage
        top = y0 + 170 * L.s
        rh = min(150 * L.s, (h - 200 * L.s) / n)
        for i, (row, r) in enumerate(zip(rows, reveal)):
            a = c.p(r, 0.5)
            if a <= 0:
                continue
            y = top + i * rh + rh / 2
            off = (1 - a) * -40 * L.s
            bx0 = x0 + (0 if L.short else 160)
            bx1 = x0 + w - (0 if L.short else 160)
            S.rounded_box(img, (bx0 + off, y - rh / 2 + 10 * L.s, bx1 + off, y + rh / 2 - 10 * L.s),
                          int(18 * L.s), S.CARD, S.CARD_EDGE, width=2, alpha=a)
            draw_text(img, (bx0 + 50 * L.s + off, y), row["word"], font("serif_bold", 64 * L.s),
                      S.ACCENT, a, anchor="lm")
            f = font("sans", 38 * L.s)
            path = row["path"]
            while S.text_size(path, f)[0] > (bx1 - bx0) * 0.62 and f.size > 18:
                f = font("sans", f.size - 2)
            draw_text(img, (bx1 - 50 * L.s + off, y), path, f, S.INK, a, anchor="rm")


class Sources(Scene):
    def draw(self, img, c):
        L, d = self.L, self.d
        self.title(img, c, d.get("title", "참고 자료"))
        x0, y0, w, h = L.stage
        f = font("sans", 34 * L.s)
        y = y0 + 170 * L.s
        for i, src in enumerate(d.get("sources", [])):
            a = appear(c.t, 0.3 + i * 0.12, 0.5)
            for line in S.wrap("· " + src, f, w - 200 * L.s):
                draw_text(img, (x0 + 100 * L.s, y), line, f, S.MUTED, a, anchor="lm")
                y += 50 * L.s
        if d.get("next"):
            a = c.p(d.get("next_at", max(0, len(c.sents) - 1)), 0.6)
            yb = y0 + h - 90 * L.s
            S.rounded_box(img, (L.cx - 620 * L.s, yb - 70 * L.s, L.cx + 620 * L.s, yb + 70 * L.s),
                          int(70 * L.s), S.ACCENT, alpha=a)
            draw_text(img, (L.cx, yb), d["next"], font("sans_bold", 46 * L.s), S.BG_BOTTOM, a)


class Cta(Scene):
    """쇼츠 마지막: 본편으로 유도."""

    def draw(self, img, c):
        L, d = self.L, self.d
        a = appear(c.t, 0.1, 0.6)
        draw_text(img, (L.cx, L.cy - 120 * L.s), d.get("small", ""), font("sans_bold", 50 * L.s),
                  S.MUTED, a)
        f = font("serif_bold", 96 * L.s)
        for i, line in enumerate(d["text"].split("\n")):
            draw_text(img, (L.cx, L.cy + i * 120 * L.s), line, f, S.INK, a, dy=(1 - a) * 30,
                      shadow=True)
        b = c.p(d.get("button_at", 0.4), 0.5)
        yb = L.cy + 330 * L.s
        S.rounded_box(img, (L.cx - 330 * L.s, yb - 70 * L.s, L.cx + 330 * L.s, yb + 70 * L.s),
                      int(70 * L.s), S.ACCENT, alpha=b)
        draw_text(img, (L.cx, yb), d.get("button", "본편 보러 가기"), font("sans_bold", 52 * L.s),
                  S.BG_BOTTOM, b)


TYPES = {
    "hook": Hook, "title": Title, "chapter": Chapter, "chain": Chain, "map": Map,
    "timeline": Timeline, "theories": Theories, "summary": Summary, "sources": Sources,
    "cta": Cta,
}
