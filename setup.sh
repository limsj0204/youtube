#!/usr/bin/env bash
# 영상 제작에 필요한 폰트, 파이썬 패키지, 무료 한국어 음성 모델을 설치합니다.
set -euo pipefail
cd "$(dirname "$0")"

if command -v apt-get >/dev/null; then
  sudo_cmd=""; [ "$(id -u)" -ne 0 ] && sudo_cmd="sudo"
  $sudo_cmd apt-get install -y -qq ffmpeg fonts-noto-cjk fonts-nanum libcairo2 >/dev/null
fi

pip install -q -r requirements.txt

MODEL=vits-mimic3-ko_KO-kss_low
if [ ! -d "models/$MODEL" ]; then
  mkdir -p models
  curl -sSL -o "models/$MODEL.tar.bz2" \
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/$MODEL.tar.bz2"
  tar xjf "models/$MODEL.tar.bz2" -C models
  rm "models/$MODEL.tar.bz2"
fi
echo "준비 완료"
