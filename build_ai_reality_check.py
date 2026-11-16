"""AI reality check reel: 12 talking-head clips -> sharp jump cuts (dead air removed by audio energy, ends
cut when the speaker reaches for the phone's stop button), instant punch zooms, Alfa Slab One captions
just under the chin, title chips above the head.  Ink #1B1B26 / gold #C9A24B.  9:16, 2160x3840.

Usage:  python build_ai_reality_check.py [--preview]
Needs:  media/ai_reality_check/work/words.json (analyze.py), work/fonts/AlfaSlabOne.ttf
Output: media/upload_ready/4k/ai_reality_check_reel_4k.mp4   (preview -> media/ai_reality_check/work/)
"""
import json, sys
import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build_reel as br

VIDEO = "ai_reality_check"
W, H, FPS, px = br.W, br.H, br.FPS, br.px
SRC = br.ROOT / "media" / VIDEO
WORK = SRC / "work"
OUT = br.ROOT / "media/upload_ready/4k"
FONT = WORK / "fonts" / "AlfaSlabOne.ttf"

INK, GOLD = (0x1B, 0x1B, 0x26), (0xC9, 0xA2, 0x4B)
TOP_T, CAP = 0.15, 0.72           # head top always lands at 15% of the frame; chin never lower than 72%
SIL, PAD, MAX_SHOT, MIN_SHOT = 0.35, 0.08, 1.7, 0.55
ZOOMS = (1.0, 1.22)               # instant punch in / out, alternating shot to shot
grid = lambda t: round(t * FPS) / FPS
norm = lambda w: w.lower().strip(",.?!'\"")
font = lambda s: ImageFont.truetype(str(FONT), px(s))

# Whisper mis-hears Hinglish: per-clip caption fixes {clip: {"heard": "meant"}}  ("" drops the word)
FIX = {2: {"ho": "ko"}, 4: {"jaayi": "", "s": "is"}, 7: {"Abse": "Sabse"},
       8: {"takin": "taaki", "bade": "badhe", "meise": "mein se"}, 9: {"Kusra": "Doosra", "krti": "karti", "diyna": "dena"},
       10: {"kare": "karna", "hain": "hai"}, 11: {"sirv": "sirf", "ropne": "rukne", "karthi": "karte", "lehne": "lene"}}
# where speech really ends (just before the glance/reach for the stop button) when Whisper mis-times it
END_OVERRIDE = {3: 6.32, 10: 3.31, 12: 6.9}
# head top (hair) and chin (beard bottom) as a fraction of the source frame height, measured by eye
TOP = {1: .17, 2: .11, 3: .14, 4: .21, 5: .17, 6: .22, 7: .20, 8: .22, 9: .125, 10: .06, 11: .19, 12: .19}
CHIN = {1: .615, 2: .595, 3: .67, 4: .67, 5: .64, 6: .65, 7: .667, 8: .645, 9: .645, 10: .567, 11: .645, 12: .667}
# title above the head: (clip, from word, until word or None=clip end, text)
TITLES = [
    (1, "Mai", None, "AI REALITY CHECK"),
    (2, "Jinko", "Toh", "AI TAKING YOUR JOB?"), (2, "already", None, "JOB ALREADY GONE"),
    (3, "email", None, "LAID OFF BY EMAIL"),
    (4, "pehle", "market", "10 PEOPLE NOW 3-4"), (4, "market", None, "FEWER JOBS, MORE COMPETITION"),
    (5, "sab", "competition", "EVERYONE WANTS AI"), (5, "competition", None, "TOO MANY APPLICANTS"),
    (6, "How", None, "HOW TO AVOID THIS?"),
    (7, "Sabse", None, "STEP 1: BECOME AI ENABLED"),
    (8, "Job", None, "STEP 2: FIX YOUR LINKEDIN"),
    (9, "Doosra", "Toh", "STEP 3: SHORTLIST COMPANIES"), (9, "Toh", None, "EMAIL RESUME + PORTFOLIO"),
    (10, "Wait", None, "DON'T WAIT FOR JOB POSTS"),
    (11, "Ab", "Kamse", "STEP 4: APPLY"), (11, "Kamse", "Lekin", "30-40 APPLICATIONS A DAY"),
    (11, "Lekin", "jaake", "SKILLS ALONE DON'T WIN"), (11, "jaake", None, "GO OUT OF THE BOX"),
    (12, "If", None, "COMMENT YOUR QUESTIONS"),
]


