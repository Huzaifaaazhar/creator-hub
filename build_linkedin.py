"""LinkedIn-posts reel: 8 talking-head clips -> sharp jump cuts, instant punch zooms, captions,
LinkedIn-style icon cards + whoosh/impact sound design.  9:16, 2160x3840.

Usage:  python build_linkedin.py [--preview]
Needs:  media/linkedin_posts/work/words.json  (made by analyze.py + words_fix.py)
Output: media/upload_ready/4k/linkedin_posts_reel_4k.mp4  (preview -> media/linkedin_posts/work/)
Reuses the caption/ffmpeg helpers in build_reel.py.
"""
import json, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build_reel as br

VIDEO = "linkedin_posts"
W, H, FPS, px = br.W, br.H, br.FPS, br.px
SRC = br.ROOT / "media" / VIDEO
WORK = SRC / "work"
OUT = br.ROOT / "media/upload_ready/4k"

# ---- LinkedIn look -------------------------------------------------------------------------
BLUE, NAVY, WHITE, RED = (10, 102, 194), (10, 25, 41), (255, 255, 255), (214, 48, 49)
KEY = (86, 176, 255)                      # light LinkedIn blue for highlighted caption words
br.GOLD = KEY
br.KEYWORDS = {"linkedin", "recruiters", "hire", "ai", "automation", "post", "posting", "unnecessary",
               "scroll", "achievements", "projects", "business", "outcome", "regularly", "quality",
               "quantity", "reel", "especially", "instagram", "insta"}
F_BOLD, F_BLACK = "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/ariblk.ttf"
font = lambda p, s: ImageFont.truetype(p, px(s))

# caption fixes for unclear transcription (checked by ear is not possible - see notes to user)
FIX = {2: {"cheeze": "cheezein", "gayi": "gayi", "raha": "raha"},
       3: {"SMA": "Especially"},
       4: {"To": "So", "nut": "minute", "karthe": "karte"}}
CARD = {1: ("in", "RECRUITERS ARE WATCHING"), 2: ("in", "EVERYONE POSTS AI AUTOMATION"),
        3: ("x", "POSTING JUST TO POST"), 4: ("scroll", "SCROLLED PAST IN SECONDS"),
        5: ("check", "POST YOUR WINS"), 6: ("chart", "BUSINESS OUTCOME > TECH"),
        7: ("cal", "NO NEED TO POST DAILY"), 8: ("star", "QUALITY > QUANTITY")}
ZOOMS = [1.0, 1.26, 1.08, 1.34, 1.0, 1.2, 1.3, 1.06]   # instant punch-in / punch-out cycle
FACE_Y, GAP, TARGET = 0.42, 0.30, 1.25
grid = lambda t: round(t * FPS) / FPS


# ---- icons / widgets -----------------------------------------------------------------------
def draw_icon(dr, kind, cx, cy, r, fg=WHITE):
    k, lw = r / 100.0, int(r * 0.16)
    P = lambda pts: [(cx + x * k, cy + y * k) for x, y in pts]
    if kind == "x":
        dr.line(P([(-45, -45), (45, 45)]), fill=fg, width=lw); dr.line(P([(-45, 45), (45, -45)]), fill=fg, width=lw)
    elif kind == "scroll":
        for dy in (-28, 22):
            dr.line(P([(-45, dy - 10), (0, dy + 30), (45, dy - 10)]), fill=fg, width=lw, joint="curve")
    elif kind == "check":
        dr.line(P([(-48, 5), (-12, 42), (50, -38)]), fill=fg, width=lw, joint="curve")
    elif kind == "chart":
        for i, (x, top) in enumerate(((-45, 10), (-10, -20), (25, -52))):
            dr.rectangle(P([(x, top), (x + 24, 50)])[0] + P([(x, top), (x + 24, 50)])[1], fill=fg)
    elif kind == "cal":
        dr.rounded_rectangle(P([(-50, -38), (50, 50)])[0] + P([(-50, -38), (50, 50)])[1], r * 0.12, outline=fg, width=lw)
        dr.line(P([(-50, -8), (50, -8)]), fill=fg, width=lw)
        for x in (-25, 25):
            dr.line(P([(x, -58), (x, -28)]), fill=fg, width=lw)
        dr.line(P([(-62, 62), (62, -62)]), fill=RED, width=lw)
    elif kind == "star":
        import math
        pts = [(cx + r * (0.8 if i % 2 == 0 else 0.33) * math.sin(i * math.pi / 5),
                cy - r * (0.8 if i % 2 == 0 else 0.33) * math.cos(i * math.pi / 5)) for i in range(10)]
        dr.polygon(pts, fill=fg)


