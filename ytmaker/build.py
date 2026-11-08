"""대본(YAML) → 영상(mp4) + 썸네일 + 설명란 텍스트.

사용법:
    python -m ytmaker.build episodes/001_portuguese_words/script.yaml            # 롱폼
    python -m ytmaker.build episodes/001_portuguese_words/script.yaml --short    # 쇼츠
    python -m ytmaker.build ... --preview 12.5    # 해당 시점 한 프레임만 PNG로
"""
import argparse
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

from . import style as S
from . import tts
from .scenes import TYPES, Clock, Layout

FPS = 30
LEAD, GAP, TAIL = 0.6, 0.55, 1.1   # 장면 시작 여백, 문장 사이 간격, 장면 끝 여백(초)


def smart_quotes(t):
    """자막의 곧은 따옴표를 둥근 따옴표로 (화면 글자와 맞추기)."""
    t = re.sub(r"'([^']*)'", "\u2018\\1\u2019", t)
    return re.sub(r'"([^"]*)"', "\u201c\\1\u201d", t)


def sentences(scene):
    out = []
    for s in scene.get("say", []) or []:
        if isinstance(s, str):
            out.append({"say": s, "sub": smart_quotes(s)})
        else:
            out.append({"say": s["say"], "sub": smart_quotes(s.get("sub", s["say"]))})
    return out


def plan(scenes, speed):
    """음성을 만들고 장면별 길이와 문장 타이밍을 계산한다."""
    timeline, audio, t = [], [], 0.0
    sr = tts.SAMPLE_RATE
    flat = [s["say"] for sc in scenes for s in sentences(sc)]    # 앞뒤 문장 맥락용
    k = 0
    for sc in scenes:
        sents = sentences(sc)
        local, chunks, cur = [], [], LEAD
        chunks.append(np.zeros(int(LEAD * sr), np.float32))
        for i, s in enumerate(sents):
            prev = flat[k - 1] if k > 0 else ""
            nxt = flat[k + 1] if k + 1 < len(flat) else ""
            wav, _ = tts.synthesize(s["say"], speed, prev, nxt)
            k += 1
            dur = len(wav) / sr
            local.append((cur, cur + dur))
            chunks.append(wav)
            cur += dur
            if i < len(sents) - 1:
                chunks.append(np.zeros(int(GAP * sr), np.float32))
                cur += GAP
        hold = float(sc.get("hold", 0))
        total = max(cur + TAIL, hold) if sents else max(hold, 2.5)
        pad = int(round(total * sr)) - sum(len(c) for c in chunks)
        chunks.append(np.zeros(max(0, pad), np.float32))
        seg = np.concatenate(chunks)[: int(round(total * sr))]
        if sc["type"] in ("intro", "intro_dismantle", "intro_shatter", "outro"):
            from . import sfx
            from .scenes import Intro, IntroDismantle, IntroShatter, OutroAssemble, jamo
            if sc["type"] == "outro":
                fx = sfx.outro_assemble(sr, total, OutroAssemble.timing())
            elif sc["type"] == "intro_shatter":
                fx = sfx.intro_shatter(sr, total, IntroShatter.timing())
            elif sc["type"] == "intro":
                fx = sfx.intro(sr, total, Intro.timing(len(sc.get("name", "단어언박싱"))), sc.get("sfx", "full"))
            else:
                n_parts = sum(len(jamo(ch)) for ch in sc.get("word", "단어"))
                fx = sfx.intro_dismantle(sr, total, IntroDismantle.timing(), n_parts)
            fx = np.pad(fx, (0, max(0, len(seg) - len(fx))))[: len(seg)]
            seg = seg + 0.6 * fx
        audio.append(seg)
        timeline.append({"scene": sc, "start": t, "dur": total, "sents": local, "subs": sents})
        t += total
    return timeline, np.concatenate(audio), t


