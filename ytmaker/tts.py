"""문장 → 음성. 기본은 무료 오프라인 한국어 음성(KSS VITS).

다른 TTS(일레븐랩스, 타입캐스트, 클로바 보이스 등)로 바꾸려면
`synthesize(text) -> (samples: np.float32 배열, sample_rate)` 를 같은 형태로 구현하면 된다.
"""
import hashlib
import re
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "vits-mimic3-ko_KO-kss_low"
CACHE_DIR = ROOT / "output" / "cache" / "tts"
SAMPLE_RATE = 22050

_tts = None


def _engine():
    global _tts
    if _tts is None:
        import sherpa_onnx
        d = str(MODEL_DIR) + "/"
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=d + "ko_KO-kss_low.onnx",
                    tokens=d + "tokens.txt",
                    data_dir=d + "espeak-ng-data",
                    length_scale=1.0,
                ),
                num_threads=4,
            )
        )
        _tts = sherpa_onnx.OfflineTts(cfg)
    return _tts


def clean(text):
    """음성 엔진이 못 읽는 기호 정리. 숫자/로마자는 대본에서 한글로 적어 두는 게 원칙."""
    if re.search(r"[A-Za-z0-9]", text):
        warnings.warn(f"TTS 문장에 숫자나 로마자가 있습니다. 한글로 적어주세요: {text}")
    text = re.sub(r"[‘’“”'\"「」『』()\[\]]", "", text)
    text = text.replace("?", ".").replace("!", ".").replace("·", ",").replace("…", ",")
    return text.strip()


def synthesize(text, speed=1.0):
    text = clean(text)
    key = hashlib.sha1(f"{MODEL_DIR.name}|{speed}|{text}".encode()).hexdigest()[:16]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.npy"
    if path.exists():
        return np.load(path), SAMPLE_RATE
    audio = _engine().generate(text, sid=0, speed=speed)
    samples = np.asarray(audio.samples, dtype=np.float32)
    samples = _trim(samples, audio.sample_rate)
    np.save(path, samples)
    return samples, audio.sample_rate


def _trim(x, sr, thresh=0.01):
    """앞뒤 무음 제거 (문장 간 간격은 빌드 단계에서 일정하게 넣는다)."""
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(0.03 * sr))
    b = min(len(x), idx[-1] + int(0.08 * sr))
    return x[a:b]
