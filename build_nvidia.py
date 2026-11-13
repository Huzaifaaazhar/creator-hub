"""NVIDIA reel: talking-head clips 1-9, instant cuts + punch zooms, Jost captions just under the chin,
quick news-image cutaways.  NVIDIA green / black / white only.  9:16, 2160x3840.

Usage:  python build_nvidia.py [--preview]
Needs:  media/nvidia/work/words.json (analyze.py + words_fix.py), media/nvidia/work/fonts/Jost.ttf
Output: media/upload_ready/4k/nvidia_reel_4k.mp4   (preview -> media/nvidia/work/)
"""
import json, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build_reel as br

VIDEO = "nvidia"
W, H, FPS, px = br.W, br.H, br.FPS, br.px
SRC = br.ROOT / "media" / VIDEO
WORK = SRC / "work"
OUT = br.ROOT / "media/upload_ready/4k"

GREEN, WHITE, BLACK = (118, 185, 0), (255, 255, 255), (0, 0, 0)
JOST = WORK / "fonts" / "Jost.ttf"
KEYWORDS = {"nvidia", "ceo", "ai", "bubble", "burst", "billions", "huge", "impact", "positions", "news",
            "follow", "jensen", "33", "weeks", "speed", "different", "stepped", "down"}

# caption text fixes (Hinglish / mis-heard words)
FIX = {1: {"rin.": "rahi."}, 2: {"cheezo": "cheezon"}, 3: {"CO": "CEO"},
       7: {"2": "do", "bahot": "bahut", "hame": "hamein"}}
# chin height (fraction of source frame, measured by eye) per clip
CHIN = {1: .68, 2: .71, 3: .62, 4: .69, 5: .67, 6: .68, 7: .75, 8: .65, 9: .67}
SPEECH_END = {}
CHIN_PIN, GAP, MIN_SHOT = 0.60, 0.30, 0.40
# phrases (first word, last word) that get an instant punch-in
EMPH = {1: [("bubble", "burst")], 2: [("speed", "doon")], 3: [("33", "years")], 4: [("market", "cap")],
        5: [("positions", "positions")], 6: [("huge", "impact")], 7: [("bahut", "news")],
        8: [("upcoming", "weeks")], 9: [("follow", "more")]}
# news cutaways: (first word, last word, image, punch focus (x, y) or None, punch zoom)
NEWS = {3: [("just", "down", "ceo.PNG", (0.39, 0.40), 1.22), ("from", "position", "oustated.PNG", None, 1.0)],
        4: [("billions", "dollars", "wiped.PNG", None, 1.0)]}
grid = lambda t: round(t * FPS) / FPS
norm = lambda w: w.lower().strip(",.?!'\"")


def jost(size, wght=700):
    f = ImageFont.truetype(str(JOST), px(size))
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


def caption_png(words, path):
    """Jost Bold, white; key words NVIDIA green; black outline; shrinks to fit."""
    size, d = 150, ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    while True:
        f, gap = jost(size), px(size * 0.24)
        ws = [(w.upper(), d.textlength(w.upper(), font=f)) for w in words]
        total = int(sum(w for _, w in ws) + gap * (len(ws) - 1)) + px(120)
        if total <= W - px(80) or size <= 90:
            break
        size -= 6
    img = Image.new("RGBA", (total, px(260)), (0, 0, 0, 0))
    dr, x = ImageDraw.Draw(img), px(60)
    for w, wid in ws:
        dr.text((x, px(50)), w, font=f, fill=GREEN if norm(w) in KEYWORDS else WHITE,
                stroke_width=px(size * 0.09), stroke_fill=BLACK)
        x += wid + gap
    img.save(path)
    return img.size


# ---- geometry: chin pinned so captions always sit just below it ---------------------------------
def zmin(i):
    return max(1.10, (1 - 0.68) / (1 - CHIN[i]))


def chin_out(i, z):
    return max(CHIN_PIN, z * (CHIN[i] - 1) + 1)


