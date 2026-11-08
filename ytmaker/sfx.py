"""간단한 효과음을 코드로 합성 (저작권 걱정 없음)."""
import numpy as np


def _env(n, attack, decay, sr):
    t = np.arange(n) / sr
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / max(decay, 1e-4))


def thud(sr, dur=0.35):
    """상자가 바닥에 떨어지는 '퉁'."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    freq = 110 * np.exp(-t * 6) + 45
    body = np.sin(2 * np.pi * np.cumsum(freq) / sr)
    noise = np.random.default_rng(1).normal(0, 1, n) * np.exp(-t * 40) * 0.25
    return (body * _env(n, 0.003, 0.09, sr) + noise) * 0.9


def rustle(sr, dur=0.35):
    """종이 상자 날개가 열리는 '사락'."""
    n = int(dur * sr)
    rng = np.random.default_rng(2)
    x = rng.normal(0, 1, n)
    # 간단한 고역 통과 (차분) 후 진폭 흔들기
    x = np.diff(x, prepend=0)
    t = np.arange(n) / sr
    flutter = 0.6 + 0.4 * np.sin(2 * np.pi * 23 * t)
    return x * flutter * _env(n, 0.03, 0.12, sr) * 0.18


def pop(sr, pitch=600.0, dur=0.16):
    """글자가 튀어나오는 '뽁'."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    freq = pitch * (1 + 1.2 * np.exp(-t * 40))
    s = np.sin(2 * np.pi * np.cumsum(freq) / sr)
    return s * _env(n, 0.002, 0.04, sr) * 0.45


def chime(sr, dur=1.2):
    """마지막에 은은한 '띵'."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    s = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((880, 1.0), (1320, 0.5), (1760, 0.25)))
    return s * _env(n, 0.005, 0.35, sr) * 0.18


def mix_at(buf, clip, t, sr):
    i = int(t * sr)
    j = min(len(buf), i + len(clip))
    if i < len(buf):
        buf[i:j] += clip[: j - i]


def _smooth(x, n):
    """이동 평균 (간단한 저역 통과)."""
    k = np.ones(n) / n
    return np.convolve(x, k, mode="same")


def cut(sr, dur):
    """커터칼로 테이프를 긋는 부드러운 '스윽'.
    날카로운 고음(치익)과 낮은 웅웅거림을 걸러내고 가운데 대역만 남긴다."""
    n = int(dur * sr)
    rng = np.random.default_rng(3)
    x = rng.normal(0, 1, n)
    band = _smooth(x, 7) - _smooth(x, 40)            # 약 550Hz ~ 3kHz 만 남김
    texture = 0.8 + 0.2 * _smooth(rng.normal(0, 1, n), int(sr * 0.03)) * 8   # 아주 느린 결
    t = np.arange(n) / sr
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5                     # 부드럽게 커졌다 작아짐
    y = band * np.clip(texture, 0.5, 1.1) * env
    return y / (np.abs(y).max() + 1e-9) * 0.3


def whoosh(sr, dur):
    """줌인할 때 점점 커지는 바람 소리."""
    n = int(dur * sr)
    rng = np.random.default_rng(4)
    x = rng.normal(0, 1, n)
    k = np.exp(-1 / (sr * 0.002))                                   # 저역 통과로 부드럽게
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc = acc * k + x[i] * (1 - k)
        y[i] = acc
    t = np.arange(n) / sr
    env = (t / dur) ** 2 * np.clip((dur - t) / 0.06, 0, 1)
    return y / (np.abs(y).max() + 1e-9) * env * 0.5


def thump(sr, dur=0.22):
    """종이 상자 날개가 '툭' 열리는 낮고 부드러운 소리."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    freq = 140 * np.exp(-t * 9) + 70
    body = np.sin(2 * np.pi * np.cumsum(freq) / sr)
    rng = np.random.default_rng(5)
    paper = _smooth(rng.normal(0, 1, n), 12) * np.exp(-t * 60) * 0.6
    y = (body * 0.8 + paper) * _env(n, 0.004, 0.05, sr)
    return y / (np.abs(y).max() + 1e-9) * 0.35


def soft_chime(sr, dur=1.6):
    """은은한 '띵' (배음 적게, 천천히 사라짐)."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    s = np.sin(2 * np.pi * 784 * t) + 0.35 * np.sin(2 * np.pi * 1568 * t) * np.exp(-t * 4)
    return s * _env(n, 0.01, 0.5, sr) * 0.12


def intro(sr, dur, timing, style="full"):
    """인트로 장면 효과음.
    style: full(처음 버전) | clean(깔끔하게) | minimal(제목 '띵'만) | none(없음)"""
    buf = np.zeros(int(dur * sr), np.float32)
    c0, c1 = timing["cut"]
    if style == "full":
        # (칼로 긋는 '스윽' 소리는 넣지 않음)
        mix_at(buf, rustle(sr, 0.35), timing["open"], sr)
        if "open2" in timing:
            mix_at(buf, rustle(sr, 0.3) * 0.8, timing["open2"], sr)
        mix_at(buf, pop(sr, 700), timing["title"], sr)
    elif style == "clean":
        # (칼로 긋는 '스윽' 소리는 넣지 않음)
        mix_at(buf, thump(sr), timing["open"] + 0.05, sr)
        mix_at(buf, soft_chime(sr), timing["title"], sr)
    elif style == "minimal":
        mix_at(buf, soft_chime(sr), timing["title"], sr)
    return np.clip(buf, -1, 1)


def tick(sr, pitch=1200.0, dur=0.06):
    """부품이 놓이는 작은 '톡'."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    return np.sin(2 * np.pi * pitch * t) * _env(n, 0.001, 0.012, sr) * 0.12


def intro_dismantle(sr, dur, timing, n_parts=5):
    """단어해체소 인트로 효과음: 툭(떨어짐) → 스윽(절단) → 톡톡(부품) → 띵(제목)."""
    buf = np.zeros(int(dur * sr), np.float32)
    mix_at(buf, thump(sr) * 0.9, timing["drop"], sr)
    # (칼로 긋는 '스윽' 소리는 넣지 않음)
    mix_at(buf, thump(sr, 0.15) * 0.5, timing["split"], sr)
    for k in range(n_parts):
        mix_at(buf, tick(sr, 900 + k * 120), timing["parts"] - 0.2 + k * 0.05, sr)
    mix_at(buf, soft_chime(sr), timing["title"], sr)
    return np.clip(buf, -1, 1)