# ---------------- graphics ----------------------------------------------------------------------
def text_size(t, f):
    b = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), t, font=f)
    return b[2] - b[0], b[3] - b[1], b[0], b[1]


def caption_png(words, path):
    size = 150
    while True:
        f, gap = font(size), px(size * 0.26)
        ws = [(w.upper(), text_size(w.upper(), f)[0]) for w in words]
        total = int(sum(w for _, w in ws) + gap * (len(ws) - 1)) + px(120)
        if total <= W - px(100) or size <= 90:
            break
        size -= 6
    img = Image.new("RGBA", (total, px(260)), (0, 0, 0, 0))
    dr, x = ImageDraw.Draw(img), px(60)
    for w, wid in ws:
        dr.text((x + px(7), px(57)), w, font=f, fill=INK + (200,))                       # hard drop shadow
        dr.text((x, px(50)), w, font=f, fill=GOLD, stroke_width=px(size * 0.10), stroke_fill=INK)
        x += wid + gap
    img.save(path)
    return img.size


def title_png(text, path):
    size = 128
    while True:
        f = font(size)
        tw, th, ox, oy = text_size(text.upper(), f)
        w, h = tw + px(120), th + px(90)
        if w <= W - px(120) or size <= 60:
            break
        size -= 6
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((0, 0, w - 1, h - 1), px(34), fill=INK + (240,), outline=GOLD, width=px(8))
    dr.text(((w - tw) / 2 - ox, (h - th) / 2 - oy), text.upper(), font=f, fill=GOLD)
    img.save(path)
    return img.size


# ---------------- planning ----------------------------------------------------------------------
def energy(i):
    c = av.open(str(SRC / f"{i}.mp4")); r = av.AudioResampler(format="s16", layout="mono", rate=16000)
    x = np.concatenate([q.to_ndarray().ravel() for fr in c.decode(audio=0) for q in r.resample(fr)]).astype(float)
    return np.sqrt(np.convolve(x ** 2, np.ones(160) / 160, "same")[::160])


def load():
    data = json.load(open(WORK / "words.json"))
    clips = {}
    for i in range(1, 13):
        c = data[str(i)]
        words = [(FIX.get(i, {}).get(w, w), s, e) for w, s, e in c["words"]]
        words = [w for w in words if w[0]]
        e0 = END_OVERRIDE.get(i, min(words[-1][2], c["speech_end"]) + 0.06)   # cut before the reach for stop
        clips[i] = dict(words=words, e0=min(e0, c["dur"] - 0.01))
    return clips