def logo(dr, x, y, size):
    """LinkedIn-style 'in' square."""
    dr.rounded_rectangle((x, y, x + size, y + size), size * 0.18, fill=BLUE)
    f = ImageFont.truetype(F_BLACK, int(size * 0.62))
    t = "in"; tw = dr.textlength(t, font=f)
    dr.text((x + (size - tw) / 2 - size * 0.02, y + size * 0.12), t, font=f, fill=WHITE)


def card_png(kind, text, path):
    f = font(F_BOLD, 88)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    h = px(230)
    w = h + int(d.textlength(text, font=f)) + px(80)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((0, 0, w - 1, h - 1), px(46), fill=NAVY + (235,), outline=BLUE, width=px(7))
    pad = px(22)
    if kind == "in":
        logo(dr, pad, pad, h - 2 * pad)
    else:
        col = RED if kind in ("x", "scroll") else BLUE
        dr.ellipse((pad, pad, h - pad, h - pad), fill=col)
        draw_icon(dr, kind, h / 2, h / 2, (h - 2 * pad) / 2)
    dr.text((h + px(8), h / 2 - px(62)), text, font=f, fill=WHITE)
    img.save(path)
    return img.size


def caption_png(words, path):
    """white outlined caption, key words blue; font shrinks so the chunk always fits the frame"""
    size = 150
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    while True:
        f, gap = font(F_BLACK, size), px(size * 0.22)
        ws = [(w.upper(), d.textlength(w.upper(), font=f)) for w in words]
        total = int(sum(w for _, w in ws) + gap * (len(ws) - 1)) + px(120)
        if total <= W - px(80) or size <= 90:
            break
        size -= 6
    img = Image.new("RGBA", (total, px(260)), (0, 0, 0, 0))
    dr, x = ImageDraw.Draw(img), px(60)
    for w, wid in ws:
        key = w.lower().strip(".,?!'\"") in br.KEYWORDS
        dr.text((x, px(50)), w, font=f, fill=KEY if key else WHITE, stroke_width=px(size * 0.08), stroke_fill=(10, 8, 6, 255))
        x += wid + gap
    img.save(path)
    return img.size


# ---- shots: tight cuts + zoom cycle --------------------------------------------------------
def load():
    data = json.load(open(WORK / "words.json"))
    clips = {}
    for i in range(1, 9):
        c = data[str(i)]
        words = [(FIX.get(i, {}).get(w, w), s, e) for w, s, e in c["words"]]
        clips[i] = dict(words=words, s0=max(0, c["rms_start"] - 0.05),
                        e0=min(words[-1][2] + 0.05, c["rms_end"] + 0.02))
    return clips


def make_shots(clips):
    shots, n = [], 0
    for i, c in clips.items():
        words = [w for w in c["words"] if w[2] > c["s0"] and w[1] < c["e0"]]
        ranges, cur = [], c["s0"]
        for a, b in zip(words, words[1:]):                      # drop dead air between words
            if b[1] - a[2] >= GAP:
                ranges.append((cur, a[2] + 0.07)); cur = b[1] - 0.05
        ranges.append((cur, c["e0"]))
        first = True
        for (rs, re_) in ranges:
            rw = [w for w in words if rs <= (w[1] + w[2]) / 2 and w[1] < re_]
            cuts, last = [rs], rs                                  # split long runs at word boundaries
            for a, b in zip(rw, rw[1:]):
                if b[1] - last >= TARGET and re_ - b[1] >= 0.6:
                    cut = (a[2] + b[1]) / 2 if b[1] > a[2] else b[1] - 0.01
                    cuts.append(cut); last = cut
            cuts.append(re_)
            for k, (a, b) in enumerate(zip(cuts, cuts[1:])):
                s, e = grid(a), grid(b)
                shots.append(dict(clip=i, s=s, d=e - s, z=ZOOMS[n % len(ZOOMS)], first=first,
                                  drift=0.14 if (i == 1 and first) else 0.04, gap_before=(k == 0),
                                  words=[w for w in rw if s <= (w[1] + w[2]) / 2 and (k == len(cuts) - 2 or (w[1] + w[2]) / 2 < e)]))
                n += 1; first = False
    t = 0
    for sh in shots:
        sh["t"] = t; t += sh["d"]
    for k, sh in enumerate(shots):                                 # last shot of each clip -> widget end
        sh["clip_last"] = k + 1 == len(shots) or shots[k + 1]["clip"] != sh["clip"]
        sh["gap_after"] = sh["clip_last"] or shots[k + 1]["gap_before"]
    return shots


def captions(sh, k):
    ov, chunks, cur = [], [], []
    for w in sh["words"]:
        cur.append(w)
        if len(cur) == 3 or w[0][-1] in ".,?!":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    for j, ch in enumerate(chunks):
        t0 = 0 if j == 0 else max(0, ch[0][1] - sh["s"] - 0.03)
        t1 = chunks[j + 1][0][1] - sh["s"] - 0.03 if j + 1 < len(chunks) else sh["d"]
        p = WORK / f"cap_{k}_{j}.png"
        w, _ = caption_png([x[0] for x in ch], p)
        ov.append(dict(png=p, x=f"({W}-{w})/2", y=px(2330), t0=t0, t1=t1, slide=0))
    return ov