def face_chain(i, z, label):
    """face clip -> 9:16 frame at zoom z with the chin pinned; z is a number or an ffmpeg expression of t"""
    ys = f"min(max(ih*{CHIN[i]}-{CHIN_PIN * H:.1f},0),ih-{H})"
    return (f"[0:v]fps={FPS},scale=w='{W}*{z}':h=-2:eval=frame:flags=lanczos,"
            f"crop={W}:{H}:x='(iw-{W})/2':y='{ys}',eq=contrast=1.05:saturation=1.08,unsharp=5:5:0.5,setsar=1[{label}]")


# ---- shot planning -----------------------------------------------------------------------------
def load():
    data = json.load(open(WORK / "words.json"))
    SPEECH_END.update(json.load(open(WORK / "speech_end.json")))
    clips = {}
    for i in range(1, 10):
        c = data[str(i)]
        words = [(FIX.get(i, {}).get(w, w), s, e) for w, s, e in c["words"]]
        # cut ~0.06 s after the *measured* end of speech (work/speech_end.py), not Whisper's padded word end
        end = min(words[-1][2], SPEECH_END[str(i)]) + 0.06
        clips[i] = dict(words=words, s0=max(0, c["rms_start"] - 0.08), e0=min(end, c["dur"] - 0.01))
    return clips


def make_shots(clips):
    shots = []
    for i, c in clips.items():
        words = [w for w in c["words"] if w[2] > c["s0"] and w[1] < c["e0"]]
        # tag every word: news window / emphasis / normal
        tag = ["norm"] * len(words)
        for (a, b) in EMPH.get(i, []):
            ia = next(j for j, w in enumerate(words) if norm(w[0]) == a)
            ib = next(j for j, w in enumerate(words) if j >= ia and norm(w[0]) == b)
            for j in range(ia, ib + 1):
                tag[j] = "emph"
        for k, (a, b, img, foc, zz) in enumerate(NEWS.get(i, [])):
            ia = next(j for j, w in enumerate(words) if norm(w[0]) == a)
            ib = next(j for j, w in enumerate(words) if j >= ia and norm(w[0]) == b)
            for j in range(ia, ib + 1):
                tag[j] = f"news{k}"
        # dead air between words -> removed (audio and video)
        ranges, cur = [], c["s0"]
        for a, b in zip(words, words[1:]):
            if b[1] - a[2] >= GAP:
                ranges.append((cur, a[2] + 0.07)); cur = b[1] - 0.06
        ranges.append((cur, c["e0"]))
        n_clip = 0
        for (rs, re_) in ranges:
            idx = [j for j, w in enumerate(words) if rs <= (w[1] + w[2]) / 2 and w[1] < re_]
            runs = []                                          # maximal runs of the same tag
            for j in idx:
                if runs and runs[-1][0] == tag[j]:
                    runs[-1][1].append(j)
                else:
                    runs.append([tag[j], [j]])
            split = []                                         # split long plain runs at a word boundary
            for r in runs:
                if r[0] == "norm" and words[r[1][-1]][2] - words[r[1][0]][1] > 1.9 and len(r[1]) > 3:
                    h = len(r[1]) // 2
                    split += [[r[0], r[1][:h]], [r[0], r[1][h:]]]
                else:
                    split.append(r)
            runs, k = split, 0
            while k < len(runs):                               # absorb tiny plain runs into a plain neighbour
                dur = words[runs[k][1][-1]][2] - words[runs[k][1][0]][1]
                if runs[k][0] == "norm" and dur < MIN_SHOT:
                    if k > 0 and runs[k - 1][0] == "norm":
                        runs[k - 1][1] += runs[k][1]; del runs[k]; continue
                    if k + 1 < len(runs) and runs[k + 1][0] == "norm":
                        runs[k + 1][1] = runs[k][1] + runs[k + 1][1]; del runs[k]; continue
                k += 1
            bounds = [rs]
            for a, b in zip(runs, runs[1:]):
                ea, sb = words[a[1][-1]][2], words[b[1][0]][1]
                bounds.append((ea + sb) / 2 if sb > ea else sb)
            bounds.append(re_)
            for q, r in enumerate(runs):
                s, e = grid(bounds[q]), grid(bounds[q + 1])
                shots.append(dict(clip=i, s=s, d=e - s, tag=r[0], gap_before=(q == 0),
                                  words=[words[j] for j in r[1]], n=n_clip))
                n_clip += 1
    t, flip = 0.0, 0
    for k, sh in enumerate(shots):
        sh["t"] = t; t += sh["d"]
        z0 = zmin(sh["clip"])
        if sh["tag"] == "emph":
            sh["z"] = z0 + 0.26
        else:
            sh["z"] = z0 + (0.0 if flip % 2 == 0 else 0.12); flip += 1
        sh["gap_after"] = k + 1 == len(shots) or shots[k + 1]["gap_before"] or shots[k + 1]["clip"] != sh["clip"]
    return shots