def make_shots(clips):
    shots = []
    for i, c in clips.items():
        rms = energy(i)                                          # dead air -> cut (by audio, never mid-word)
        ref = np.percentile(rms[: int(c["e0"] * 100)], 75)
        onset = next((k for k in range(len(rms) - 6) if rms[k:k + 6].mean() > 0.25 * ref), 0) / 100
        c["s0"] = max(0, onset - 0.05)                           # start at the first sound (never clip a word)
        words = [w for w in c["words"] if w[2] > c["s0"] and w[1] < c["e0"]]
        lo, hi = int(c["s0"] * 100), int(c["e0"] * 100)
        quiet = rms[lo:hi] < 0.10 * np.percentile(rms[lo:hi], 75)
        ranges, cur, k = [], c["s0"], 0
        while k < len(quiet):
            if quiet[k]:
                j = k
                while j < len(quiet) and quiet[j]:
                    j += 1
                if (j - k) / 100 >= SIL and k > 0 and j < len(quiet):
                    ranges.append((cur, (lo + k) / 100 + PAD)); cur = (lo + j) / 100 - PAD
                k = j
            else:
                k += 1
        ranges.append((cur, c["e0"]))
        first = True
        for rs, re_ in ranges:
            ws = [w for w in words if rs <= (w[1] + w[2]) / 2 < re_ + 0.05]
            bounds, start = [rs], rs                             # new shot at a word gap every ~1.4-1.7 s
            for n, w in enumerate(ws[:-1]):
                if w[2] - start >= 1.4 and re_ - w[2] > MIN_SHOT or (w[2] - start >= MAX_SHOT and re_ - w[2] > 0.3):
                    b = (w[2] + ws[n + 1][1]) / 2 if ws[n + 1][1] > w[2] else ws[n + 1][1]
                    bounds.append(b); start = b
            bounds.append(re_)
            for q in range(len(bounds) - 1):
                s, e = grid(bounds[q]), grid(bounds[q + 1])
                if e - s < 1 / FPS:
                    continue
                shots.append(dict(clip=i, s=s, d=e - s, first=first, gap_before=(q == 0),
                                  words=[w for w in ws if bounds[q] <= (w[1] + w[2]) / 2 < bounds[q + 1] + (0.05 if q == len(bounds) - 2 else 0)],
                                  allwords=c["words"]))
                first = False
    t = 0.0
    for k, sh in enumerate(shots):
        i = sh["clip"]; sh["t"] = t; t += sh["d"]
        fh = CHIN[i] - TOP[i]
        zmax = (CAP - TOP_T) / fh
        sh["z"] = max(1.0, min(ZOOMS[k % 2], zmax))
        sh["gap_after"] = k + 1 == len(shots) or shots[k + 1]["gap_before"]
    return shots, t


# ---------------- rendering ---------------------------------------------------------------------
def overlays(sh, k):
    i, s, d, z = sh["clip"], sh["s"], sh["d"], sh["z"]
    ov = []
    for n, (ci, a, b, text) in enumerate(TITLES):               # title chips above the head
        if ci != i:
            continue
        ws = sh["allwords"]
        ia = next(j for j, w in enumerate(ws) if norm(w[0]) == norm(a))
        ib = next(j for j, w in enumerate(ws) if j >= ia and norm(w[0]) == norm(b)) if b else len(ws) - 1
        ta, tb = ws[ia][1] - 0.02, (ws[ib][1] - 0.02 if b else 1e9)
        t0, t1 = max(0, ta - s), min(d, tb - s)
        if t1 <= t0:
            continue
        p = WORK / f"title_{n}.png"
        w, h = title_png(text, p)
        ov.append(dict(png=p, x=f"({W}-{w})/2", y=int(TOP_T * H - h - px(80)), t0=t0, t1=t1, fade=ta >= s))
    chunks, cur = [], []                                         # captions, 1-3 words per chunk
    for w in sh["words"]:
        cur.append(w)
        if len(cur) == 3 or len(" ".join(x[0] for x in cur)) > 15 or w[0][-1] in ".,?!":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    y = int((TOP_T + z * (CHIN[i] - TOP[i])) * H + px(60))      # just under the chin
    for j, ch in enumerate(chunks):
        t0 = 0 if j == 0 else max(0, ch[0][1] - s - 0.03)
        t1 = chunks[j + 1][0][1] - s - 0.03 if j + 1 < len(chunks) else d
        p = WORK / f"cap_{k}_{j}.png"
        w, _ = caption_png([x[0] for x in ch], p)
        ov.append(dict(png=p, x=f"({W}-{w})/2", y=y, t0=t0, t1=t1))
    return ov


