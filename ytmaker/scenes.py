"""장면 종류별 그리기.

모든 장면은 `prepare(layout)` 로 무거운 준비(지도 등)를 한 번 하고,
`draw(img, c)` 로 매 프레임을 그린다. c 는 Clock (장면 안 시간 + 문장 타이밍).
"""
import math
import warnings

from PIL import Image, ImageDraw, ImageFilter

from . import assets as A
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


def bob(t, phase=0.0, amp=8.0):
    """그림이 살짝 떠다니는 움직임."""
    return math.sin(t * 1.6 + phase) * amp


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
        """장면 위쪽 제목 (d["icon"] 이 있으면 제목 왼쪽에 그림)."""
        if not text:
            return
        L = self.L
        x, y, w, _ = L.stage
        a = c.p(0, 0.6) if c.sents else appear(c.t, 0)
        f = font("sans_bold", 54 * L.s)
        draw_text(img, (L.cx, y + 40 * L.s), text, f, S.INK, a, dy=(1 - a) * 20)
        if self.d.get("icon"):
            tw = S.text_size(text, f)[0]
            A.place(img, self.d["icon"], (L.cx - tw / 2 - 60 * L.s, y + 36 * L.s + bob(c.t, 0, 3)),
                    80 * L.s, a)
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
        if d.get("icon"):
            k = c.p(d.get("icon_at", 0.4), 0.6)
            A.place(img, d["icon"], (L.cx + 310 * L.s, cy - 70 * L.s + bob(c.t, 0, 10 * L.s)),
                    240 * L.s * (0.7 + 0.3 * k), k, rotate=-10 * (1 - k))
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
        flags = d.get("flags", [])
        if flags:
            fw, gap = 96 * L.s, 90 * L.s
            total = fw * len(flags) + gap * (len(flags) - 1)
            fy = y + 190 * L.s
            dr = ImageDraw.Draw(img)
            for i, code in enumerate(flags):
                k = appear(c.t, 1.3 + i * 0.35, 0.5)
                fx = L.cx - total / 2 + fw / 2 + i * (fw + gap)
                A.place(img, "flag:" + code, (fx, fy + (1 - k) * 20), fw, k)
                k2 = appear(c.t, 1.5 + i * 0.35, 0.4)
                if i + 1 < len(flags) and k2 > 0:
                    S.draw_arrow(img, (fx + fw / 2 + 20 * L.s, fy), (gap - 40 * L.s) * k2, S.ACCENT, 50 * L.s)
        if d.get("ship"):
            p = c.t / max(1.0, c.dur)
            A.place(img, d["ship"], (lerp_(-150, L.W + 150, p), L.H - (420 if L.short else 150) * L.s
                                     + bob(c.t, 0, 5 * L.s)), 200 * L.s, 0.9)


def lerp_(a, b, x):
    return a + (b - a) * x


