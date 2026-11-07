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


def cut(sr, dur):
    """커터칼로 테이프를 긋는 '지익'."""
    n = int(dur * sr)
    rng = np.random.default_rng(3)
    x = np.diff(rng.normal(0, 1, n), prepend=0)
    t = np.arange(n) / sr
    grain = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 38 * t))     # 테이프 결을 긁는 느낌
    env = np.clip(t / 0.05, 0, 1) * np.clip((dur - t) / 0.08, 0, 1)
    return x * grain * env * 0.16


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


def intro(sr, dur, timing):
    """인트로 장면 효과음."""
    buf = np.zeros(int(dur * sr), np.float32)
    c0, c1 = timing["cut"]
    mix_at(buf, cut(sr, c1 - c0), c0, sr)
    mix_at(buf, rustle(sr, 0.4), timing["open"], sr)
    mix_at(buf, pop(sr, 700), timing["title"], sr)
    mix_at(buf, whoosh(sr, dur - timing["zoom"]), timing["zoom"], sr)
    return np.clip(buf, -1, 1)
