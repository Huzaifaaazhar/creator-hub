"""Matrix escape reel: voice clips 1m-15m + gameplay 1-5 -> 9:16 4K, under 90 s.
Font: Matrix (Audun Larsson Kleveland, letters only). Colours: neon greens on dark blacks.
Face shots pin the chin at a fixed height: captions sit just under it, stickers sit above the head.

Usage:  python build_matrix.py [--preview]
Output: media/upload_ready/4k/matrix_reel_4k.mp4   (preview -> media/matrix/work/)
"""
import json, subprocess, sys, wave
from pathlib import Path
import av
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).parent
SRC = ROOT / "media" / "matrix"
WORK = SRC / "work"
OUT = ROOT / "media/upload_ready/4k"
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
PREVIEW = "--preview" in sys.argv
S = 0.25 if PREVIEW else 1.0
W, H = int(2160 * S), int(3840 * S)
px = lambda v: int(round(v * 2 * S))                 # layout units are 1080x1920 "design px"
FONT = WORK / "fonts" / "Matrix.ttf"
NEON, LIME, BLACK = (0, 255, 65), (182, 255, 57), (3, 8, 4)
SIL, PAD = 0.38, 0.07
CHIN_PIN = 0.68
CHIN = {1: .62, 2: .65, 3: .60, 4: .61, 5: .62, 6: .60, 7: .61, 8: .62, 9: .60, 10: .60, 11: .62, 12: .62, 13: .60, 14: .62, 15: .61}
HEAD = {1: .21, 2: .30, 3: .25, 4: .28, 5: .20, 6: .20, 7: .17, 8: .20, 9: .17, 10: .20, 11: .20, 12: .22, 13: .18, 14: .18, 15: .15}
FIX = {2: {"To": "I", "build": "built", "a": "a"}, 5: {"there": "the guy at", "the": "the"},
       6: {"keep": "keeps", "reloading": "rolling", "safe": "save"}, 7: {"files": "days", "from": "in"},
       15: {"Now": "Now"}}
NUMS = {"1": "ONE", "2": "TWO", "3": "THREE", "4": "FOUR", "5": "FIVE", "6": "SIX", "7": "SEVEN", "8": "EIGHT", "9": "NINE", "100": "HUNDRED"}
EMPH = {"matrix", "glitches", "escape", "trap", "red", "blue", "agents", "boom", "wake", "loops", "exit", "third", "forever"}
grid = lambda t: round(t * FPS) / FPS
norm = lambda w: "".join(c for c in w.lower() if c.isalnum() or c == "'")


def clean(w):                                        # the font has letters only
    w = NUMS.get(w.strip(",.?!"), w)
    return "".join(c for c in w.upper() if c.isalpha() or c == " ")


def font(size):
    return ImageFont.truetype(str(FONT), px(size))


def run(args):
    r = subprocess.run([FF, "-v", "error", "-y", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-2500:])


def energy(i):
    c = av.open(str(SRC / f"{i}m.mp4")); r = av.AudioResampler(format="s16", layout="mono", rate=16000)
    x = np.concatenate([q.to_ndarray().ravel() for fr in c.decode(audio=0) for q in r.resample(fr)]).astype(float)
    return np.sqrt(np.convolve(x ** 2, np.ones(160) / 160, "same")[::160])


# ---------------- voice timeline (dead air out, cut when the eyes are still on the camera) -------
def build_voice():
    data = json.load(open(WORK / "words.json"))
    clips, t = {}, 0.0
    for i in range(1, 16):
        c = data[str(i)]
        words = [(FIX.get(i, {}).get(w, w), a, b) for w, a, b in c["words"]]
        s0 = grid(max(0, c["rms_start"] - 0.08)); e0 = grid(min(c["speech_end"] + 0.06, c["dur"] - 0.01))
        rms = energy(i); lo, hi = int(s0 * 100), int(e0 * 100)
        thr = 0.10 * np.percentile(rms[lo:hi], 75); quiet = rms[lo:hi] < thr
        ranges, cur, k = [], s0, 0
        while k < len(quiet):
            if quiet[k]:
                j = k
                while j < len(quiet) and quiet[j]:
                    j += 1
                if (j - k) / 100 >= SIL and k > 0 and j < len(quiet):
                    ranges.append((cur, grid((lo + k) / 100 + PAD))); cur = grid((lo + j) / 100 - PAD)
                k = j
            else:
                k += 1
        ranges.append((cur, e0))
        pieces, off = [], t
        for a, b in ranges:
            pieces.append(dict(a=a, b=b, off=off)); off += b - a
        clips[i] = dict(words=words, pieces=pieces, start=t, end=off)
        t = off
    return clips, t