class Chapter(Scene):
    def draw(self, img, c):
        L, d = self.L, self.d
        a = appear(c.t, 0.05, 0.6)
        b = appear(c.t, 0.3, 0.7)
        num = f"{d.get('num', 1):02d}"
        if d.get("icon"):
            k = appear(c.t, 0.2, 0.7)
            A.place(img, d["icon"], (L.cx, L.cy - 290 * L.s + bob(c.t, 0, 8 * L.s) + (1 - k) * 30),
                    190 * L.s, k)
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
            badge = ("flag:" + step["flag"]) if step.get("flag") else step.get("badge")
            bw_ = 46 * L.s if badge else 0
            tw = S.text_size(lang, ft)[0] + 36 * L.s + (bw_ + 12 * L.s if badge else 0)
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
            shift = (bw_ + 12 * L.s) / 2 if badge else 0
            if badge:
                A.place(img, badge, (lx - tw / 2 + 18 * L.s + bw_ / 2, ly), bw_, a, shadow=False)
            draw_text(img, (lx + shift, ly), lang, ft, S.ON_ACCENT if cur else S.opt("tag_ink", S.INK), a)
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
                    p0 = (L.cx, by + bh + 14 * L.s)
                    S.draw_arrow(img, p0, max(1, (ny - by - bh - 28 * L.s) * k), S.ACCENT, 56 * L.s, "down")
                else:
                    p0 = (bx + bw + 16 * L.s, by + bh / 2 - off)
                    S.draw_arrow(img, p0, max(1, (nx - bx - bw - 32 * L.s) * k), S.ACCENT, 56 * L.s)
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
            ll = _smooth([tuple(v) for v in r["via"]])
            if not r.get("overland"):
                bad = geo.land_crossings(ll)
                if bad:
                    warnings.warn(f"항로 '{d.get('title', '')}'가 육지를 지납니다 "
                                  f"(경유점을 바다 쪽으로 옮기세요): {bad[:5]}")
            pts = [self.proj(lon, lat) for lon, lat in ll]
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
            if r.get("head") or p < 1:
                heads.append((path[-1], col, r.get("head")))
        for pos, col, head in heads:
            S.glow(img, pos, 60 * L.s, col, 0.9)
            if head:
                A.place(img, head, (pos[0], pos[1] - 34 * L.s + bob(c.t, 0, 3 * L.s)), 96 * L.s)
            else:
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
            iw = 44 * L.s if pin.get("icon") else 0
            lx, ly = x + dx, y + dy
            S.rounded_box(img, (lx - tw / 2 - iw / 2 - 16 * L.s - (6 * L.s if iw else 0),
                                ly - th / 2 - 14 * L.s,
                                lx + tw / 2 + iw / 2 + 16 * L.s + (6 * L.s if iw else 0),
                                ly + th / 2 + 14 * L.s),
                          int(12 * L.s), S.CARD, col, width=2, alpha=0.9 * a)
            if iw:
                A.place(img, pin["icon"], (lx - tw / 2 - 6 * L.s, ly), iw, a, shadow=False)
            draw_text(img, (lx + iw / 2 + (6 * L.s if iw else 0) / 2, ly), pin["name"], f, S.INK, a)
            if pin.get("caption"):
                draw_text(img, (lx, ly + th / 2 + 36 * L.s), pin["caption"],
                          font("sans", 30 * L.s), S.INK, a)
        if d.get("title"):
            f = font("sans_bold", 46 * L.s)
            a = appear(c.t, 0.1, 0.6)
            # 가운데 위: 지도 가장자리의 지명 핀을 가리지 않도록
            pos = (L.W / 2, 300 if L.short else 70)
            anchor = "mm"
            tw, th = S.text_size(d["title"], f)
            bx = pos[0] - (tw / 2 if anchor == "mm" else 0)
            S.rounded_box(img, (bx - 24, pos[1] - th / 2 - 18, bx + tw + 24, pos[1] + th / 2 + 18),
                          14, S.CARD, S.ACCENT, width=2, alpha=0.9 * a)
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
            if e.get("icon"):
                ip = (x0 + w - 90 * L.s, y) if L.short else (x, y - 190)
                A.place(img, e["icon"], (ip[0], ip[1] + bob(c.t, i, 5 * L.s) + (1 - a) * 20),
                        (110 if cur else 90) * L.s, a)
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
    """여러 설을 카드로 나란히 보여준다. 정설이 없으면 '정설 없음' 도장.

    cards:
      - label: 유력한 설
        head: 카스티야의 과자
        chain: [bolo de Castella, カステイラ, カステラ]   # 선택: 세로로 쌓고 화살표로 잇는다
        body: "옛 일본 문헌에 남은 이름과도\n이어진다"      # \n 으로 줄바꿈 위치 지정 가능
    """

    def _layout(self, card, bw):
        """카드 안 요소들의 위치와 전체 높이 계산."""
        L = self.L
        s = L.s
        pad = 44 * s
        items = []
        y = pad + 18 * s
        items.append(("label", y))
        y += 62 * s
        hs = 62 * s
        while hs > 24 and S.text_size(card["head"], font("serif_bold", hs))[0] > bw - pad * 2:
            hs -= 2
        items.append(("head", y, hs))
        y += hs * 0.5 + 34 * s
        items.append(("rule", y))
        y += 40 * s
        if card.get("chain"):
            fc = font("sans_bold", 36 * s)
            for k, word in enumerate(card["chain"]):
                y += 22 * s
                items.append(("chain", y, word, fc, k))
                y += 22 * s
                if k + 1 < len(card["chain"]):
                    items.append(("down", y + 8 * s))
                    y += 52 * s
            y += 30 * s
        fb = font("sans", 34 * s)
        for line in S.wrap(card.get("body", ""), fb, bw - pad * 2):
            y += 26 * s
            items.append(("body", y, line, fb))
            y += 26 * s
        return items, y + pad, pad

    def draw(self, img, c):
        L, d = self.L, self.d
        cards = d["cards"]
        n = len(cards)
        self.title(img, c, d.get("title"))
        x0, y0, w, h = L.stage
        top = y0 + 130 * L.s
        avail = y0 + h - 20 * L.s - top
        if L.short:
            gap = 36 * L.s
            bw = w
            lays = [self._layout(cd, bw) for cd in cards]
            total = sum(l[1] for l in lays) + gap * (n - 1)
            y = top + max(0, (avail - total) / 2)
            boxes = []
            for lay in lays:
                boxes.append((x0, y, bw, lay[1]))
                y += lay[1] + gap
        else:
            gap = 44
            bw = (w - gap * (n - 1)) / n
            lays = [self._layout(cd, bw) for cd in cards]
            ch = max(l[1] for l in lays)
            y = top + max(0, (avail - ch) / 2)
            boxes = [(x0 + i * (bw + gap), y, bw, ch) for i in range(n)]

        for i, (card, (bx, by, bw_, bh), (items, _, pad)) in enumerate(zip(cards, boxes, lays)):
            a = c.p(card.get("at", i), 0.5)
            if a <= 0:
                continue
            by += (1 - a) * 40 * L.s
            S.rounded_box(img, (bx, by, bx + bw_, by + bh), int(22 * L.s), S.CARD, S.CARD_EDGE,
                          width=3, alpha=a)
            lx = bx + pad
            for it in items:
                kind, yy = it[0], by + it[1]
                if kind == "label":
                    draw_text(img, (lx, yy), card["label"], font("sans_bold", 30 * L.s), S.ACCENT, a,
                              anchor="lm")
                elif kind == "head":
                    draw_text(img, (lx, yy), card["head"], font("serif_bold", it[2]), S.INK, a, anchor="lm")
                elif kind == "rule":
                    ImageDraw.Draw(img).line([(lx, yy), (bx + bw_ - pad, yy)],
                                             fill=S.mix(S.CARD, S.MUTED, 0.5 * a), width=max(1, int(2 * L.s)))
                elif kind == "chain":
                    last = it[4] == len(card["chain"]) - 1
                    draw_text(img, (lx, yy), it[2], it[3], S.INK if last else S.MUTED, a, anchor="lm")
                elif kind == "down":
                    S.draw_arrow(img, (lx + 18 * L.s, yy), 30 * L.s, S.ACCENT, 36 * L.s, "down", alpha=a)
                elif kind == "body":
                    draw_text(img, (lx, yy), it[2], it[3], S.MUTED, a, anchor="lm")
        st = d.get("stamp")
        if st:
            a = c.p(st.get("at", n), 0.35)
            if a > 0:
                scale = 1.6 - 0.6 * a
                f = font("serif_bold", 64 * L.s * scale)
                tw, th = S.text_size(st["text"], f)
                pad = 40 * L.s
                layer = Image.new("RGBA", (int(tw + pad * 2), int(th + pad * 2.2)), (0, 0, 0, 0))
                ld = ImageDraw.Draw(layer)
                ld.rounded_rectangle((6, 6, layer.width - 6, layer.height - 6),
                                     int(18 * L.s * S.opt("radius", 1.0)),
                                     outline=S.RED + (255,), width=int(9 * L.s * scale))
                S.draw_text(layer, (layer.width / 2, layer.height / 2), st["text"], f, S.RED)
                layer = layer.rotate(-8, expand=True, resample=Image.BICUBIC)
                layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a * 0.95)))
                bx0, by0 = boxes[0][0], boxes[0][1]
                # 제목 오른쪽에 (카드 내용과 자막을 가리지 않도록)
                tf = font("sans_bold", 54 * L.s)
                tw2 = S.text_size(d.get("title", ""), tf)[0]
                if L.short:
                    cx, cy = L.cx, boxes[-1][1] + boxes[-1][3] + 70 * L.s
                else:
                    cx, cy = L.cx + tw2 / 2 + 60 * L.s + layer.width / 2, y0 + 40 * L.s
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
            wx = bx0 + 50 * L.s + off
            if row.get("icon"):
                A.place(img, row["icon"], (wx + 40 * L.s, y), 90 * L.s, a)
                wx += 110 * L.s
            draw_text(img, (wx, y), row["word"], font("serif_bold", 64 * L.s),
                      S.ACCENT, a, anchor="lm")
            size = 38 * L.s
            parts = S.path_parts(row["path"])
            while S.path_width(parts, font("sans", size), size) > (bx1 - bx0) * 0.62 and size > 18:
                size -= 2
            S.draw_path(img, (bx1 - 50 * L.s + off, y), row["path"], font("sans", size), S.INK, size,
                        a, anchor="rm", arrow_color=S.ACCENT)


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
            draw_text(img, (L.cx, yb), d["next"], font("sans_bold", 46 * L.s), S.ON_ACCENT, a)


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
                  S.ON_ACCENT, b)


