"""AI-engineer reel: 12 talking-head clips -> sharp jump cuts (dead air removed by audio energy),
instant punch zooms, Robot Reavers captions just under the chin, top-band sticker graphics,
HUD corners, progress bar, RGB-glitch on hard cuts.  9:16, 2160x3840.

Usage:  python build_ai_engineer.py [--preview]
Needs:  media/ai_engineer/work/words.json (analyze.py), media/ai_engineer/work/fonts/RobotReavers.ttf
Output: media/upload_ready/4k/ai_engineer_reel_4k.mp4   (preview -> media/ai_engineer/work/)
"""
import json, wave
import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build_reel as br

VIDEO = "ai_engineer"
W, H, FPS, px = br.W, br.H, br.FPS, br.px
SRC = br.ROOT / "media" / VIDEO
WORK = SRC / "work"
OUT = br.ROOT / "media/upload_ready/4k"
FONT = WORK / "fonts" / "RobotReavers.ttf"

WHITE, BLACK = (255, 255, 255), (0, 0, 0)
CYAN, PINK, YELLOW = (0, 229, 255), (255, 45, 149), (255, 230, 0)
KEYWORDS = {"ai", "engineer", "engineers", "industry", "demand", "100x", "expectations", "race", "fast",
            "updated", "career", "personal", "life", "compromise", "weekends", "raate", "naukri", "goal",
            "competition", "skillful", "interview", "crack", "cv", "rag", "fine", "tuning", "comments",
            "talented", "strong", "aspiring", "nahi.", "videos", "news"}

FIX = {1: {"sabkuj": "sab kuch"}, 2: {"Adar": "Agar", "ab": "aap", "seekro": "seekh rahe"},
       3: {"padke": "padh ke"}, 4: {"bulke": "balki"},
       6: {"wad,": "waqt,", "muse": "news", "rhane": "rehna"},
       8: {"palenge,": "padengi,", "palenge": "padengi"},
       10: {"baho": "bahut", "hoon.": "ho."}, 11: {"rut": "ratt", "rag": "RAG"},
       12: {"mai": "main", "dita": "deta"}}
CHIN = {1: .57, 2: .67, 3: .63, 4: .62, 5: .57, 6: .62, 7: .56, 8: .67, 9: .57, 10: .72, 11: .60, 12: .62}
END_OVERRIDE = {5: 10.32}          # Whisper mis-timed clip 5's last word; mouth moves until ~10.25 s
EMPH = {1: [("nahi", "nahi")], 2: [("aspiring", "ho")], 3: [("talented", "hain")],
        4: [("100x", "expectations")], 5: [("race", "race"), ("falls", "engineers")],
        6: [("updated", "hai")], 7: [("personal", "compromise")],
        8: [("raate", "padengi"), ("weekends", "padengi")], 9: [("become", "engineer")],
        10: [("competition", "zyada"), ("crack", "crack")], 11: [("ratt", "ratt"), ("RAG", "tuning")],
        12: [("comments", "comments")]}
# graphics in the top band: (clip, from word, until word or None=clip end, kind, payload, x, y)
STICKERS = [
    (1, "ai", "nahi", "title", (["AI ENGINEER", CYAN], ["SAB THEEK?", WHITE]), "c", 520),
    (1, "nahi", None, "big", ("NAHI!", PINK), "c", 560),
    (4, "100x", None, "title", (["100X", YELLOW], ["EXPECTATIONS", WHITE]), "c", 520),
    (5, "race", "and", "chip", ("THE AI RACE", PINK), "c", 600),
    (5, "falls", None, "chip", ("ALL ON AI ENGINEERS", CYAN), "c", 600),
    (6, "updated", None, "chip", ("24/7 UPDATED", YELLOW), "c", 600),
    (7, "personal", None, "title", (["PERSONAL LIFE", WHITE], ["COMPROMISE", PINK]), "c", 520),
    (8, "raate", None, "chip", ("NIGHTS", CYAN), 140, 600),
    (8, "weekends", None, "chip", ("+ WEEKENDS", PINK), 940, 600),
    (10, "competition", "aur", "big", ("COMPETITION", YELLOW), "c", 580),
    (10, "crack", None, "chip", ("CRACK IT", CYAN), "c", 600),
    (11, "prepare", None, "chip", ("INTERVIEW PREP", PINK), "c", 470),
    (11, "cv", None, "check", ("CV", CYAN), 140, 720),
    (11, "basic", None, "check", ("BASICS", CYAN), 1120, 720),
    (11, "rag", None, "check", ("RAG", YELLOW), 140, 930),
    (11, "fine", None, "check", ("FINE-TUNING", YELLOW), 1120, 930),
    (12, "comments", None, "chip", ("COMMENT BELOW", PINK), "c", 600),
]
CHIN_PIN, SIL, PAD, MAX_SHOT, MIN_SHOT = 0.60, 0.35, 0.08, 1.9, 0.40
grid = lambda t: round(t * FPS) / FPS
norm = lambda w: w.lower().strip(",.?!'\"")
font = lambda s: ImageFont.truetype(str(FONT), px(s))