def tl(clips, i, src):
    best = None
    for p in clips[i]["pieces"]:
        if p["a"] - 1e-6 <= src <= p["b"] + 1e-6:
            return p["off"] + (src - p["a"])
        d = min(abs(src - p["a"]), abs(src - p["b"]))
        if best is None or d < best[0]:
            best = (d, p["off"] + (min(max(src, p["a"]), p["b"]) - p["a"]))
    return best[1]


# ---------------- edit decision list ------------------------------------------------------------
def build_edl(clips, total):
    def Wd(i, word, nth=1):
        n = 0
        for w, a, b in clips[i]["words"]:
            if norm(w) == norm(word):
                n += 1
                if n == nth:
                    return grid(tl(clips, i, a))
        raise KeyError((i, word))
    St = lambda i: clips[i]["start"]
    En = lambda i: clips[i]["end"]
    game = lambda t0, t1, f, a, b: dict(kind="game", t0=t0, t1=t1, src=f, a=a, b=b)
    face = lambda t0, t1, i, z: dict(kind="face", t0=t0, t1=t1, clip=i, z=z)
    shots = [
        face(St(1), Wd(1, "Matrix"), 1, 1.10), face(Wd(1, "Matrix"), En(1), 1, 1.10),
        face(St(2), Wd(2, "escaping"), 2, 1.10), face(Wd(2, "escaping"), En(2), 2, 1.28),
        game(St(3), En(3), "1", 5.0, 10.5),
        game(St(4), En(4), "1", 10.5, 14.5),
        game(St(5), En(5), "1", 23.5, 27.5),
        game(St(6), En(6), "1", 17.5, 23.0),
        face(St(7), Wd(7, "your"), 7, 1.10), game(Wd(7, "your"), En(7), "1", 11.5, 14.8),
        game(St(8), Wd(8, "red"), "1", 36.5, 39.5), game(Wd(8, "red"), En(8), "1", 40.0, 42.4),
        game(St(9), En(9), "1", 41.0, 42.6),
        game(St(10), Wd(10, "from"), "2", 10.0, 17.0), face(Wd(10, "from"), Wd(10, "important"), 10, 1.28),
        game(Wd(10, "important"), En(10), "3", 20.0, 27.5),
        game(St(11), Wd(11, "be"), "4", 4.5, 8.0), game(Wd(11, "be"), En(11), "4", 40.0, 45.0),
        game(St(12), Wd(12, "BOOM"), "4", 34.0, 38.0), game(Wd(12, "BOOM"), En(12), "5", 38.0, 40.5),
        face(St(13), Wd(13, "third"), 13, 1.28), game(Wd(13, "third"), En(13), "5", 40.5, 44.5),
        game(St(14), En(14), "5", 44.5, 50.8),
        face(St(15), Wd(15, "exit"), 15, 1.10), game(Wd(15, "exit"), En(15), "1", 8.4, 10.2),
    ]
    for s in shots:
        s["t0"], s["t1"] = grid(s["t0"]), grid(s["t1"])
    for a, b in zip(shots, shots[1:]):
        b["t0"] = a["t1"]
    shots[-1]["t1"] = grid(total)
    L = lambda size, text, col=NEON: (size, text, col)
    stickers = [
        dict(t0=St(1), t1=En(1), lines=[L(46, "YOU ARE LIVING IN A SIMULATION"), L(46, "HOW DO YOU GET OUT", LIME)]),
        dict(t0=St(2), t1=En(2), lines=[L(48, "I BUILT THE ESCAPE"), L(48, "STEP BY STEP", LIME)]),
        dict(t0=St(4), t1=En(4), top=1010, lines=[L(84, "STEP ONE"), L(52, "FIND THE GLITCHES", LIME)]),
        dict(t0=St(5), t1=En(5), top=1010, lines=[L(84, "LOOP", LIME)]),
        dict(t0=St(6), t1=En(6), top=1010, lines=[L(84, "ROLLBACK", LIME)]),
        dict(t0=Wd(7, "your"), t1=En(7), top=1010, lines=[L(84, "STEP TWO"), L(52, "CHECK YOUR FILE", LIME)]),
        dict(t0=Wd(8, "red"), t1=En(8), top=1010, lines=[L(84, "STEP THREE"), L(52, "CHOOSE", LIME)]),
        dict(t0=St(9), t1=En(9), top=1010, lines=[L(60, "HOLD TO CHOOSE", LIME)]),
        dict(t0=Wd(10, "identify"), t1=En(10), top=1010, lines=[L(84, "STEP FOUR"), L(52, "SPOT THE AGENTS", LIME)]),
        dict(t0=St(12), t1=En(12), top=1010, lines=[L(84, "STEP FIVE"), L(52, "ANSWER THE LINE", LIME)]),
        dict(t0=Wd(13, "third"), t1=En(13), top=1010, lines=[L(76, "THIRD OPTION", LIME)]),
        dict(t0=St(14), t1=En(14), top=1010, lines=[L(52, "THE EXIT IS JUST"), L(60, "ANOTHER ROOM", LIME)]),
        dict(t0=St(15), t1=Wd(15, "exit"), lines=[L(40, "FOUR ENDINGS WHICH ONE DID YOU GET", LIME)]),
    ]
    return shots, stickers


