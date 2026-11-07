"""영상 스타일(테마). 대본의 `theme:` 또는 `--theme` 으로 고른다.

fonts: 역할 → (폰트 파일, ttc 번호, 크기 배율)
  serif_bold = 큰 단어와 제목, sans_bold = 이름표와 자막, sans = 본문, serif = 보조
"""
from pathlib import Path

_A = str(Path(__file__).resolve().parent.parent / "assets" / "fonts") + "/"
_NOTO = "/usr/share/fonts/opentype/noto/"
_NANUM = "/usr/share/fonts/truetype/nanum/"

NOTO = {
    "sans": (_NOTO + "NotoSansCJK-Regular.ttc", 1, 1.0),
    "sans_bold": (_NOTO + "NotoSansCJK-Bold.ttc", 1, 1.0),
    "serif": (_NOTO + "NotoSerifCJK-Regular.ttc", 1, 1.0),
    "serif_bold": (_NOTO + "NotoSerifCJK-Bold.ttc", 1, 1.0),
}

THEMES = {
    # 지금까지의 기본: 짙은 남색 + 호박색
    "midnight": {
        "label": "미드나잇 (지금 버전)",
        "colors": dict(BG_TOP=(14, 22, 38), BG_BOTTOM=(8, 12, 22), INK=(245, 240, 230),
                       MUTED=(150, 160, 180), ACCENT=(242, 181, 68), ACCENT2=(90, 200, 190),
                       RED=(230, 95, 80), LAND=(34, 48, 74), LAND_EDGE=(52, 70, 102),
                       LAND_HI=(120, 92, 44), CARD=(24, 34, 56), CARD_EDGE=(60, 78, 112),
                       ON_ACCENT=(8, 12, 22), SUB_BOX=(0, 0, 0), SUB_INK=(245, 240, 230),
                       GRID=(255, 255, 255)),
        "fonts": NOTO, "bg": "gradient", "sub_alpha": 0.55,
    },

    # 옛 사전과 고문서: 누런 종이, 먹색 글씨, 붉은 도장
    "dictionary": {
        "label": "고서·사전",
        "colors": dict(BG_TOP=(240, 230, 206), BG_BOTTOM=(228, 213, 181), INK=(43, 31, 23),
                       MUTED=(118, 100, 80), ACCENT=(168, 50, 42), ACCENT2=(46, 76, 109),
                       RED=(168, 50, 42), LAND=(218, 200, 160), LAND_EDGE=(160, 138, 100),
                       LAND_HI=(196, 158, 96), CARD=(246, 238, 220), CARD_EDGE=(120, 98, 72),
                       ON_ACCENT=(246, 238, 220), SUB_BOX=(43, 31, 23), SUB_INK=(246, 238, 220),
                       GRID=(80, 60, 40)),
        "fonts": {
            "sans": (_NANUM + "NanumMyeongjo.ttf", 0, 1.05),
            "sans_bold": (_NANUM + "NanumMyeongjoBold.ttf", 0, 1.05),
            "serif": (_A + "GowunBatang-Regular.ttf", 0, 1.0),
            "serif_bold": (_A + "SongMyung-Regular.ttf", 0, 1.08),
        },
        "tag_ink": (246, 238, 220), "bg": "paper", "radius": 0.15, "glow": 0.0, "text_shadow": False,
        "vignette": 90, "vignette_color": (150, 115, 70), "sub_alpha": 0.88,
    },

    # 잡지 편집 디자인: 흰 바탕, 굵은 검정 글씨, 빨강 한 색
    "magazine": {
        "label": "매거진",
        "colors": dict(BG_TOP=(247, 245, 240), BG_BOTTOM=(240, 237, 230), INK=(18, 18, 18),
                       MUTED=(110, 110, 110), ACCENT=(228, 52, 42), ACCENT2=(30, 79, 214),
                       RED=(228, 52, 42), LAND=(226, 223, 215), LAND_EDGE=(180, 175, 165),
                       LAND_HI=(246, 180, 170), CARD=(255, 255, 255), CARD_EDGE=(18, 18, 18),
                       ON_ACCENT=(255, 255, 255), SUB_BOX=(18, 18, 18), SUB_INK=(255, 255, 255),
                       GRID=(0, 0, 0)),
        "fonts": {
            "sans": (_A + "Pretendard-Regular.otf", 0, 1.0),
            "sans_bold": (_A + "Pretendard-Bold.otf", 0, 1.0),
            "serif": (_A + "Pretendard-Regular.otf", 0, 1.0),
            "serif_bold": (_A + "Pretendard-Black.otf", 0, 1.0),
        },
        "tag_ink": (255, 255, 255), "bg": "flat", "radius": 0.0, "border": 1.6, "glow": 0.0, "text_shadow": False,
        "vignette": 0, "sub_alpha": 1.0,
    },

    # 매거진 반전: 검정 바탕, 흰 글씨, 빨강 한 색
    "magazine_dark": {
        "label": "매거진 (반전)",
        "colors": dict(BG_TOP=(16, 16, 16), BG_BOTTOM=(12, 12, 12), INK=(245, 245, 242),
                       MUTED=(150, 150, 150), ACCENT=(240, 62, 50), ACCENT2=(90, 140, 255),
                       RED=(240, 62, 50), LAND=(40, 40, 40), LAND_EDGE=(80, 80, 80),
                       LAND_HI=(110, 40, 34), CARD=(22, 22, 22), CARD_EDGE=(245, 245, 242),
                       ON_ACCENT=(255, 255, 255), SUB_BOX=(245, 245, 242), SUB_INK=(16, 16, 16),
                       GRID=(255, 255, 255)),
        "fonts": {
            "sans": (_A + "Pretendard-Regular.otf", 0, 1.0),
            "sans_bold": (_A + "Pretendard-Bold.otf", 0, 1.0),
            "serif": (_A + "Pretendard-Regular.otf", 0, 1.0),
            "serif_bold": (_A + "Pretendard-Black.otf", 0, 1.0),
        },
        "tag_ink": (16, 16, 16), "bg": "flat", "radius": 0.0, "border": 1.6, "glow": 0.0,
        "text_shadow": False, "vignette": 0, "sub_alpha": 1.0,
    },

    # 팝: 노란 바탕, 굵은 검정 테두리, 딱딱한 그림자
    "pop": {
        "label": "팝·코믹",
        "colors": dict(BG_TOP=(255, 214, 64), BG_BOTTOM=(255, 200, 40), INK=(20, 20, 20),
                       MUTED=(70, 60, 30), ACCENT=(255, 84, 56), ACCENT2=(40, 104, 255),
                       RED=(230, 40, 40), LAND=(255, 250, 235), LAND_EDGE=(20, 20, 20),
                       LAND_HI=(255, 140, 110), CARD=(255, 255, 255), CARD_EDGE=(20, 20, 20),
                       ON_ACCENT=(255, 255, 255), SUB_BOX=(20, 20, 20), SUB_INK=(255, 255, 255),
                       GRID=(0, 0, 0)),
        "fonts": {
            "sans": (_A + "DoHyeon-Regular.ttf", 0, 1.08),
            "sans_bold": (_A + "DoHyeon-Regular.ttf", 0, 1.12),
            "serif": (_A + "DoHyeon-Regular.ttf", 0, 1.08),
            "serif_bold": (_A + "BlackHanSans-Regular.ttf", 0, 1.0),
        },
        "tag_ink": (255, 255, 255), "bg": "dots", "pattern": (240, 180, 20), "radius": 0.7, "border": 2.2,
        "offset_shadow": 10, "glow": 0.0, "text_shadow": False, "vignette": 0, "sub_alpha": 1.0,
    },

    # 칠판: 짙은 초록, 분필 손글씨
    "chalk": {
        "label": "칠판 수업",
        "colors": dict(BG_TOP=(40, 66, 58), BG_BOTTOM=(30, 52, 45), INK=(244, 241, 232),
                       MUTED=(185, 198, 188), ACCENT=(255, 224, 122), ACCENT2=(158, 216, 240),
                       RED=(255, 138, 128), LAND=(52, 86, 75), LAND_EDGE=(200, 214, 204),
                       LAND_HI=(110, 120, 70), CARD=(46, 76, 67), CARD_EDGE=(220, 229, 218),
                       ON_ACCENT=(30, 52, 45), SUB_BOX=(20, 36, 31), SUB_INK=(244, 241, 232),
                       GRID=(255, 255, 255)),
        "fonts": {
            "sans": (_A + "Gaegu-Regular.ttf", 0, 1.2),
            "sans_bold": (_A + "Gaegu-Bold.ttf", 0, 1.2),
            "serif": (_A + "Gaegu-Regular.ttf", 0, 1.2),
            "serif_bold": (_A + "Gaegu-Bold.ttf", 0, 1.25),
        },
        "tag_ink": (30, 52, 45), "bg": "chalk", "radius": 0.5, "glow": 0.35, "text_shadow": False,
        "vignette": 140, "vignette_color": (12, 22, 18), "sub_alpha": 0.7,
    },

    # 청사진·탐사 노트: 파란 모눈 바탕, 고정폭 글씨
    "blueprint": {
        "label": "청사진·탐사",
        "colors": dict(BG_TOP=(30, 78, 140), BG_BOTTOM=(24, 64, 118), INK=(243, 247, 255),
                       MUTED=(170, 196, 230), ACCENT=(255, 209, 102), ACCENT2=(127, 227, 208),
                       RED=(255, 120, 110), LAND=(44, 98, 168), LAND_EDGE=(207, 224, 255),
                       LAND_HI=(70, 130, 200), CARD=(34, 86, 152), CARD_EDGE=(207, 224, 255),
                       ON_ACCENT=(24, 64, 118), SUB_BOX=(14, 40, 78), SUB_INK=(243, 247, 255),
                       GRID=(255, 255, 255)),
        "fonts": {
            "sans": (_NOTO + "NotoSansCJK-Regular.ttc", 6, 0.95),
            "sans_bold": (_NOTO + "NotoSansCJK-Bold.ttc", 6, 0.95),
            "serif": (_NOTO + "NotoSansCJK-Regular.ttc", 6, 0.95),
            "serif_bold": (_NOTO + "NotoSansCJK-Bold.ttc", 6, 1.0),
        },
        "tag_ink": (24, 64, 118), "bg": "grid", "pattern": (255, 255, 255), "radius": 0.1, "glow": 0.25,
        "text_shadow": False, "vignette": 120, "vignette_color": (10, 30, 60), "sub_alpha": 0.85,
    },
}