# ---- rendering ---------------------------------------------------------------------------------
def captions(sh, k):
    chunks, cur, ov = [], [], []
    for w in sh["words"]:
        cur.append(w)
        if len(cur) == 3 or w[0][-1] in ".,?!":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    y = int(chin_out(sh["clip"], zmin(sh["clip"]) if sh["tag"].startswith("news") else sh["z"]) * 3840 + 40)
    for j, ch in enumerate(chunks):
        t0 = 0 if j == 0 else max(0, ch[0][1] - sh["s"] - 0.03)
        t1 = chunks[j + 1][0][1] - sh["s"] - 0.03 if j + 1 < len(chunks) else sh["d"]
        p = WORK / f"cap_{k}_{j}.png"
        w, _ = caption_png([x[0] for x in ch], p)
        ov.append(dict(png=p, x=f"({W}-{w})/2", y=px(y), t0=t0, t1=t1))
    return ov


def news_filters(sh, f):
    """dimmed face behind a quick news-image card; headline punch-in as an instant keyframe"""
    i = sh["clip"]; a, b, name, foc, zz = NEWS[i][int(sh["tag"][4:])]
    im = Image.open(SRC / name)
    cw = px(1880); ch = int(cw * im.height / im.width); bd = px(10)
    zexpr = "1" if not foc else f"if(lt(t,0.32),1,{zz})"
    fx, fy = foc or (0.5, 0.5)
    f.append(face_chain(i, zmin(i), "face"))
    f.append(f"[face]scale={W // 16}:{H // 16}:flags=bilinear,scale={W}:{H}:flags=bilinear,eq=brightness=-0.42:saturation=0.5[bg]")
    f.append(f"[1:v]format=rgb24,scale=w='{cw}*{zexpr}':h=-2:eval=frame:flags=lanczos,"
             f"crop={cw}:{ch}:x='min(max(iw*{fx}-{cw}/2,0),iw-{cw})':y='min(max(ih*{fy}-{ch}/2,0),ih-{ch})',"
             f"unsharp=5:5:0.8,pad={cw + 2 * bd}:{ch + 2 * bd}:{bd}:{bd}:color=0x76B900[card]")
    top = int(H * 0.40 - (ch + 2 * bd) / 2)
    f.append(f"[bg][card]overlay=x=({W}-w)/2:y={top}[base]")
    return ["-loop", 1, "-t", f"{sh['d']:.3f}", "-i", SRC / name]