class Tableau(Scene):
    """그림 여러 장을 배치해 상황을 보여주는 장면 (아이콘 조합, 나중엔 AI 일러스트 한 장도 가능).

    layers:
      - img: custom:carrack      # 그림 이름 (assets.py 참고)
        x: 0.5                   # 무대 안 상대 위치 (0~1)
        y: 0.55
        size: 300                # 긴 변 픽셀 (가로 영상 기준)
        at: 0                    # 등장 문장 번호
        motion: slide            # pop(기본) | slide | float | zoom
        from: [-0.2, 0.55]       # slide 시작 위치
        until: 1                 # slide 가 끝나는 문장 번호 (기본: at 문장 끝)
        flip: false
        short: {x: 0.5, y: 0.3}  # 세로(쇼츠) 화면에서만 덮어쓸 값
    texts:
      - {text: 남만인, x: 0.5, y: 0.9, size: 56, at: 0, color: accent, font: serif_bold}
    """

    def draw(self, img, c):
        L, d = self.L, self.d
        self.title(img, c, d.get("title"))
        x0, y0, w, h = L.stage
        top = y0 + (120 * L.s if d.get("title") else 0)
        hh = y0 + h - top

        def pos(x, y):
            return x0 + w * x, top + hh * y

        for i, ly in enumerate(d.get("layers", [])):
            ly = {**ly, **(ly.get("short", {}) if L.short else {})}
            at = ly.get("at", 0)
            a = c.p(at, 0.6)
            if a <= 0:
                continue
            motion = ly.get("motion", "pop")
            x, y = pos(ly.get("x", 0.5), ly.get("y", 0.5))
            size = ly.get("size", 200) * L.s
            rot = 0.0
            if motion == "slide":
                fx, fy = pos(*ly.get("from", [-0.2, ly.get("y", 0.5)]))
                t0, t1 = c.at(at), c.end_of(ly.get("until", int(at)))
                k = S.ease_in_out((c.t - t0) / max(0.1, t1 - t0))
                x, y = fx + (x - fx) * k, fy + (y - fy) * k
                y += bob(c.t, i, 4 * L.s)
                a = min(1.0, a * 2)
            elif motion == "zoom":
                size *= 1.0 + 0.06 * S.clamp((c.t - c.at(at)) / max(1.0, c.dur))
            else:
                if motion == "float":
                    y += bob(c.t, i * 1.3, 9 * L.s)
                size *= 0.75 + 0.25 * a
                rot = ly.get("tilt", 0) * (1 - a)
            A.place(img, ly["img"], (x, y), size, a * ly.get("alpha", 1.0), flip=ly.get("flip", False),
                    rotate=rot)
        for tx in d.get("texts", []):
            tx = {**tx, **(tx.get("short", {}) if L.short else {})}
            a = c.p(tx.get("at", 0), 0.5)
            col = getattr(S, tx.get("color", "ink").upper())
            x, y = pos(tx.get("x", 0.5), tx.get("y", 0.9))
            draw_text(img, (x, y), tx["text"], font(tx.get("font", "sans_bold"), tx.get("size", 48) * L.s),
                      col, a, dy=(1 - a) * 20, shadow=True)


