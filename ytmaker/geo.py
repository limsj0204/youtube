"""세계 지도(Natural Earth, world-atlas TopoJSON) 읽기와 투영."""
import json
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

from . import style as S

TOPO = Path(__file__).resolve().parent.parent / "assets" / "countries-50m.json"


@lru_cache(maxsize=1)
def countries():
    """{나라 이름: [고리(경도,위도 목록), ...]}"""
    topo = json.loads(TOPO.read_text())
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(indices):
        out = []
        for i in indices:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        # 날짜변경선을 넘는 고리는 경도를 이어붙여 가로줄 생기는 걸 막는다
        for k in range(1, len(out)):
            lon, lat = out[k]
            while lon - out[k - 1][0] > 180:
                lon -= 360
            while lon - out[k - 1][0] < -180:
                lon += 360
            out[k] = (lon, lat)
        return out

    result = {}
    for g in topo["objects"]["countries"]["geometries"]:
        name = g.get("properties", {}).get("name", "")
        if g["type"] == "Polygon":
            polys = [g["arcs"]]
        elif g["type"] == "MultiPolygon":
            polys = g["arcs"]
        else:
            continue
        rings = [ring(r) for poly in polys for r in poly]
        result.setdefault(name, []).extend(rings)
    return result


class Projection:
    """정거원통 투영(중심 위도 보정)으로 view 영역을 box 안에 맞춘다."""

    def __init__(self, view, box, fit=False):
        self.lon0, self.lon1, self.lat0, self.lat1 = view
        bx, by, bw, bh = box
        k = math.cos(math.radians((self.lat0 + self.lat1) / 2))
        dw = (self.lon1 - self.lon0) * k
        dh = self.lat1 - self.lat0
        # fill: 상자를 꽉 채움(넘치는 부분은 잘림), fit: view 전체가 상자 안에 들어오게
        self.s = min(bw / dw, bh / dh) if fit else max(bw / dw, bh / dh)
        self.k = k
        self.cx = bx + bw / 2
        self.cy = by + bh / 2
        self.clon = (self.lon0 + self.lon1) / 2
        self.clat = (self.lat0 + self.lat1) / 2

    def __call__(self, lon, lat):
        return (self.cx + (lon - self.clon) * self.k * self.s,
                self.cy - (lat - self.clat) * self.s)


def base_map(size, proj, highlight=(), ss=2):
    """정적인 지도 바탕 이미지 (2배로 그린 뒤 줄여서 계단 현상 감소)."""
    w, h = size
    big = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    # 경위선
    for lon in range(-180, 181, 15):
        x, _ = proj(lon, 0)
        d.line([(x * ss, 0), (x * ss, h * ss)], fill=(255, 255, 255, 12), width=ss)
    for lat in range(-75, 76, 15):
        _, y = proj(0, lat)
        d.line([(0, y * ss), (w * ss, y * ss)], fill=(255, 255, 255, 12), width=ss)
    for name, rings in countries().items():
        if name == "Antarctica":
            continue
        fill = S.LAND_HI if name in highlight else S.LAND
        for r in rings:
            pts = [proj(lon, lat) for lon, lat in r]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if max(xs) < -50 or min(xs) > w + 50 or max(ys) < -50 or min(ys) > h + 50:
                continue
            d.polygon([(x * ss, y * ss) for x, y in pts], fill=fill + (255,),
                      outline=S.LAND_EDGE + (255,))
    return big.resize((w, h), Image.LANCZOS)