def render_shot(k, sh):
    d, i = sh["d"], sh["clip"]
    inputs = ["-ss", f"{sh['s']:.3f}", "-t", f"{d:.3f}", "-i", SRC / f"{i}.mp4"]
    f = []
    if sh["tag"].startswith("news"):
        inputs += news_filters(sh, f)
        first_cap = 2
    else:
        f.append(face_chain(i, sh["z"], "base"))
        first_cap = 1
    last = "base"
    for j, o in enumerate(captions(sh, k)):
        inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", o["png"]]
        f.append(f"[{first_cap + j}:v]format=rgba[w{j}]")
        f.append(f"[{last}][w{j}]overlay=x={o['x']}:y={o['y']}:enable='between(t,{o['t0']:.3f},{o['t1']:.3f})'[o{j}]")
        last = f"o{j}"
    f.append(f"[{last}]scale=in_range=auto:out_range=tv,format=yuv420p[fin]")
    out = WORK / f"shot_{k:02d}{'_p' if br.PREVIEW else ''}.mp4"
    br.run(inputs + ["-filter_complex", ";".join(f), "-map", "[fin]", "-t", f"{d:.3f}", "-r", FPS, "-an",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", 22 if br.PREVIEW else 16,
                     "-pix_fmt", "yuv420p", "-g", 60, "-colorspace", "bt709", "-color_primaries", "bt709",
                     "-color_trc", "bt709", out])
    return out


def sfx_track(shots, total, path):
    sr = 48000
    buf = np.zeros(int((total + 0.5) * sr))
    for sh in shots:                                          # soft low thud when a news image hits
        if sh["tag"].startswith("news"):
            n = int(0.3 * sr); x = np.arange(n) / sr
            y = np.sin(2 * np.pi * (50 + 80 * np.exp(-x * 28)) * x) * np.exp(-x * 10) * 0.5
            a = int(sh["t"] * sr); buf[a:a + n] += y[:len(buf) - a]
    st = (np.clip(buf, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(sr)
        wv.writeframes(np.repeat(st, 2).tobytes())


def build_audio(shots, total):
    inp, parts = [], []
    for k, sh in enumerate(shots):
        inp += ["-ss", f"{sh['s']:.3f}", "-t", f"{sh['d']:.3f}", "-i", SRC / f"{sh['clip']}.mp4"]
        fx = (",afade=t=in:d=0.008" if sh["gap_before"] else "") + \
             (f",afade=t=out:st={sh['d'] - 0.008:.3f}:d=0.008" if sh["gap_after"] else "")
        parts.append(f"[{k}:a]aresample=48000{fx}[a{k}]")
    sfx = WORK / "sfx.wav"
    sfx_track(shots, total, sfx)
    inp += ["-i", sfx]
    chain = "".join(f"[a{k}]" for k in range(len(shots)))
    g = (";".join(parts) + f";{chain}concat=n={len(shots)}:v=0:a=1,aformat=channel_layouts=stereo[v];"
         f"[{len(shots)}:a]aformat=channel_layouts=stereo[s];[v][s]amix=inputs=2:normalize=0:duration=first,"
         "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    out = WORK / "voice_mix.m4a"
    br.run(inp + ["-filter_complex", g, "-map", "[a]", "-c:a", "aac", "-b:a", "256k", "-ar", 48000, out])
    return out


def main():
    WORK.mkdir(exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    shots = make_shots(load())
    total = sum(s["d"] for s in shots)
    print(f"{len(shots)} shots, {total:.2f}s", flush=True)
    files = []
    for k, sh in enumerate(shots):
        print(f"shot {k} clip {sh['clip']} {sh['tag']} {sh['d']:.2f}s z={sh['z']:.2f}  "
              + " ".join(w[0] for w in sh["words"]), flush=True)
        files.append(render_shot(k, sh))
    audio = build_audio(shots, total)
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in files))
    final = WORK / f"{VIDEO}_preview.mp4" if br.PREVIEW else OUT / f"{VIDEO}_reel_4k.mp4"
    br.run(["-f", "concat", "-safe", 0, "-i", lst, "-i", audio, "-c:v", "copy", "-c:a", "copy",
            "-shortest", "-movflags", "+faststart", final])
    print("done", final)


if __name__ == "__main__":
    main()