def render_shot(k, sh):
    d, i = sh["d"], sh["clip"]
    z = f"({sh['z']}*(1+{sh['drift']}*min(t/{d:.3f},1)))"
    f = [f"[0:v]fps={FPS},scale=w='{W}*{z}':h=-2:eval=frame:flags=lanczos,"
         f"crop={W}:{H}:x='(iw-{W})/2':y='min(max(ih*{FACE_Y}-{H}/2,0),ih-{H})',"
         f"eq=contrast=1.05:saturation=1.1,unsharp=5:5:0.5,setsar=1[base]"]
    kind, text = CARD[i]
    cp = WORK / f"card_{i}.png"
    if not cp.exists() or sh["first"]:
        card_png(kind, text, cp)
    widgets = [dict(png=cp, x=px(100), y=px(560), t0=0.08 if sh["first"] else -1, t1=d, slide=60)]
    ovs, inputs = widgets + captions(sh, k), ["-ss", f"{sh['s']:.3f}", "-t", f"{d:.3f}", "-i", SRC / f"{i}.mp4"]
    last = "base"
    for j, o in enumerate(ovs):
        inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", o["png"]]
        t0, t1 = o["t0"], o["t1"]
        f.append(f"[{j + 1}:v]format=rgba,fade=t=in:st={max(t0, 0):.3f}:d={0.12 if t0 >= 0 else 0.001}:alpha=1[w{j}]")
        yy = f"{o['y']}+{px(o['slide'])}*(1-min(1,max(0,(t-{t0:.3f}))/0.2))" if o["slide"] else str(o["y"])
        f.append(f"[{last}][w{j}]overlay=x={o['x']}:y='{yy}':enable='between(t,{t0:.3f},{t1:.3f})'[o{j}]")
        last = f"o{j}"
    f.append(f"[{last}]scale=in_range=auto:out_range=tv,format=yuv420p[fin]")
    out = WORK / f"shot_{k:02d}{'_p' if br.PREVIEW else ''}.mp4"
    br.run(inputs + ["-filter_complex", ";".join(f), "-map", "[fin]", "-t", f"{d:.3f}", "-r", FPS, "-an",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", 22 if br.PREVIEW else 16,
                     "-pix_fmt", "yuv420p", "-g", 60, "-colorspace", "bt709", "-color_primaries", "bt709",
                     "-color_trc", "bt709", out])
    return out


# ---- audio: voice + whoosh / impact --------------------------------------------------------
def sfx_track(shots, total, path):
    sr = 48000
    buf = np.zeros(int((total + 0.5) * sr))
    rng = np.random.default_rng(7)

    def whoosh(t, dur=0.32, gain=0.30):
        n = int(dur * sr); x = np.arange(n) / sr
        sweep = np.sin(2 * np.pi * np.cumsum(180 * (14 ** (x / dur))) / sr)      # rising chirp
        env = np.sin(np.pi * np.clip(x / dur, 0, 1)) ** 2
        y = (0.6 * sweep + 0.4 * rng.standard_normal(n) * 0.5) * env * gain
        a = int(max(0, t) * sr); buf[a:a + n] += y[:max(0, len(buf) - a)][:n]

    def impact(t, dur=0.35, gain=0.55):
        n = int(dur * sr); x = np.arange(n) / sr
        y = np.sin(2 * np.pi * (55 + 90 * np.exp(-x * 25)) * x) * np.exp(-x * 9) * gain
        a = int(t * sr); buf[a:a + n] += y[:len(buf) - a]

    impact(0.0)
    for sh in shots:
        if sh["first"] and sh["clip"] > 1:
            whoosh(sh["t"] - 0.14)
    pk = np.abs(buf).max() or 1
    st = (np.clip(buf / max(pk, 1.0), -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(sr)
        wv.writeframes(np.repeat(st, 2).tobytes())


def build_audio(shots, total):
    inp, parts = [], []
    for k, sh in enumerate(shots):
        inp += ["-ss", f"{sh['s']:.3f}", "-t", f"{sh['d']:.3f}", "-i", SRC / f"{sh['clip']}.mp4"]
        fx = ""
        if sh["gap_before"]:
            fx += ",afade=t=in:d=0.008"
        if sh["gap_after"]:
            fx += f",afade=t=out:st={sh['d'] - 0.008:.3f}:d=0.008"
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
        print(f"shot {k} clip {sh['clip']} {sh['d']:.2f}s zoom {sh['z']}", flush=True)
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