def render_shot(k, sh):
    out = WORK / f"shot_{k:02d}{'_p' if br.PREVIEW else ''}.mp4"
    if out.exists():                                             # resume support; delete shot_*.mp4 to redo
        return out
    i, d, z = sh["clip"], sh["d"], sh["z"]
    y_off = z * TOP[i] - TOP_T                                   # crop offset (x H) that parks the head top at TOP_T
    pad = int(round(max(0, -y_off) * H))                         # not enough wall above the head: extend it
    vf = f"[0:v]fps={FPS},scale={int(round(W * z / 2)) * 2}:-2:flags=lanczos"
    if pad:
        vf += f",pad=iw:ih+{pad}:0:{pad},fillborders=top={pad}:mode=smear"
    vf += (f",crop={W}:{H}:x='(iw-{W})/2':y={int(round(max(0, y_off) * H))},"
           f"eq=contrast=1.06:saturation=1.1,unsharp=5:5:0.5,setsar=1[v0]")
    f, inputs = [vf], ["-ss", f"{sh['s']:.3f}", "-t", f"{d:.3f}", "-i", SRC / f"{i}.mp4"]
    last, n = "v0", 1
    for o in overlays(sh, k):
        inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", o["png"]]
        src = f"{n}:v"
        if o.get("fade"):
            f.append(f"[{n}:v]format=rgba,fade=t=in:st={o['t0']:.3f}:d=0.12:alpha=1[f{n}]"); src = f"f{n}"
        f.append(f"[{last}][{src}]overlay=x={o['x']}:y={o['y']}:enable='between(t,{o['t0']:.3f},{o['t1']:.3f})'[o{n}]")
        last = f"o{n}"; n += 1
    f.append(f"[{last}]scale=in_range=auto:out_range=tv,format=yuv420p[fin]")
    br.run(inputs + ["-filter_complex", ";".join(f), "-map", "[fin]", "-t", f"{d:.3f}", "-r", FPS, "-an",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", 22 if br.PREVIEW else 16,
                     "-pix_fmt", "yuv420p", "-g", 60, "-colorspace", "bt709", "-color_primaries", "bt709",
                     "-color_trc", "bt709", out])
    return out


def build_audio(shots):
    inp, parts = [], []
    for k, sh in enumerate(shots):
        inp += ["-ss", f"{sh['s']:.3f}", "-t", f"{sh['d']:.3f}", "-i", SRC / f"{sh['clip']}.mp4"]
        fx = (",afade=t=in:d=0.008" if sh["gap_before"] else "") + \
             (f",afade=t=out:st={sh['d'] - 0.008:.3f}:d=0.008" if sh["gap_after"] else "")
        parts.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo{fx}[a{k}]")
    chain = "".join(f"[a{k}]" for k in range(len(shots)))
    g = ";".join(parts) + f";{chain}concat=n={len(shots)}:v=0:a=1,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    out = WORK / "voice.m4a"
    br.run(inp + ["-filter_complex", g, "-map", "[a]", "-c:a", "aac", "-b:a", "256k", "-ar", 48000, out])
    return out


def main():
    WORK.mkdir(exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    shots, total = make_shots(load())
    print(f"{len(shots)} shots, {total:.2f}s", flush=True)
    files = []
    for k, sh in enumerate(shots):
        print(f"shot {k} clip {sh['clip']} {sh['d']:.2f}s z={sh['z']:.2f}  " + " ".join(w[0] for w in sh["words"]), flush=True)
        files.append(render_shot(k, sh))
    audio = build_audio(shots)
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in files))
    final = WORK / f"{VIDEO}_preview.mp4" if br.PREVIEW else OUT / f"{VIDEO}_reel_4k.mp4"
    br.run(["-f", "concat", "-safe", 0, "-i", lst, "-i", audio, "-c:v", "copy", "-c:a", "copy",
            "-shortest", "-movflags", "+faststart", final])
    print("done", final)


if __name__ == "__main__":
    main()
