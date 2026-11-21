"""Overtime reel: 13 talking-head clips -> sharp cuts, instant punch zooms, Montserrat captions (NO backgrounds).
Captions sit just under the chin; keyword text sits just above the head (or below the captions if the head leaves no room).
Clip 1 starts as recorded (phone moving to the face). Every clip is cut when the eyes leave the camera.

Usage:  python build_overtime.py [--preview]
Output: media/upload_ready/4k/overtime_reel_4k.mp4   (preview -> media/overtime/work/)
"""
import json, subprocess, sys
from pathlib import Path
import av
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
SRC = ROOT / "media" / "overtime"
WORK = SRC / "work"
OUT = ROOT / "media/upload_ready/4k"
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
PREVIEW = "--preview" in sys.argv
S = 0.25 if PREVIEW else 1.0
W, H = int(2160 * S), int(3840 * S)
px = lambda v: int(round(v * 2 * S))                      # layout units are 1080x1920 design px
FONT = WORK / "fonts" / "Montserrat.ttf"
WHITE, YELLOW, BLACK = (255, 255, 255), (255, 214, 10), (0, 0, 0)
SIL, PAD, CHIN_PIN, TOP_MIN = 0.38, 0.07, 0.66, 190
CHIN = {1: .57, 2: .64, 3: .62, 4: .68, 5: .61, 6: .60, 7: .60, 8: .63, 9: .62, 10: .63, 11: .63, 12: .62, 13: .62}
HEAD = {1: .08, 2: .20, 3: .22, 4: .25, 5: .15, 6: .22, 7: .17, 8: .20, 9: .17, 10: .15, 11: .15, 12: .17, 13: .17}
FIX = {1: {"kalne.": "karte hain."}, 3: {"laid": "late", "hoon.": "honge."}, 4: {"nikhaalde,": "nikaal dein,"},
       5: {"deeni": "dena"}, 6: {"etna": "itna", "ohoho": "oho"},
       7: {"wo": "woh", "ye": "yeh", "the": "tha", "baay": "bas", "100": "100%", "%": ""},
       10: {"jatein": "jaate ho"},
       12: {"kya,": "", "kya": "ya toh", "late": "ya late", "jaani": "zyada", "mai": "main"},
       13: {"zildi": "jaldi", "karlnay": "kar", "otna": "utna", "bahtar": "behtar", "niche": "neeche"}}
EMPH = {"overtime", "shadow", "appreciation", "mindset", "effort", "100", "startups", "fast", "comment", "majboor"}
TRUE_START = {5: 0.76, 11: 0.50, 12: 0.76}                   # looks at the button first, then speaks
grid = lambda t: round(t * FPS) / FPS
norm = lambda w: "".join(c for c in w.lower() if c.isalnum() or c == "'")


def font(size):
    f = ImageFont.truetype(str(FONT), px(size))
    try:
        f.set_variation_by_axes([800])                        # Montserrat ExtraBold
    except Exception:
        pass
    return f


def run(args):
    r = subprocess.run([FF, "-v", "error", "-y", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-2500:])


def energy(i):
    c = av.open(str(SRC / f"{i}.mp4")); r = av.AudioResampler(format="s16", layout="mono", rate=16000)
    x = np.concatenate([q.to_ndarray().ravel() for fr in c.decode(audio=0) for q in r.resample(fr)]).astype(float)
    return np.sqrt(np.convolve(x ** 2, np.ones(160) / 160, "same")[::160])


