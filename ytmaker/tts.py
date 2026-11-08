"""문장 → 음성. 엔진은 대본의 `voice:` 설정으로 고른다.

    voice:
      engine: google            # kss(무료, 비상업) | google | elevenlabs
      name: ko-KR-Chirp3-HD-Charon
      rate: 1.0
      comma_pause: true         # (google) 쉼표 자리에서 확실히 쉬기

대본에서 쉼표가 없는 곳에 쉬고 싶으면 `/` 를 적는다. 예: "그런데 이 빵이라는 말 / 원래는"

엔진별 API 키
  - google:     작업 환경의 네트워크 비밀값(헤더 X-Goog-Api-Key) 또는 환경 변수 GOOGLE_TTS_API_KEY
  - elevenlabs: 작업 환경의 네트워크 비밀값(헤더 xi-api-key) 또는 환경 변수 ELEVENLABS_API_KEY
키를 코드나 대본에 적지 말 것.
"""
import base64
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.request
import warnings
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "vits-mimic3-ko_KO-kss_low"
CACHE_DIR = ROOT / "output" / "cache" / "tts"
SAMPLE_RATE = 24000          # 모든 엔진의 결과를 이 샘플레이트로 맞춘다

DEFAULTS = {
    "kss": {"name": "kss"},
    "google": {"name": "ko-KR-Chirp3-HD-Charon", "comma_pause": True},
    "elevenlabs": {"name": "pNInz6obpgDQGcFmaJgB", "model": "eleven_multilingual_v2"},
}
VOICE = {"engine": "kss", **DEFAULTS["kss"]}

_kss = None


def configure(cfg=None):
    """대본의 voice 설정 적용."""
    global VOICE
    cfg = dict(cfg or {})
    engine = cfg.get("engine", "kss")
    if engine not in DEFAULTS:
        raise SystemExit(f"알 수 없는 TTS 엔진: {engine} (kss, google, elevenlabs 중 하나)")
    VOICE = {"engine": engine, **DEFAULTS[engine], **cfg}
    if engine == "kss":
        warnings.warn("KSS 음성은 비상업 라이선스입니다. 수익화 채널 업로드용으로 쓰지 마세요.")


def clean(text):
    """음성 엔진이 못 읽는 기호 정리. 숫자/로마자는 대본에서 한글로 적어 두는 게 원칙."""
    if re.search(r"[A-Za-z0-9]", text):
        warnings.warn(f"TTS 문장에 숫자나 로마자가 있습니다. 한글로 적어주세요: {text}")
    text = re.sub(r"[‘’“”'\"「」『』()\[\]]", "", text)
    if VOICE["engine"] == "kss":
        text = text.replace("?", ".").replace("!", ".")
    text = text.replace("·", ",").replace("…", ",")
    if VOICE["engine"] != "google":
        text = text.replace(" / ", ", ").replace("/", ", ")
    return re.sub(r"\s+", " ", text).strip()


def synthesize(text, speed=1.0):
    text = clean(text)
    sig = json.dumps(VOICE, sort_keys=True, ensure_ascii=False)
    key = hashlib.sha1(f"{sig}|{speed}|{SAMPLE_RATE}|{text}".encode()).hexdigest()[:16]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.npy"
    if path.exists():
        return np.load(path), SAMPLE_RATE
    engine = VOICE["engine"]
    if engine == "google":
        x, sr = _google(text, speed)
    elif engine == "elevenlabs":
        x, sr = _elevenlabs(text, speed)
    else:
        x, sr = _kss_tts(text, speed)
    x = _resample(np.asarray(x, dtype=np.float32), sr, SAMPLE_RATE)
    x = _trim(x, SAMPLE_RATE)
    np.save(path, x)
    return x, SAMPLE_RATE


# ---------------------------------------------------------------- 엔진들
def _kss_tts(text, speed):
    global _kss
    if _kss is None:
        import sherpa_onnx
        d = str(MODEL_DIR) + "/"
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=d + "ko_KO-kss_low.onnx", tokens=d + "tokens.txt",
                    data_dir=d + "espeak-ng-data", length_scale=1.0),
                num_threads=4))
        _kss = sherpa_onnx.OfflineTts(cfg)
    audio = _kss.generate(text, sid=0, speed=speed)
    return audio.samples, audio.sample_rate


def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"TTS 요청 실패 ({e.code}): {e.read()[:300].decode(errors='ignore')}")
    except urllib.error.URLError as e:
        raise SystemExit(f"{url.split('/')[2]} 에 연결할 수 없습니다 ({e.reason}). "
                         "작업 환경에 이 서비스의 API 키(네트워크 비밀값)가 등록됐는지 확인하세요.")


def _google(text, speed):
    # 키는 작업 환경의 네트워크 비밀값으로 프록시가 넣어 준다. 없으면 환경 변수를 쓴다.
    key = os.environ.get("GOOGLE_TTS_API_KEY", "set-by-proxy")
    # 쉼표와 / 자리에 쉼 표시를 넣는다 (Chirp 3 HD 의 markup 기능)
    if VOICE.get("comma_pause", True) and ("," in text or "/" in text):
        marked = re.sub(r"\s*/\s*", " [pause] ", text)
        marked = re.sub(r",\s*", ", [pause] ", marked)
        inp = {"markup": re.sub(r"(\[pause\]\s*)+", "[pause] ", marked).strip()}
    else:
        inp = {"text": text.replace("/", " ")}
    body = {
        "input": inp,
        "voice": {"languageCode": "ko-KR", "name": VOICE["name"]},
        "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": SAMPLE_RATE,
                        "speakingRate": float(VOICE.get("rate", 1.0)) * speed},
    }
    raw = _post("https://texttospeech.googleapis.com/v1/text:synthesize", body, {"X-Goog-Api-Key": key})
    wav = base64.b64decode(json.loads(raw)["audioContent"])
    with wave.open(io.BytesIO(wav)) as w:
        sr = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768, sr


def _elevenlabs(text, speed):
    key = os.environ.get("ELEVENLABS_API_KEY", "set-by-proxy")
    body = {
        "text": text,
        "model_id": VOICE.get("model", "eleven_multilingual_v2"),
        "voice_settings": {"stability": float(VOICE.get("stability", 0.5)),
                           "similarity_boost": float(VOICE.get("similarity", 0.75)),
                           "speed": float(VOICE.get("rate", 1.0)) * speed},
    }
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE['name']}?output_format=pcm_24000"
    raw = _post(url, body, {"xi-api-key": key})
    pcm = np.frombuffer(raw, dtype=np.int16)
    return pcm.astype(np.float32) / 32768, 24000


# ---------------------------------------------------------------- 도우미
def _resample(x, sr_in, sr_out):
    if sr_in == sr_out or len(x) == 0:
        return x
    n = int(round(len(x) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def _trim(x, sr, thresh=0.01):
    """앞뒤 무음 제거 (문장 간 간격은 빌드 단계에서 일정하게 넣는다)."""
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(0.03 * sr))
    b = min(len(x), idx[-1] + int(0.08 * sr))
    return x[a:b]