# ---------------- graphics ----------------------------------------------------------------------
def glow_text(img, xy, text, f, fill, stroke):
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).text(xy, text, font=f, fill=fill + (255,), stroke_width=stroke)
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(px(7))))
    ImageDraw.Draw(img).text(xy, text, font=f, fill=fill + (255,), stroke_width=0)


def plate_png(lines, path, border=NEON):
    f = [font(s) for s, _, _ in lines]
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    dims = [d.textbbox((0, 0), t, font=ft) for (_, t, _), ft in zip(lines, f)]
    wmax = max(b[2] - b[0] for b in dims)
    scale = 1.0
    if wmax + px(110) > W - px(80):                      # shrink to fit the frame
        scale = (W - px(80) - px(110)) / wmax
        f = [ImageFont.truetype(str(FONT), max(8, int(px(s) * scale))) for s, _, _ in lines]
        dims = [d.textbbox((0, 0), t, font=ft) for (_, t, _), ft in zip(lines, f)]
        wmax = max(b[2] - b[0] for b in dims)
    gap = px(12)
    w = wmax + px(110); h = sum(b[3] - b[1] for b in dims) + gap * (len(lines) - 1) + px(60)
    pad = px(14)
    img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((pad, pad, pad + w, pad + h), px(14), fill=BLACK + (238,), outline=border, width=px(4))
    y = pad + px(30)
    for (sz, t, col), ft, b in zip(lines, f, dims):
        glow_text(img, (pad + (w - (b[2] - b[0])) / 2 - b[0], y - b[1]), t, ft, col, 0)
        y += b[3] - b[1] + gap
    img.save(path)
    return img.size


def hud_pngs():
    L, T = px(70), px(6)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    for x0, sx, y0, sy in ((px(36), 1, px(236), 1), (W - px(36), -1, px(236), 1), (px(36), 1, H - px(250), -1), (W - px(36), -1, H - px(250), -1)):
        xa, xb = sorted([x0, x0 + sx * L]); dr.rectangle((xa, y0 if sy > 0 else y0 - T, xb, (y0 + T) if sy > 0 else y0), fill=NEON + (200,))
        ya, yb = sorted([y0, y0 + sy * L]); dr.rectangle((min(x0, x0 + sx * T), ya, max(x0, x0 + sx * T), yb), fill=NEON + (200,))
    img.save(WORK / "hud.png")
    bar = Image.new("RGBA", (W, px(10)), NEON + (255,)); bar.save(WORK / "progress.png")


def caption_chunks(words):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or sum(len(clean(x[0])) for x in cur) > 16 or w[0][-1] in ".,?!":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    return chunks