# ---------------- voice timeline ----------------------------------------------------------------
def build_voice():
    data = json.load(open(WORK / "words.json"))
    clips, t = {}, 0.0
    for i in range(1, 14):
        c = data[str(i)]
        words = [(FIX.get(i, {}).get(w, w), a, b) for w, a, b in c["words"]]
        words = [x for x in words if x[0]]
        true_start = TRUE_START.get(i, c["rms_start"])                    # measured from the audio, not Whisper
        s0 = 0.0 if i == 1 else grid(max(0, true_start - 0.08))           # clip 1 keeps the phone-to-face start
        if i in TRUE_START:                                               # Whisper starts these words too early
            words = [(w, max(a, true_start), max(b, true_start + 0.1)) for w, a, b in words]
        e0 = grid(min(c["speech_end"] + 0.06, c["dur"] - 0.01))
        rms = energy(i); lo, hi = int(s0 * 100), int(e0 * 100)
        thr = 0.10 * np.percentile(rms[lo:hi], 75); quiet = rms[lo:hi] < thr
        ranges, cur, k = [], s0, 0
        while k < len(quiet):
            if quiet[k]:
                j = k
                while j < len(quiet) and quiet[j]:
                    j += 1
                if (j - k) / 100 >= SIL and k > 0 and j < len(quiet) and not (i == 1 and (lo + k) / 100 < 1.2):
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


# ---------------- shots -------------------------------------------------------------------------
def make_shots(clips):
    shots, flip = [], 0
    for i in range(1, 14):
        for p in clips[i]["pieces"]:
            ws = [(w, tl(clips, i, a), tl(clips, i, min(b, p["b"]))) for w, a, b in clips[i]["words"]
                  if p["a"] - 0.05 <= (a + b) / 2 < p["b"] + 0.05]
            pa, pb = p["off"], p["off"] + p["b"] - p["a"]
            if not ws:
                runs = [["norm", []]]
            else:
                runs = []
                for w in ws:
                    tag = "emph" if norm(w[0]) in EMPH else "norm"
                    if runs and runs[-1][0] == tag:
                        runs[-1][1].append(w)
                    else:
                        runs.append([tag, [w]])
            out = []
            for r in runs:                                   # split long plain runs
                stack = [r]
                while stack:
                    q = stack.pop(0)
                    if len(q[1]) > 3 and q[1][-1][2] - q[1][0][1] > 1.9:
                        h = len(q[1]) // 2
                        stack = [[q[0], q[1][:h]], [q[0], q[1][h:]]] + stack
                    else:
                        out.append(q)
            runs = out
            dur = lambda r: (r[1][-1][2] - r[1][0][1]) if r[1] else 9
            while len(runs) > 1:                             # no flicker: merge shots < 0.45 s
                k = next((k for k, r in enumerate(runs) if dur(r) < 0.45), None)
                if k is None:
                    break
                t = k + 1 if (k == 0 or (runs[k][0] == "emph" and k + 1 < len(runs))) else k - 1
                lo_, hi_ = sorted((k, t))
                tag = "emph" if "emph" in (runs[lo_][0], runs[hi_][0]) else "norm"
                runs[lo_:hi_ + 1] = [[tag, runs[lo_][1] + runs[hi_][1]]]
            bounds = [pa]
            for a, b in zip(runs, runs[1:]):
                ea, sb = a[1][-1][2], b[1][0][1]
                bounds.append(min(max(grid((ea + sb) / 2 if sb > ea else sb), pa + 0.1), pb - 0.1))
            bounds.append(pb)
            for q, r in enumerate(runs):
                t0, t1 = grid(bounds[q]), grid(bounds[q + 1])
                if t1 - t0 < 1 / FPS:
                    continue
                if i == 1:
                    z = 1.18 if r[0] == "emph" else 1.0       # clip 1 stays as recorded
                else:
                    z = 1.30 if r[0] == "emph" else (1.10 if flip % 2 == 0 else 1.20)
                    flip += 0 if r[0] == "emph" else 1
                shots.append(dict(clip=i, t0=t0, t1=t1, a=p["a"] + (t0 - p["off"]), z=z, words=r[1], tag=r[0]))
    for a, b in zip(shots, shots[1:]):
        b["t0"] = a["t1"]
    return shots