class Intro(Scene):
    """채널 인트로: 상자가 떨어져 튕기고, 흔들리다 열리면서 채널 이름 글자가 하나씩 튀어나온다.

    - type: intro
      name: 단어언박싱           # 글자마다 하나씩 튀어나옴
      accent_from: 2             # 이 글자부터 강조색 (단어 / 언박싱)
      tagline: 단어 속에 숨은 이야기를 꺼내 봅니다
      hold: 4.4
    """
    LAND, WIGGLE, OPEN, LETTER0, STEP = 0.55, 0.85, 1.2, 1.5, 0.16
    KRAFT, KRAFT_DARK, KRAFT_LIGHT = (196, 140, 86), (160, 110, 64), (214, 162, 106)

    @classmethod
    def timing(cls, n):
        letters = [cls.LETTER0 + k * cls.STEP for k in range(n)]
        return {"land": cls.LAND, "open": cls.OPEN, "letters": letters, "done": letters[-1] + 0.4}

    def prepare(self, L):
        super().prepare(L)
        self.chars = list(self.d.get("name", "단어언박싱"))
        f = font("serif_bold", 180 * L.s)
        widths = [S.text_size(ch, f)[0] for ch in self.chars]
        gap = 8 * L.s
        total = sum(widths) + gap * (len(widths) - 1)
        x = L.cx - total / 2
        self.targets = []
        for w in widths:
            self.targets.append(x + w / 2)
            x += w + gap

    def _box(self, open_k, s):
        """상자 그림 (RGBA). 아래 가운데가 기준점."""
        bw, bh, th = 520 * s, 350 * s, 32 * s
        W, H = int(bw * 2.6), int(bh * 3.2)
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        bx0, by1 = (W - bw) / 2, H - 10
        by0 = by1 - bh
        # 몸통 + 오른쪽 그늘 + 테이프 + 라벨
        d.rectangle((bx0, by0, bx0 + bw, by1), fill=self.KRAFT)
        d.rectangle((bx0 + bw * 0.82, by0, bx0 + bw, by1), fill=self.KRAFT_DARK)
        d.rectangle((bx0 + bw * 0.44, by0, bx0 + bw * 0.56, by0 + bh * 0.42), fill=S.mix(self.KRAFT, (255, 255, 255), 0.35))
        lx0, ly0 = bx0 + bw * 0.2, by0 + bh * 0.52
        d.rounded_rectangle((lx0, ly0, lx0 + bw * 0.5, ly0 + bh * 0.3), int(8 * s), fill=(245, 242, 235))
        f = font("sans_bold", 40 * s)
        d.text((lx0 + bw * 0.25, ly0 + bh * 0.15), "FRAGILE", font=f, fill=S.ACCENT, anchor="mm")
        # 날개: 왼쪽은 왼쪽 모서리, 오른쪽은 오른쪽 모서리를 축으로 열린다
        ang = math.radians(150 * open_k)
        for side in (-1, 1):
            hx = bx0 if side < 0 else bx0 + bw
            length = bw / 2
            a = ang if side < 0 else -ang
            dirx, diry = (-side) * math.cos(a), -abs(math.sin(a))
            nx, ny = -diry, dirx
            p1 = (hx, by0)
            p2 = (hx + dirx * length, by0 + diry * length)
            pts = [p1, p2, (p2[0] + nx * th * side * -1, p2[1] + ny * th * side * -1),
                   (p1[0] + nx * th * side * -1, p1[1] + ny * th * side * -1)]
            d.polygon(pts, fill=self.KRAFT_LIGHT if open_k > 0.02 else self.KRAFT, outline=self.KRAFT_DARK)
        return im, (W / 2, H - 10), by0 - (H - 10)

    def draw(self, img, c):
        L, d, s, t = self.L, self.d, self.L.s, c.t
        floor = L.cy + 330 * s
        # 떨어지기 → 튕기기
        if t < self.LAND:
            k = (t / self.LAND) ** 2
            dy = -(L.H * 0.9) * (1 - k)
        elif t < self.LAND + 0.32:
            dy = -46 * s * math.sin(math.pi * (t - self.LAND) / 0.32)
        else:
            dy = 0
        # 흔들기
        rot = 0.0
        if self.WIGGLE <= t < self.OPEN:
            k = (t - self.WIGGLE) / (self.OPEN - self.WIGGLE)
            rot = 7 * math.sin(k * math.pi * 4) * (1 - k)
        # 열기 (살짝 넘쳤다 돌아오는 움직임)
        ok = 0.0
        if t >= self.OPEN:
            x = S.clamp((t - self.OPEN) / 0.35)
            c1 = 1.70158
            ok = 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2
        box, anchor, top_off = self._box(ok, s)
        if rot:
            box = box.rotate(rot, resample=Image.BICUBIC, center=anchor)
        mouth = (L.cx, floor + top_off)
        # 상자 안에서 새어 나오는 빛과 빛줄기
        if ok > 0:
            S.glow(img, mouth, 260 * s, S.ACCENT, 0.7 * min(1, ok))
            dr = ImageDraw.Draw(img)
            ray_k = S.clamp((t - self.OPEN) / 0.9)
            fade = 1 - S.clamp((t - self.OPEN - 0.6) / 0.8)
            if fade > 0:
                for i in range(11):
                    ang = math.radians(-170 + i * 16)
                    r0, r1 = 60 * s, (80 + 230 * ray_k) * s
                    col = S.mix(S.BG_TOP, S.ACCENT, fade)
                    dr.line([(mouth[0] + math.cos(ang) * r0, mouth[1] + math.sin(ang) * r0),
                             (mouth[0] + math.cos(ang) * r1, mouth[1] + math.sin(ang) * r1)],
                            fill=col, width=max(2, int(5 * s)))
        # 바닥 그림자 (떨어지는 동안엔 작고 흐리게)
        near = S.clamp(1 + dy / (L.H * 0.5))
        sw = 300 * s * (0.5 + 0.5 * near)
        sh_layer = Image.new("RGBA", (int(sw * 2 + 20), int(60 * s) + 20), (0, 0, 0, 0))
        ImageDraw.Draw(sh_layer).ellipse((10, 10, 10 + sw * 2, 10 + 40 * s), fill=(0, 0, 0, int(150 * near)))
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(10 * s))
        img.paste(sh_layer, (int(L.cx - sw - 10), int(floor - 20 * s - 10)), sh_layer)
        img.paste(box, (int(L.cx - anchor[0]), int(floor - anchor[1] + dy)), box)
        # 글자가 하나씩 튀어나와 제자리로
        ty = floor + top_off - 230 * s
        tim = self.timing(len(self.chars))
        acc_from = d.get("accent_from", 2)
        for k, (ch, tx) in enumerate(zip(self.chars, self.targets)):
            t0 = tim["letters"][k]
            if t < t0:
                continue
            x = S.clamp((t - t0) / 0.42)
            c1 = 1.70158
            e = 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2   # 살짝 넘쳤다 돌아옴
            px = mouth[0] + (tx - mouth[0]) * S.clamp(e, 0, 1.2)
            arc = -math.sin(math.pi * S.clamp(x)) * 70 * s
            py = mouth[1] + (ty - mouth[1]) * S.clamp(e, 0, 1.2) + arc
            size = 180 * s * (0.25 + 0.75 * S.clamp(e, 0, 1.15))
            col = S.ACCENT if k >= acc_from else S.INK
            draw_text(img, (px, py), ch, font("serif_bold", size), col, min(1, x * 3))
        if d.get("tagline"):
            a = appear(t, tim["done"], 0.5)
            draw_text(img, (L.cx, floor + 70 * s), d["tagline"], font("sans", 42 * s), S.MUTED, a,
                      dy=(1 - a) * 12)


TYPES = {
    "hook": Hook, "title": Title, "chapter": Chapter, "chain": Chain, "map": Map,
    "timeline": Timeline, "theories": Theories, "summary": Summary, "sources": Sources,
    "cta": Cta, "tableau": Tableau, "intro": Intro,
}