# ---------------- geometry ----------------------------------------------------------------------
def face_geo(i, z):
    y = min(max(z * CHIN[i] - CHIN_PIN, 0), z - 1)
    return z * CHIN[i] - y, z * HEAD[i] - y, y               # chin_out, head_out, crop offset (fractions of H)


def plan_zoom(shots, stickers):
    """cap the zoom of face shots so a sticker above the head never touches the hair"""
    for sh in shots:
        if sh["kind"] != "face":
            continue
        need = 0
        for st in stickers:
            if st["t0"] < sh["t1"] and st["t1"] > sh["t0"] and "top" not in st:
                h = sum(int(s * 1.25) for s, _, _ in st["lines"]) + 40
                need = max(need, (262 + h + 24) / 1920)
        z = sh["z"]
        while z > 1.07 and face_geo(sh["clip"], z)[1] < need:
            z -= 0.01
        sh["z"] = round(z, 2)


# ---------------- rendering ---------------------------------------------------------------------
def overlays(k, sh, clips, stickers):
    d = sh["t1"] - sh["t0"]; ov = []
    for n, st in enumerate(stickers):
        a, b = max(st["t0"], sh["t0"]), min(st["t1"], sh["t1"])
        if b - a < 1 / FPS:
            continue
        p = WORK / f"st_{k}_{n}.png"
        w, h = plate_png(st["lines"], p)
        top = px(st.get("top", 262)) if sh["kind"] == "game" or "top" in st else px(262)
        if sh["kind"] == "face" and "top" not in st:        # sit just above the head
            _, head_out, _ = face_geo(sh["clip"], sh["z"])
            top = max(px(262), int(head_out * H - h - px(18)))
        ov.append(dict(png=p, x=f"({W}-{w})/2", y=top, t0=a - sh["t0"], t1=b - sh["t0"]))
    chin_out = face_geo(sh["clip"], sh["z"])[0] if sh["kind"] == "face" else CHIN_PIN
    cy = int(chin_out * H + px(80))                          # caption plate just under the chin
    for j, ch in enumerate(caption_chunks([w for w in sh["words"]])):
        lines = [(66, " ".join(clean(x[0]) for x in ch), LIME if any(norm(x[0]) in EMPH for x in ch) else NEON)]
        p = WORK / f"cap_{k}_{j}.png"
        w, h = plate_png(lines, p)
        t0 = max(0, ch[0][1] - sh["t0"] - 0.03)
        t1 = (sh["words"][-1][2] if False else None)
        ov.append(dict(png=p, x=f"({W}-{w})/2", y=cy - h // 2, t0=t0, t1=None, cap=True))
    caps = [o for o in ov if o.get("cap")]
    for q, o in enumerate(caps):
        o["t1"] = caps[q + 1]["t0"] if q + 1 < len(caps) else d
    return ov


def render_shot(k, sh, clips, stickers):
    d = round((sh["t1"] - sh["t0"]) * FPS) / FPS
    inputs, f = [], []
    if sh["kind"] == "game":
        span = sh["b"] - sh["a"]; sp = span / d
        inputs = ["-ss", sh["a"], "-t", span, "-i", SRC / f"{sh['src']}.mp4"]
        vf = (f"setpts=(PTS-STARTPTS)/{sp:.5f},fps={FPS}" if sp >= 1 else f"fps={FPS},tpad=stop_mode=clone:stop_duration={d - span + 0.1:.3f}")
        if PREVIEW:
            vf += f",scale={W}:{H}"
        f.append(f"[0:v]{vf},eq=contrast=1.05:saturation=1.1[v0]")
        sh["words"] = [w for w in sh["words"]]
    else:
        i = sh["clip"]; ps = [(p["a"] + max(sh["t0"], p["off"]) - p["off"], min(sh["t1"], p["off"] + p["b"] - p["a"]) - max(sh["t0"], p["off"]))
                              for p in clips[i]["pieces"] if min(sh["t1"], p["off"] + p["b"] - p["a"]) - max(sh["t0"], p["off"]) > 1e-6]
        a = ps[0][0]
        _, _, yoff = face_geo(i, sh["z"])
        inputs = ["-ss", f"{a:.3f}", "-t", f"{d:.3f}", "-i", SRC / f"{i}m.mp4"]
        f.append(f"[0:v]fps={FPS},scale={int(W * sh['z'])}:-2:flags=lanczos,crop={W}:{H}:x='(iw-{W})/2':y='{yoff * H:.1f}',"
                 f"eq=contrast=1.06:saturation=1.1,unsharp=5:5:0.4,setsar=1[v0]")
    ov = overlays(k, sh, clips, stickers)
    fixed = [dict(png=WORK / "hud.png", x=0, y=0, t0=0, t1=d)]
    last, n = "v0", 1
    for o in fixed + ov:
        inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", o["png"]]
        f.append(f"[{last}][{n}:v]overlay=x={o['x']}:y={o['y']}:enable='between(t,{o['t0']:.3f},{o['t1']:.3f})'[o{n}]")
        last = f"o{n}"; n += 1
    inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", WORK / "progress.png"]
    f.append(f"[{last}][{n}:v]overlay=x='-{W}+{W}*({sh['t0']:.3f}+t)/{sh['total']:.3f}':y=0[pb]")
    f.append("[pb]scale=in_range=auto:out_range=tv,format=yuv420p[fin]")
    out = WORK / f"shot_{k:02d}{'_p' if PREVIEW else ''}.mp4"
    if not PREVIEW and out.exists():                     # resume: reuse finished 4K shots
        return out
    run(inputs + ["-filter_complex", ";".join(f), "-map", "[fin]", "-t", f"{d:.3f}", "-r", FPS, "-an", "-c:v", "libx264",
                  "-preset", "veryfast", "-crf", 24 if PREVIEW else 16, "-pix_fmt", "yuv420p", "-g", 60, "-colorspace", "bt709",
                  "-color_primaries", "bt709", "-color_trc", "bt709", out])
    return out


def build_audio(clips, total):
    inp, parts, n = [], [], 0
    for i in range(1, 16):
        for p in clips[i]["pieces"]:
            inp += ["-ss", f"{p['a']:.3f}", "-t", f"{p['b'] - p['a']:.3f}", "-i", SRC / f"{i}m.mp4"]
            parts.append(f"[{n}:a]aresample=48000,afade=t=in:d=0.006,afade=t=out:st={p['b'] - p['a'] - 0.006:.3f}:d=0.006[a{n}]"); n += 1
    chain = "".join(f"[a{k}]" for k in range(n))
    g = ";".join(parts) + f";{chain}concat=n={n}:v=0:a=1,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    out = WORK / "voice_mix.m4a"
    run(inp + ["-filter_complex", g, "-map", "[a]", "-c:a", "aac", "-b:a", "256k", "-ar", 48000, out])
    return out


def attach_words(shots, clips):
    for sh in shots:
        sh["words"] = []
        for i in range(1, 16):
            for w, a, b in clips[i]["words"]:
                if not clean(w):
                    continue
                ta = tl(clips, i, a)
                if sh["t0"] - 1e-6 <= ta < sh["t1"] - 1e-6:
                    sh["words"].append((w, ta, tl(clips, i, min(b, clips[i]["pieces"][-1]["b"]))))


def main():
    WORK.mkdir(exist_ok=True)
    clips, total = build_voice()
    shots, stickers = build_edl(clips, total)
    attach_words(shots, clips); plan_zoom(shots, stickers); hud_pngs()
    print(f"{len(shots)} shots, {total:.2f}s", flush=True)
    files = []
    for k, sh in enumerate(shots):
        sh["total"] = total
        print(k, sh["kind"], sh.get("src", f"face{sh.get('clip')}"), f"{sh['t0']:.2f}-{sh['t1']:.2f}",
              (f"x{(sh['b'] - sh['a']) / (sh['t1'] - sh['t0']):.2f}" if sh["kind"] == "game" else f"z{sh['z']}"), flush=True)
        files.append(render_shot(k, sh, clips, stickers))
    audio = build_audio(clips, total)
    lst = WORK / "concat.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in files))
    final = WORK / "matrix_preview.mp4" if PREVIEW else OUT / "matrix_reel_4k.mp4"
    OUT.mkdir(parents=True, exist_ok=True)
    run(["-f", "concat", "-safe", 0, "-i", lst, "-i", audio, "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", final])
    print("done", final)


if __name__ == "__main__":
    main()