def build_stickers(clips):
    def Wd(i, word):
        for w, a, b in clips[i]["words"]:
            if norm(w) == norm(word):
                return grid(tl(clips, i, a))
        raise KeyError((i, word))
    St = lambda i: clips[i]["start"]
    En = lambda i: clips[i]["end"]
    Y = lambda t: (t, YELLOW)
    Wt = lambda t: (t, WHITE)
    return [
        dict(t0=St(1), t1=En(1), size=78, segs=[Y("OVERTIME"), Wt(" IN IT JOBS")]),
        dict(t0=St(2), t1=Wd(2, "Overtime"), size=70, segs=[Wt("IT INDUSTRY "), Y("REALITY")]),
        dict(t0=Wd(2, "Overtime"), t1=En(2), size=70, segs=[Y("OVERTIME"), Wt(" FOLLOWS YOU")]),
        dict(t0=St(4), t1=En(4), size=70, segs=[Wt("NO EXTRA "), Y("APPRECIATION")]),
        dict(t0=St(5), t1=En(5), size=70, segs=[Wt("IT CULTURE "), Y("MINDSET")]),
        dict(t0=Wd(7, "100"), t1=En(7), size=74, segs=[Y("100%"), Wt(" EFFORT")]),
        dict(t0=St(8), t1=En(8), size=70, segs=[Y("STARTUP"), Wt(" WORK CULTURE")]),
        dict(t0=St(9), t1=En(9), size=70, segs=[Wt("FAST "), Y("PACE"), Wt(" JOBS")]),
        dict(t0=St(11), t1=En(11), size=70, segs=[Wt("NEW "), Y("ENGINEER")]),
        dict(t0=Wd(12, "culture"), t1=En(12), size=70, segs=[Y("WORK CULTURE"), Wt(" REALITY")]),
        dict(t0=Wd(13, "comment"), t1=En(13), size=74, segs=[Y("COMMENT"), Wt(" YOUR TAKE")]),
    ]


# ---------------- text (no backgrounds: outline + soft shadow only) ------------------------------
def text_png(segs, size, path, max_w=None):
    max_w = max_w or (W - px(70))
    sz = size
    while True:
        f = font(sz)
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        wd = sum(d.textlength(t, font=f) for t, _ in segs)
        if wd + px(40) <= max_w or sz <= 36:
            break
        sz -= 3
    st = max(2, int(px(sz) * 0.10))
    bb = d.textbbox((0, 0), "HgÁ", font=f)
    w, h = int(wd) + px(40), bb[3] - bb[1] + px(34)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = px(20); y = px(12) - bb[1]
    for t, col in segs:
        ImageDraw.Draw(sh).text((x + px(3), y + px(6)), t, font=f, fill=(0, 0, 0, 170), stroke_width=st, stroke_fill=(0, 0, 0, 170))
        ImageDraw.Draw(img).text((x, y), t, font=f, fill=col + (255,), stroke_width=st, stroke_fill=BLACK + (255,))
        x += d.textlength(t, font=f)
    sh.alpha_composite(img)
    sh.save(path)
    return sh.size


def caption_chunks(words):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or sum(len(x[0]) for x in cur) > 17 or w[0][-1] in ".,?!":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    return chunks


# ---------------- geometry ----------------------------------------------------------------------
def face_geo(i, z):
    y = min(max(z * CHIN[i] - CHIN_PIN, 0), z - 1)
    return z * CHIN[i] - y, z * HEAD[i] - y, y               # chin_out, head_out, crop offset (fractions of H)


