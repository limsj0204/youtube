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


def intro(sr, dur, timing):
    """인트로 장면 효과음. timing: 각 사건이 일어나는 시각(초)."""
    buf = np.zeros(int(dur * sr), np.float32)
    mix_at(buf, thud(sr), timing["land"], sr)
    mix_at(buf, thud(sr, 0.25) * 0.4, timing["land"] + 0.22, sr)  # 작게 한 번 더 튐
    mix_at(buf, rustle(sr), timing["open"], sr)
    for k, t in enumerate(timing["letters"]):
        mix_at(buf, pop(sr, 520 + k * 90), t, sr)
    mix_at(buf, chime(sr), timing["done"], sr)
    return np.clip(buf, -1, 1)