def subtitle(img, L, text, alpha):
    if not text or alpha <= 0.01:
        return
    f = S.font("sans_bold", 58 if L.short else 46)
    lines = S.wrap(text, f, 880 if L.short else 1500)
    lh = 80 if L.short else 64
    n = len(lines)
    top = L.sub_y - (n - 1) * lh / 2
    widest = max(S.text_size(line, f)[0] for line in lines)
    S.rounded_box(img, (L.W / 2 - widest / 2 - 34, top - lh / 2 - 12,
                        L.W / 2 + widest / 2 + 34, top + (n - 1) * lh + lh / 2 + 12),
                  int(18 * S.opt("radius", 1.0)) or 1, S.SUB_BOX, alpha=S.opt("sub_alpha", 0.55) * alpha)
    for i, line in enumerate(lines):
        S.draw_text(img, (L.W / 2, top + i * lh), line, f, S.SUB_INK, alpha)


def header(img, L, ep):
    """쇼츠 상단 고정 띠."""
    sh = ep.get("shorts", {})
    S.draw_text(img, (L.W / 2, 130), sh.get("kicker", ep.get("series", "")),
                S.font("sans_bold", 40), S.ACCENT)
    S.draw_text(img, (L.W / 2, 205), sh.get("header", ep["title"]), S.font("serif_bold", 64), S.INK)


def watermark(img, L, ep):
    S.draw_text(img, (L.W - 60, 50), ep.get("series", ""), S.font("sans_bold", 28), S.MUTED,
                0.7, anchor="rm")


def render_frame(t, timeline, L, ep, objs):
    bg = S.background(L.W, L.H)
    for k, item in enumerate(timeline):
        if item["start"] <= t < item["start"] + item["dur"] or k == len(timeline) - 1:
            break
    lt = t - item["start"]
    clock = Clock(lt, item["dur"], item["sents"])
    img = bg.copy()
    sc = item["scene"]
    objs[k].draw(img, clock)
    if L.short:
        header(img, L, ep)
    elif sc["type"] not in ("hook", "title", "intro", "intro_dismantle", "intro_shatter", "outro"):
        watermark(img, L, ep)
    # 장면 전환: 처음 0.25초 동안 배경에서 서서히 나타남
    if lt < 0.25 and k > 0:
        img = Image.blend(bg, img, S.ease_out(lt / 0.25))
    # 자막
    for i, (a, b) in enumerate(item["sents"]):
        if a - 0.05 <= lt < b + GAP * 0.8:
            al = min(S.clamp((lt - a + 0.05) / 0.12), S.clamp((b + GAP * 0.8 - lt) / 0.12))
            subtitle(img, L, item["subs"][i]["sub"], al)
            break
    # 마지막 0.5초 페이드아웃
    total = timeline[-1]["start"] + timeline[-1]["dur"]
    if t > total - 0.5:
        img = Image.blend(Image.new("RGB", img.size), img, S.clamp((total - t) / 0.5))
    return img


# 목소리 보정 프리셋 (대본의 voice_fx 로 선택)
VOICE_FX = {
    "none": "",
    # 날카로움 줄이기: 저음 채우기, 고음 깎기, 치찰음(ㅅ ㅆ ㅊ) 누르기
    "soft": "equalizer=f=200:t=q:w=1:g=3.5,equalizer=f=3000:t=q:w=1:g=-1.5,"
            "equalizer=f=6500:t=q:w=1:g=-5,deesser=i=0.5,lowpass=f=11000",
}


def voice_fx(ep):
    fx = VOICE_FX.get(ep.get("voice_fx", "none"), ep.get("voice_fx", ""))
    return (fx + "," if fx else "") + "loudnorm=I=-14:TP=-1.5:LRA=11"