def overlays(k, sh, stickers):
    d = sh["t1"] - sh["t0"]; ov = []
    chin_out, head_out, _ = face_geo(sh["clip"], sh["z"])
    cy = int(chin_out * H + px(80))                          # caption line sits just under the chin
    for n, st in enumerate(stickers):
        a, b = max(st["t0"], sh["t0"]), min(st["t1"], sh["t1"])
        if b - a < 1 / FPS:
            continue
        p = WORK / f"kw_{k}_{n}.png"
        w, h = text_png(st["segs"], st["size"], p)
        room = head_out * H - px(14) - px(TOP_MIN)
        y = int(head_out * H - px(14) - h) if room >= h else cy + px(86)   # above the head, else under the captions
        ov.append(dict(png=p, x=f"({W}-{w})/2", y=y, t0=a - sh["t0"], t1=b - sh["t0"]))
    chunks = caption_chunks(sh["words"])
    for j, ch in enumerate(chunks):
        segs = []
        for q, w in enumerate(ch):
            segs.append((w[0].upper() + (" " if q < len(ch) - 1 else ""), YELLOW if norm(w[0]) in EMPH else WHITE))
        p = WORK / f"cap_{k}_{j}.png"
        w, h = text_png(segs, 68, p)
        t0 = 0 if j == 0 else max(0, ch[0][1] - sh["t0"] - 0.03)
        t1 = d if j == len(chunks) - 1 else max(t0 + 0.1, chunks[j + 1][0][1] - sh["t0"] - 0.03)
        ov.append(dict(png=p, x=f"({W}-{w})/2", y=cy - h // 2, t0=t0, t1=t1))
    return ov


def render_shot(k, sh, stickers):
    out = WORK / f"shot_{k:02d}{'_p' if PREVIEW else ''}.mp4"
    if not PREVIEW and out.exists():                         # resume: reuse finished 4K shots
        return out
    d = round((sh["t1"] - sh["t0"]) * FPS) / FPS
    _, _, yoff = face_geo(sh["clip"], sh["z"])
    inputs = ["-ss", f"{sh['a']:.3f}", "-t", f"{d:.3f}", "-i", SRC / f"{sh['clip']}.mp4"]
    f = [f"[0:v]fps={FPS},scale={int(W * sh['z'])}:-2:flags=lanczos,crop={W}:{H}:x='(iw-{W})/2':y='{yoff * H:.1f}',"
         f"eq=contrast=1.05:saturation=1.1,unsharp=5:5:0.4,setsar=1[v0]"]
    last, n = "v0", 1
    for o in overlays(k, sh, stickers):
        inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", o["png"]]
        f.append(f"[{last}][{n}:v]overlay=x={o['x']}:y={o['y']}:enable='between(t,{o['t0']:.3f},{o['t1']:.3f})'[o{n}]")
        last = f"o{n}"; n += 1
    f.append(f"[{last}]scale=in_range=auto:out_range=tv,format=yuv420p[fin]")
    run(inputs + ["-filter_complex", ";".join(f), "-map", "[fin]", "-t", f"{d:.3f}", "-r", FPS, "-an", "-c:v", "libx264",
                  "-preset", "veryfast", "-crf", 24 if PREVIEW else 16, "-pix_fmt", "yuv420p", "-g", 60, "-colorspace", "bt709",
                  "-color_primaries", "bt709", "-color_trc", "bt709", out])
    return out


def build_audio(clips):
    inp, parts, n = [], [], 0
    for i in range(1, 14):
        for p in clips[i]["pieces"]:
            inp += ["-ss", f"{p['a']:.3f}", "-t", f"{p['b'] - p['a']:.3f}", "-i", SRC / f"{i}.mp4"]
            parts.append(f"[{n}:a]aresample=48000,afade=t=in:d=0.006,afade=t=out:st={p['b'] - p['a'] - 0.006:.3f}:d=0.006[a{n}]"); n += 1
    chain = "".join(f"[a{k}]" for k in range(n))
    g = ";".join(parts) + f";{chain}concat=n={n}:v=0:a=1,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    out = WORK / "voice_mix.m4a"
    run(inp + ["-filter_complex", g, "-map", "[a]", "-c:a", "aac", "-b:a", "256k", "-ar", 48000, out])
    return out


def main():
    WORK.mkdir(exist_ok=True)
    clips, total = build_voice()
    shots, stickers = make_shots(clips), build_stickers(clips)
    print(f"{len(shots)} shots, {total:.2f}s", flush=True)
    files = []
    for k, sh in enumerate(shots):
        print(k, f"clip{sh['clip']}", f"{sh['t0']:.2f}-{sh['t1']:.2f}", f"z{sh['z']}", sh["tag"], " ".join(w[0] for w in sh["words"]), flush=True)
        files.append(render_shot(k, sh, stickers))
    audio = build_audio(clips)
    lst = WORK / "concat.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in files))
    final = WORK / "overtime_preview.mp4" if PREVIEW else OUT / "overtime_reel_4k.mp4"
    OUT.mkdir(parents=True, exist_ok=True)
    run(["-f", "concat", "-safe", 0, "-i", lst, "-i", audio, "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", final])
    print("done", final)


if __name__ == "__main__":
    main()
