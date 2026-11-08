"""같은 문단을 여러 TTS 엔진·목소리로 읽혀 비교용 mp3를 만든다.

    python3 -m ytmaker.voice_sample                       # 1화 도입부로 kss, google, elevenlabs 비교
    python3 -m ytmaker.voice_sample --engines google --voices ko-KR-Chirp3-HD-Charon ko-KR-Chirp3-HD-Kore
"""
import argparse
import subprocess
from pathlib import Path

import numpy as np
import yaml

from . import build, tts

SCRIPT = Path(__file__).resolve().parent.parent / "episodes/001_portuguese_words/script.yaml"


def sample_text():
    ep = yaml.safe_load(SCRIPT.read_text())
    out = []
    for sc in ep["scenes"][:4]:                        # 도입부 + 빵 어원 카드
        for s in sc.get("say", []) or []:
            out.append(s if isinstance(s, str) else s["say"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=["kss", "google", "elevenlabs"])
    ap.add_argument("--voices", nargs="*", default=None, help="목소리 이름 (엔진이 하나일 때)")
    ap.add_argument("--out", default="output/voice_samples")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lines = sample_text()
    jobs = []
    for eng in args.engines:
        names = args.voices if (args.voices and len(args.engines) == 1) else [tts.DEFAULTS[eng]["name"]]
        jobs += [(eng, n) for n in names]
    for eng, name in jobs:
        try:
            tts.configure({"engine": eng, "name": name})
            gap = np.zeros(int(0.45 * tts.SAMPLE_RATE), np.float32)
            parts = []
            for line in lines:
                x, _ = tts.synthesize(line, 1.0)
                parts += [x, gap]
            wav = out / f"{eng}_{name}.wav"
            build.write_wav(wav, np.concatenate(parts), tts.SAMPLE_RATE)
            mp3 = wav.with_suffix(".mp3")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-b:a", "160k", str(mp3)], check=True)
            wav.unlink()
            print(f"완료: {mp3}")
        except SystemExit as e:
            print(f"실패: {eng} {name} → {e}")


if __name__ == "__main__":
    main()