def audio_args(ep, script_dir, total, voice_idx=1):
    """목소리 보정 + (있으면) 배경음악 섞기. 말할 때는 배경음악이 자동으로 작아진다(더킹)."""
    fx = VOICE_FX.get(ep.get("voice_fx", "none"), ep.get("voice_fx", ""))
    bgm = ep.get("bgm")
    if not bgm:
        return [], ["-af", voice_fx(ep)], [f"{voice_idx}:a"]
    path = Path(bgm["file"])
    if not path.is_absolute():
        path = script_dir / path
    vol = float(bgm.get("volume_db", -22))
    start = float(bgm.get("start", 0))
    fade_out = float(bgm.get("fade_out", 3))
    graph = (
        f"[{voice_idx}:a]{fx + ',' if fx else ''}asplit=2[v][key];"
        f"[{voice_idx + 1}:a]atrim=start={start},asetpts=PTS-STARTPTS,volume={vol}dB,"
        f"afade=t=in:d=1.5,atrim=0:{total:.2f},afade=t=out:st={max(0, total - fade_out):.2f}:d={fade_out}[b];"
        f"[b][key]sidechaincompress=threshold=0.02:ratio=5:attack=30:release=500[bd];"
        f"[v][bd]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    )
    return ["-stream_loop", "-1", "-i", str(path)], ["-filter_complex", graph], ["[a]"]


def write_wav(path, samples, sr):
    pcm = (np.clip(samples, -1, 1) * 32767 * 0.95).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def fmt_ts(sec):
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def description(ep, timeline):
    lines = [ep.get("description", "").strip(), "", "⏱ 챕터"]
    chapters = [(0.0, "인트로")]
    for item in timeline:
        if item["scene"].get("chapter"):
            chapters.append((item["start"], item["scene"]["chapter"]))
    lines += [f"{fmt_ts(t)} {name}" for t, name in chapters]
    lines += ["", "📚 참고 자료"] + [f"- {s}" for s in ep.get("sources", [])]
    if ep.get("credits"):
        lines += ["", "🎨 사용한 자료"] + [f"- {c}" for c in ep["credits"]]
    if ep.get("tags"):
        lines += ["", " ".join("#" + t for t in ep["tags"])]
    return "\n".join(lines) + "\n"


def thumbnail(ep, path):
    from . import geo
    th = ep.get("thumbnail", {})
    W, H = 1280, 720
    img = S.background(W, H).copy()
    if th.get("map_view"):
        proj = geo.Projection(th["map_view"], (0, 0, W, H))
        base = geo.base_map((W, H), proj, set(th.get("highlight", [])))
        base.putalpha(base.getchannel("A").point(lambda v: int(v * 0.55)))
        img.paste(base, (0, 0), base)
    # 왼쪽 큰 글자: 두 글자는 세로로 쌓고, 칸(560x620)에 맞게 크기 자동 조절
    big = th.get("big", "")
    S.glow(img, (330, 360), 330, S.ACCENT, 0.55)
    rows = list(big) if len(big) == 2 else [big]
    size = 420
    while size > 120:
        f = S.font("serif_bold", size)
        if max(S.text_size(r, f)[0] for r in rows) <= 560 and size * 0.95 * len(rows) <= 570:
            break
        size -= 10
    f = S.font("serif_bold", size)
    step = size * 0.95
    top = 360 - step * (len(rows) - 1) / 2
    for i, r in enumerate(rows):
        S.draw_text(img, (330, top + i * step), r, f, S.INK, shadow=True)
    # 오른쪽 글: 너비(600)에 맞게 자동 조절
    y = 250
    for i, line in enumerate(th.get("lines", [])):
        fs = 104 if i == 0 else 64
        while fs > 30 and S.text_size(line, S.font("serif_bold", fs))[0] > 600:
            fs -= 4
        col = S.ACCENT if i == 0 else S.INK
        S.draw_text(img, (640, y), line, S.font("serif_bold", fs), col, anchor="lm", shadow=True)
        y += 130 if i == 0 else 90
    if th.get("flags"):
        from . import assets as A
        fx = 640 + 60
        for i, code in enumerate(th["flags"]):
            A.place(img, "flag:" + code, (fx + i * 150, y + 30), 100)
            if i + 1 < len(th["flags"]):
                S.draw_arrow(img, (fx + i * 150 + 60, y + 30), 30, S.ACCENT, 46)
    if th.get("badge"):
        f = S.font("sans_bold", 36)
        tw, _ = S.text_size(th["badge"], f)
        S.rounded_box(img, (640, 90, 640 + tw + 50, 150), 30, S.RED)
        S.draw_text(img, (665, 120), th["badge"], f, S.INK, anchor="lm")
    img.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--short", action="store_true", help="세로 쇼츠 버전")
    ap.add_argument("--preview", type=float, nargs="*", help="이 시점들의 프레임만 PNG로 저장")
    ap.add_argument("--speed", type=float, default=None, help="말하기 속도 (기본: 대본의 speed, 없으면 0.95)")
    ap.add_argument("--out", default="output")
    ap.add_argument("--theme", help="영상 스타일 (기본: 대본의 theme, 없으면 midnight)")
    ap.add_argument("--voice", help="TTS 엔진만 바꿔서 만들기: kss | google | elevenlabs")
    ap.add_argument("--audio-only", action="store_true", help="화면은 그대로 두고 소리만 다시 입히기")
    args = ap.parse_args(argv)

    script = Path(args.script)
    ep = yaml.safe_load(script.read_text())
    S.use(args.theme or ep.get("theme", "midnight"))
    voice = dict(ep.get("voice") or {})
    if args.voice and args.voice != voice.get("engine"):
        voice = {"engine": args.voice}
    tts.configure(voice)
    if tts.VOICE["engine"] != "kss":
        tts.STORE_DIR = script.parent / "voice" / tts.VOICE["engine"]
    L = Layout(short=args.short)
    scenes = ep["shorts"]["scenes"] if args.short else ep["scenes"]
    name = script.parent.name + ("_short" if args.short else "")
    out = Path(args.out) / name
    out.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    speed = args.speed or ep.get("speed", 0.95)
    timeline, audio, total = plan(scenes, speed)
    print(f"음성 생성 완료: {len(scenes)}개 장면, 총 {total:.1f}초 ({time.time() - t0:.1f}s)")
    u = tts.USAGE
    print(f"음성 요청: 새로 만든 문장 {u['requests']}개 (사용 크레딧 {u['credits']}), "
          f"저장된 음성 재사용 {u['cached']}개")
    objs = []
    for item in timeline:
        obj = TYPES[item["scene"]["type"]](item["scene"])
        obj.prepare(L)
        objs.append(obj)

    if args.preview is not None:
        times = args.preview or [item["start"] + item["dur"] * 0.8 for item in timeline]
        for i, t in enumerate(times):
            p = out / f"preview_{i:02d}_{t:06.1f}s.png"
            render_frame(t, timeline, L, ep, objs).save(p)
            print(p)
        return

    wav = out / "voice.wav"
    write_wav(wav, audio, tts.SAMPLE_RATE)
    mp4 = out / f"{name}.mp4"
    extra_in, afilter, amap = audio_args(ep, script.parent, total)
    aout = ["-map", "0:v", "-map", amap[0], *afilter,
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart"]

    if args.audio_only:
        # 화면은 그대로 두고 소리만 다시 입힌다 (배경음악·목소리 보정 바꿀 때)
        if not mp4.exists():
            sys.exit("먼저 영상을 한 번 만들어야 합니다.")
        tmp = out / "tmp_audio.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-i", str(wav), *extra_in,
                        *aout[:2], "-c:v", "copy", *aout[2:], str(tmp)], check=True)
        tmp.replace(mp4)
        print(f"소리만 교체: {mp4}")
        if not args.short:
            (out / "description.txt").write_text(description(ep, timeline))
        return

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L.W}x{L.H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav), *extra_in,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           *aout, str(mp4)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(total * FPS)
    for f in range(n):
        frame = render_frame(f / FPS, timeline, L, ep, objs)
        proc.stdin.write(frame.tobytes())
        if f % (FPS * 10) == 0:
            print(f"  렌더링 {f / FPS:5.0f}s / {total:.0f}s", file=sys.stderr, flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg 실패")
    print(f"영상: {mp4} ({time.time() - t0:.0f}s 소요)")

    if not args.short:
        (out / "description.txt").write_text(description(ep, timeline))
        thumbnail(ep, out / "thumbnail.png")
        print(f"설명란: {out / 'description.txt'}\n썸네일: {out / 'thumbnail.png'}")


if __name__ == "__main__":
    main()