# ---------------- graphics ----------------------------------------------------------------------
def text_size(t, f):
    b = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), t, font=f)
    return b[2] - b[0], b[3] - b[1], b[0], b[1]


def caption_png(words, emph, path):
    size = 156
    while True:
        f, gap = font(size), px(size * 0.30)
        ws = [(w.upper(), text_size(w.upper(), f)[0]) for w in words]
        total = int(sum(w for _, w in ws) + gap * (len(ws) - 1)) + px(120)
        if total <= W - px(100) or size <= 100:
            break
        size -= 6
    img = Image.new("RGBA", (total, px(250)), (0, 0, 0, 0))
    dr, x = ImageDraw.Draw(img), px(60)
    for (w, wid), raw in zip(ws, words):
        col = YELLOW if norm(raw) in emph else CYAN if norm(raw) in KEYWORDS else WHITE
        dr.text((x + px(8), px(58)), w, font=f, fill=(0, 0, 0, 160))            # hard drop shadow
        dr.text((x, px(50)), w, font=f, fill=col, stroke_width=px(size * 0.11), stroke_fill=BLACK)
        x += wid + gap
    img.save(path)
    return img.size


def sticker_png(kind, payload, path, scale=1.0):
    pad = px(40 * scale)
    if kind in ("title", "big"):
        lines = payload if kind == "title" else [list(payload)]
        sizes = [230, 120] if kind == "title" else [280]
        fs = [font(s * scale) for s in sizes[:len(lines)]]
        dims = [text_size(t, f) for (t, _), f in zip(lines, fs)]
        w = max(d[0] for d in dims) + 2 * pad + px(30)
        h = sum(d[1] for d in dims) + px(40 * scale) * len(lines) + 2 * pad
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dr = ImageDraw.Draw(img); y = pad
        for (t, col), f, d in zip(lines, fs, dims):
            x = (w - d[0]) / 2 - d[2]
            dr.text((x + px(12 * scale), y - d[3] + px(12 * scale)), t, font=f, fill=(0, 0, 0, 170))
            dr.text((x, y - d[3]), t, font=f, fill=col, stroke_width=px(14 * scale), stroke_fill=BLACK)
            y += d[1] + px(40 * scale)
        bar = px(16 * scale)                                     # accent underline
        dr.polygon([(pad, h - pad // 2 - bar), (w - pad, h - pad // 2 - bar), (w - pad - bar, h - pad // 2), (pad - bar, h - pad // 2)],
                   fill=lines[0][1])
    else:
        text, col = payload
        f = font((96 if kind == "check" else 124) * scale); tw, th, ox, oy = text_size(text, f)
        icon = px(110 * scale) if kind == "check" else 0
        w, h = tw + icon + 2 * pad + px(30), th + 2 * pad + px(20)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
        cut = px(34 * scale)                                     # angled tech chip
        poly = [(cut, 0), (w - 1, 0), (w - 1, h - 1 - cut), (w - 1 - cut, h - 1), (0, h - 1), (0, cut)]
        dr.polygon(poly, fill=(8, 8, 14, 225)); dr.line(poly + [poly[0]], fill=col, width=px(8 * scale))
        if kind == "check":
            cx, cy, r = pad + icon / 2 - px(10), h / 2, icon / 2.4
            dr.line([(cx - r, cy), (cx - r * 0.25, cy + r * 0.7), (cx + r, cy - r * 0.8)], fill=col, width=px(16 * scale), joint="curve")
        dr.text((pad + icon - ox, (h - th) / 2 - oy), text, font=f, fill=col)
    img.save(path)
    return img.size


def fit_sticker(kind, payload, path, scale=1.0):
    while True:
        w, h = sticker_png(kind, payload, path, scale)
        if w <= W - px(160) or scale < 0.4:
            return w, h
        scale *= 0.92


def hud_pngs():
    L, T = px(150), px(12)
    for name, ys in (("hud_top", "top"), ("hud_bot", "bot")):
        img = Image.new("RGBA", (W, px(200)), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
        y = px(30) if ys == "top" else px(170) - T
        for x0, sx in ((px(70), 1), (W - px(70), -1)):
            xa, xb = sorted([x0, x0 + sx * L]); dr.rectangle((xa, y, xb, y + T), fill=CYAN + (230,))
            vy = (y, y + L) if ys == "top" else (y + T - L, y + T)
            xa, xb = sorted([x0, x0 + sx * T]); dr.rectangle((xa, vy[0], xb, vy[1]), fill=CYAN + (230,))
        img.save(WORK / f"{name}.png")
    bar = Image.new("RGBA", (W, px(20)))
    for x in range(W):
        a = x / W
        ImageDraw.Draw(bar).line([(x, 0), (x, px(20))], fill=tuple(int(c1 + (c2 - c1) * a) for c1, c2 in zip(CYAN, PINK)) + (255,))
    bar.save(WORK / "progress.png")


# ---------------- geometry (chin pinned so captions sit just below it) -------------------------
def zmin(i):
    return max(1.10, (1 - 0.68) / (1 - CHIN[i]))


def chin_out(i, z):
    return max(CHIN_PIN, z * (CHIN[i] - 1) + 1)


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
        e0 = END_OVERRIDE.get(i, min(words[-1][2], c["speech_end"]) + 0.06)
        clips[i] = dict(words=words, s0=max(0, c["rms_start"] - 0.08), e0=min(e0, c["dur"] - 0.01))
    return clips


def span_idx(words, a, b, start=0):
    ia = next(j for j, w in enumerate(words) if j >= start and norm(w[0]) == norm(a))
    ib = next(j for j, w in enumerate(words) if j >= ia and norm(w[0]) == norm(b)) if b else len(words) - 1
    return ia, ib


def make_shots(clips):
    shots = []
    for i, c in clips.items():
        words = [w for w in c["words"] if w[2] > c["s0"] and w[1] < c["e0"]]
        tag = ["norm"] * len(words)
        for a, b in EMPH.get(i, []):
            ia, ib = span_idx(words, a, b)
            for j in range(ia, ib + 1):
                tag[j] = "emph"
        rms = energy(i)                                          # dead air -> cut (by audio, never mid-word)
        lo, hi = int(c["s0"] * 100), int(c["e0"] * 100)
        thr = 0.10 * np.percentile(rms[lo:hi], 75)
        quiet = rms[lo:hi] < thr
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
            idx = [j for j, w in enumerate(words) if rs <= (w[1] + w[2]) / 2 < re_ + 0.05]
            if not idx:
                runs = [["norm", []]]
            else:
                runs = []
                for j in idx:
                    if runs and runs[-1][0] == tag[j]:
                        runs[-1][1].append(j)
                    else:
                        runs.append([tag[j], [j]])
            out = []                                             # split long runs into ~1.9 s pieces
            for r in runs:
                stack = [r]
                while stack:
                    q = stack.pop(0)
                    if len(q[1]) > 3 and words[q[1][-1]][2] - words[q[1][0]][1] > MAX_SHOT:
                        h = len(q[1]) // 2
                        stack = [[q[0], q[1][:h]], [q[0], q[1][h:]]] + stack
                    else:
                        out.append(q)
            runs, k = out, 0
            dur = lambda r: words[r[1][-1]][2] - words[r[1][0]][1] if r[1] else 1
            while len(runs) > 1:                                 # no flicker: merge shots < MIN_SHOT
                k = next((k for k, r in enumerate(runs) if dur(r) < MIN_SHOT), None)
                if k is None:
                    break
                r = runs[k]
                t = (k + 1 if r[0] == "emph" and k + 1 < len(runs) else k - 1) if k > 0 else 1
                if t >= len(runs):
                    t = k - 1
                lo_, hi_ = sorted((k, t))
                tagm = "emph" if "emph" in (runs[lo_][0], runs[hi_][0]) else "norm"
                runs[lo_:hi_ + 1] = [[tagm, runs[lo_][1] + runs[hi_][1]]]
            bounds = [rs]
            for a, b in zip(runs, runs[1:]):
                ea, sb = words[a[1][-1]][2], words[b[1][0]][1]
                bounds.append(min(max((ea + sb) / 2 if sb > ea else sb, rs + 0.1), re_ - 0.1))
            bounds.append(re_)
            for q, r in enumerate(runs):
                s, e = grid(bounds[q]), grid(bounds[q + 1])
                if e - s < 1 / FPS:
                    continue
                shots.append(dict(clip=i, s=s, d=e - s, tag=r[0], first=first, gap_before=(q == 0),
                                  words=[words[j] for j in r[1]], allwords=words))
                first = False
    t, flip = 0.0, 0
    for k, sh in enumerate(shots):
        sh["t"] = t; t += sh["d"]
        z0 = zmin(sh["clip"])
        if sh["tag"] == "emph":
            sh["z"] = min(z0 + 0.28, 1.7)
        else:
            sh["z"] = z0 + (0.0 if flip % 2 == 0 else 0.12); flip += 1
        sh["gap_after"] = k + 1 == len(shots) or shots[k + 1]["gap_before"]
    return shots, t


# ---------------- rendering ---------------------------------------------------------------------
def overlays(sh, k):
    i, s, d = sh["clip"], sh["s"], sh["d"]
    ov = []
    # stickers active in this shot
    for n, (ci, a, b, kind, payload, x, y) in enumerate(STICKERS):
        if ci != i:
            continue
        ws = sh["allwords"]
        ia, ib = span_idx(ws, a, b)
        ta = ws[ia][1] - 0.02
        tb = ws[ib][1] - 0.02 if b else 1e9
        t0, t1 = max(0, ta - s), min(d, tb - s)
        if t1 <= 0 or t0 >= d:
            continue
        p = WORK / f"st_{n}.png"
        w, h = fit_sticker(kind, payload, p)
        sc = 1.0
        while sticker_png(kind, payload, WORK / 'tmp.png', sc)[0] > w: sc *= 0.92
        xx = f"({W}-{w})/2" if x == "c" else px(x)
        if ta >= s:                                              # pop: 3 frames bigger, then settle
            pp = WORK / f"st_{n}_pop.png"
            w2, h2 = sticker_png(kind, payload, pp, scale=sc * 1.12)
            xx2 = f"({W}-{w2})/2" if x == "c" else px(x) - (w2 - w) // 2
            ov.append(dict(png=pp, x=xx2, y=px(y) - (h2 - h) // 2, t0=t0, t1=min(t1, t0 + 0.1)))
            ov.append(dict(png=p, x=xx, y=px(y), t0=t0 + 0.1, t1=t1))
        else:
            ov.append(dict(png=p, x=xx, y=px(y), t0=t0, t1=t1))
    # captions
    emph = {norm(w[0]) for w in sh["words"]} if sh["tag"] == "emph" else set()
    chunks, cur = [], []
    for w in sh["words"]:
        cur.append(w)
        if len(cur) == 3 or len(" ".join(x[0] for x in cur)) > 15 or w[0][-1] in ".,?!":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    y = px(int(chin_out(i, sh["z"]) * 3840 + 40))
    for j, ch in enumerate(chunks):
        t0 = 0 if j == 0 else max(0, ch[0][1] - s - 0.03)
        t1 = chunks[j + 1][0][1] - s - 0.03 if j + 1 < len(chunks) else d
        p = WORK / f"cap_{k}_{j}.png"
        w, _ = caption_png([x[0] for x in ch], emph, p)
        ov.append(dict(png=p, x=f"({W}-{w})/2", y=y, t0=t0, t1=t1))
    return ov


def render_shot(k, sh, total):
    i, d = sh["clip"], sh["d"]
    ys = f"min(max(ih*{CHIN[i]}-{CHIN_PIN * H:.1f},0),ih-{H})"
    glitch = (sh["first"] and i > 1) or sh["tag"] == "emph"
    f = [f"[0:v]fps={FPS},scale=w='{W}*{sh['z']:.3f}':h=-2:flags=lanczos,crop={W}:{H}:x='(iw-{W})/2':y='{ys}',"
         f"eq=contrast=1.07:saturation=1.15,unsharp=5:5:0.5,setsar=1"
         + (f",rgbashift=rh=-{px(26)}:bh={px(26)}:enable='lt(t,0.07)'" if glitch else "") + "[v0]"]
    inputs = ["-ss", f"{sh['s']:.3f}", "-t", f"{d:.3f}", "-i", SRC / f"{i}.mp4"]
    fixed = [dict(png=WORK / "hud_top.png", x=0, y=px(400), t0=0, t1=d),
             dict(png=WORK / "hud_bot.png", x=0, y=px(3060), t0=0, t1=d)]
    last, n = "v0", 1
    for o in fixed + overlays(sh, k):
        inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", o["png"]]
        f.append(f"[{last}][{n}:v]overlay=x={o['x']}:y={o['y']}:enable='between(t,{o['t0']:.3f},{o['t1']:.3f})'[o{n}]")
        last = f"o{n}"; n += 1
    inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", WORK / "progress.png"]
    f.append(f"[{last}][{n}:v]overlay=x='-{W}+{W}*({sh['t']:.3f}+t)/{total:.3f}':y=0[pb]")
    f.append("[pb]scale=in_range=auto:out_range=tv,format=yuv420p[fin]")
    out = WORK / f"shot_{k:02d}{'_p' if br.PREVIEW else ''}.mp4"
    br.run(inputs + ["-filter_complex", ";".join(f), "-map", "[fin]", "-t", f"{d:.3f}", "-r", FPS, "-an",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", 22 if br.PREVIEW else 16,
                     "-pix_fmt", "yuv420p", "-g", 60, "-colorspace", "bt709", "-color_primaries", "bt709",
                     "-color_trc", "bt709", out])
    return out


def sfx(shots, total, path):
    sr = 48000; buf = np.zeros(int((total + 0.6) * sr)); rng = np.random.default_rng(3)

    def add(t, y):
        a = int(max(0, t) * sr); buf[a:a + len(y)] += y[:max(0, len(buf) - a)]

    def whoosh(dur=0.22, g=0.18):
        n = int(dur * sr); x = np.arange(n) / sr
        return (np.sin(2 * np.pi * np.cumsum(300 * 10 ** (x / dur)) / sr) * 0.5 + rng.standard_normal(n) * 0.25) \
            * np.sin(np.pi * x / dur) ** 2 * g

    def pop(g=0.30):
        n = int(0.12 * sr); x = np.arange(n) / sr
        return np.sin(2 * np.pi * (900 - 2500 * x) * x) * np.exp(-x * 40) * g

    for sh in shots:
        if sh["first"] and sh["clip"] > 1:
            add(sh["t"] - 0.11, whoosh())
    for sh in shots:                                             # pop when a sticker lands
        for (ci, a, b, kind, payload, x, y) in STICKERS:
            if ci == sh["clip"]:
                ia, _ = span_idx(sh["allwords"], a, b)
                ta = sh["allwords"][ia][1] - 0.02
                if sh["s"] <= ta < sh["s"] + sh["d"]:
                    add(sh["t"] + ta - sh["s"], pop())
    st = (np.clip(buf, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(sr); wv.writeframes(np.repeat(st, 2).tobytes())


def build_audio(shots, total):
    inp, parts = [], []
    for k, sh in enumerate(shots):
        inp += ["-ss", f"{sh['s']:.3f}", "-t", f"{sh['d']:.3f}", "-i", SRC / f"{sh['clip']}.mp4"]
        fx = (",afade=t=in:d=0.008" if sh["gap_before"] else "") + \
             (f",afade=t=out:st={sh['d'] - 0.008:.3f}:d=0.008" if sh["gap_after"] else "")
        parts.append(f"[{k}:a]aresample=48000{fx}[a{k}]")
    p = WORK / "sfx.wav"; sfx(shots, total, p); inp += ["-i", p]
    chain = "".join(f"[a{k}]" for k in range(len(shots)))
    g = (";".join(parts) + f";{chain}concat=n={len(shots)}:v=0:a=1,aformat=channel_layouts=stereo[v];"
         f"[{len(shots)}:a]aformat=channel_layouts=stereo[s];[v][s]amix=inputs=2:normalize=0:duration=first,"
         "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    out = WORK / "voice_mix.m4a"
    br.run(inp + ["-filter_complex", g, "-map", "[a]", "-c:a", "aac", "-b:a", "256k", "-ar", 48000, out])
    return out


def main():
    WORK.mkdir(exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    hud_pngs()
    shots, total = make_shots(load())
    print(f"{len(shots)} shots, {total:.2f}s", flush=True)
    files = []
    for k, sh in enumerate(shots):
        print(f"shot {k} clip {sh['clip']} {sh['tag']} {sh['d']:.2f}s z={sh['z']:.2f}  " + " ".join(w[0] for w in sh["words"]), flush=True)
        files.append(render_shot(k, sh, total))
    audio = build_audio(shots, total)
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in files))
    final = WORK / f"{VIDEO}_preview.mp4" if br.PREVIEW else OUT / f"{VIDEO}_reel_4k.mp4"
    br.run(["-f", "concat", "-safe", 0, "-i", lst, "-i", audio, "-c:v", "copy", "-c:a", "copy",
            "-shortest", "-movflags", "+faststart", final])
    print("done", final)


if __name__ == "__main__":
    main()
