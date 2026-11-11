"""Grimyapper reel: talking-head clips 1-9 + fast-forwarded app tutorial -> 9:16 4K (2160x3840).

Usage:  python build_reel.py [--preview]     (preview = 1080x1920, quick check)
Output: media/upload_ready/4k/grimyapper_reel_4k.mp4  (preview goes to media/grimyapper/work/)
"""
import json, subprocess, sys
from pathlib import Path
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

PREVIEW = "--preview" in sys.argv
S = 0.5 if PREVIEW else 1.0            # all layout numbers below are in 4K pixels
W, H, FPS = int(2160 * S), int(3840 * S), 30
ROOT = Path(__file__).parent
VIDEO = "grimyapper"                    # folder name under media/ for this reel
MEDIA = ROOT / "media" / VIDEO
WORK = MEDIA / "work"                 # all scratch files live with the video
OUT = ROOT / "media/upload_ready/4k"  # final 4K cuts always go here
FF = imageio_ffmpeg.get_ffmpeg_exe()
px = lambda v: int(round(v * S))

GOLD, CRIMSON, CREAM, INK = (201, 162, 39), (139, 30, 30), (243, 230, 200), (28, 18, 14)
KEYWORDS = {"startup", "succeed", "web", "app", "worth", "building", "link", "rate", "success",
            "medieval", "certificate", "comment", "idea", "scale"}
F_BLACK, F_SERIF = "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/georgiab.ttf"
font = lambda path, size: ImageFont.truetype(path, px(size))

# tutorial window (seconds in app_tutorial.mp4) shown during each clip 3..8
TUT = {3: (0, 5), 4: (8, 26), 5: (33, 43), 6: (43, 52), 7: (52, 72), 8: (72, 85)}
STEP = {3: "OPEN THE LINK", 4: "DESCRIBE YOUR IDEA", 5: "GET A SUCCESS SCORE",
        6: "WORTH BUILDING?", 7: "MEDIEVAL STYLE", 8: "CERTIFICATE OF SUCCESS"}
# measured from the audio energy of each clip (media/grimyapper/work/ends.py): when sound starts / stops
SPEECH_START = {1: 0.15, 6: 0.18, 7: 0.11, 9: 0.06}
SPEECH_END = {1: 4.26, 2: 4.48, 3: 1.12, 4: 1.41, 5: 2.40, 6: 2.86, 7: 1.89, 8: 3.96, 9: 3.00}
FACE_Y = {1: 0.44, 2: 0.44, 9: 0.44}   # vertical anchor of the face for zoom framing


def run(args):
    r = subprocess.run([FF, "-v", "error", "-y", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-2000:])


# ---------- timing: trim each clip tight around its words ----------
def load_clips():
    tr = json.load(open(WORK / "transcripts.json"))
    clips = {}
    for i in range(1, 10):
        words = tr[str(i)]["words"]
        s = max(0, SPEECH_START.get(i, 0) - 0.04)         # first audible sound
        e = min(words[-1][2] + 0.05, SPEECH_END[i] + 0.02)  # cut before the reach for the stop button
        d = round((e - s) * FPS) / FPS
        clips[i] = dict(s=s, d=d, words=[(w, max(0, a - s), max(0.05, b - s)) for w, a, b in words])
    return clips


# ---------- widget / caption images ----------
def text_w(draw, t, f):
    return draw.textlength(t, font=f)


def caption_png(words, path):
    f = font(F_BLACK, 150)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    gap = px(34)
    ws = [(w.upper(), text_w(d, w.upper(), f)) for w in words]
    total = int(sum(w for _, w in ws) + gap * (len(ws) - 1)) + px(120)
    img = Image.new("RGBA", (total, px(260)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    x = px(60)
    for w, wid in ws:
        key = w.lower().strip(".,?!'\"") in KEYWORDS
        dr.text((x, px(50)), w, font=f, fill=GOLD if key else (255, 255, 255, 255),
                stroke_width=px(12), stroke_fill=(15, 10, 8, 255))
        x += wid + gap
    img.save(path)
    return img.size


def card_png(num, text, path):
    f, fn = font(F_SERIF, 66), font(F_SERIF, 84)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tw = int(text_w(d, text, f))
    h, bd = px(170), px(170)
    w = bd + px(40) + tw + px(70)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((0, 0, w - 1, h - 1), px(40), fill=INK + (230,), outline=GOLD, width=px(6))
    dr.ellipse((px(18), px(18), bd - px(18), h - px(18)), fill=CRIMSON, outline=GOLD, width=px(4))
    nw = text_w(dr, str(num), fn)
    dr.text(((bd - nw) / 2, h / 2 - px(52)), str(num), font=fn, fill=CREAM)
    dr.text((bd + px(20), h / 2 - px(40)), text, font=f, fill=CREAM)
    img.save(path)
    return img.size


def pill_png(text, path, size=58, fill=INK + (225,), color=GOLD, arrows=0):
    f = font(F_SERIF, size)
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    ah = px(size * 1.0) if arrows else 0
    tw = int(text_w(d, text, f))
    w, h = tw + ah + px(100), px(size + 80)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=fill, outline=GOLD, width=px(5))
    x = px(50)
    for k in range(arrows):            # fast-forward triangles
        a = ah // 2 + px(6)
        cx = x + k * (a - px(4))
        dr.polygon([(cx, h / 2 - a / 2), (cx, h / 2 + a / 2), (cx + a, h / 2)], fill=color)
    dr.text((px(50) + ah, h / 2 - px(size * 0.62)), text, font=f, fill=color)
    img.save(path)
    return img.size


def cta_png(path):
    f1, f2 = font(F_BLACK, 110), font(F_SERIF, 64)
    w, h = px(1600), px(520)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    stroke = dict(stroke_width=px(12), stroke_fill=(15, 10, 8, 255))   # no box, outlined text only
    for t, f, y, c in (("COMMENT BELOW", f1, 20, (255, 255, 255)), ("FOR THE LINK", f1, 150, GOLD)):
        dr.text(((w - text_w(dr, t, f)) / 2, px(y)), t, font=f, fill=c, **stroke)
    cx, y0 = w // 2, px(330)           # down arrow
    dr.polygon([(cx - px(70), y0), (cx + px(70), y0), (cx, y0 + px(100))], fill=CRIMSON, outline=(15, 10, 8), width=px(6))
    img.save(path)
    return img.size


def ring_and_mask(d, ring, mask):
    big = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    ImageDraw.Draw(big).ellipse((px(4), px(4), d - px(4), d - px(4)), outline=GOLD, width=px(14))
    big.save(ring)
    m = Image.new("L", (d, d), 0)
    ImageDraw.Draw(m).ellipse((px(7), px(7), d - px(7), d - px(7)), fill=255)
    m.save(mask)


# ---------- segment rendering ----------
def caption_overlays(i, c):
    """one overlay per 1-3 word chunk, timed to the speech"""
    chunks, cur = [], []
    for w in c["words"]:
        cur.append(w)
        if len(cur) == 3 or w[0][-1] in ".,?!":
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    ov = []
    for k, ch in enumerate(chunks):
        t0 = max(0, ch[0][1] - 0.04)
        t1 = chunks[k + 1][0][1] - 0.04 if k + 1 < len(chunks) else c["d"]
        p = WORK / f"cap_{i}_{k}.png"
        w, h = caption_png([x[0] for x in ch], p)
        ov.append(dict(png=p, x=f"(W-{w})/2", y=px(2330), t0=t0, t1=t1, slide=0, pop=True))
    return ov


def render_segment(i, c, widgets, face_mode):
    d = c["d"]
    inputs = ["-ss", f"{c['s']:.3f}", "-t", f"{d:.3f}", "-i", MEDIA / f"{i}.mp4"]   # [0] face clip
    f = []
    if face_mode:
        z0, z1 = {1: (1.0, 1.28), 2: (1.14, 1.0), 9: (1.0, 1.12)}[i]
        fy = FACE_Y[i]
        zexpr = f"({z0}+({z1}-{z0})*min(t/{d:.3f},1))"
        f.append(f"[0:v]fps={FPS},scale=w='{W}*{zexpr}':h=-2:eval=frame:flags=lanczos,"
                 f"crop={W}:{H}:x='(iw-{W})/2':y='min(max(ih*{fy}-{H}/2,0),ih-{H})',setsar=1[base]")
        nxt = 1
    else:
        a, b = TUT[i]
        inputs += ["-ss", a, "-t", b - a, "-i", MEDIA / "app_tutorial.mp4"]          # [1] tutorial
        dia = px(560)
        ring_and_mask(dia, WORK / "ring.png", WORK / "mask.png")
        inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", WORK / "mask.png"]            # [2] mask
        inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", WORK / "ring.png"]            # [3] ring
        speed = (b - a) / d
        f.append(f"[1:v]setpts=PTS*{d / (b - a):.5f},fps={FPS},scale={W}:-2:flags=lanczos,"
                 f"crop={W}:{H}:0:0,setsar=1[base]")
        f.append(f"[0:v]fps={FPS},crop=1000:1000:40:450,scale={dia}:{dia}:flags=lanczos,format=rgba[fc]")
        f.append("[2:v]format=gray[m];[fc][m]alphamerge[face]")
        f.append(f"[base][face]overlay=x={W - px(100) - dia}:y={px(600)}[b1]")
        f.append(f"[b1][3:v]overlay=x={W - px(100) - dia}:y={px(600)}[base]")
        nxt = 4
        wp = WORK / f"speed_{i}.png"
        sw, sh = pill_png(f"{speed:.1f}x FAST FORWARD", wp, size=52, arrows=2)
        widgets = widgets + [dict(png=wp, x=px(100), y=px(800), t0=0.1, t1=d, slide=40)]
    last = "base"
    for k, o in enumerate(widgets + caption_overlays(i, c)):
        inputs += ["-loop", 1, "-t", f"{d:.3f}", "-i", o["png"]]
        t0, t1 = o["t0"], o["t1"]
        f.append(f"[{nxt + k}:v]format=rgba,fade=t=in:st={t0:.3f}:d=0.18:alpha=1[w{k}]")
        yy = f"{o['y']}+{px(o.get('slide', 0))}*(1-min(1,(t-{t0:.3f})/0.22))"
        f.append(f"[{last}][w{k}]overlay=x={o['x']}:y='{yy}':enable='between(t,{t0:.3f},{t1:.3f})'[o{k}]")
        last = f"o{k}"
    f.append(f"[{last}]scale=in_range=auto:out_range=tv,format=yuv420p[fin]"); last = "fin"
    out = WORK / f"seg_{i}{'_p' if PREVIEW else ''}.mp4"
    run(inputs + ["-filter_complex", ";".join(f).replace("(W-", f"({W}-"), "-map", f"[{last}]",
         "-t", f"{d:.3f}", "-r", FPS, "-an", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", 22 if PREVIEW else 16, "-pix_fmt", "yuv420p", "-g", 60,
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", out])
    return out


def build_audio(clips):
    inp, parts = [], []
    for i, c in clips.items():
        inp += ["-ss", f"{c['s']:.3f}", "-t", f"{c['d']:.3f}", "-i", MEDIA / f"{i}.mp4"]
        parts.append(f"[{i - 1}:a]aresample=48000,afade=t=in:d=0.015,"
                     f"afade=t=out:st={c['d'] - 0.015:.3f}:d=0.015[a{i}]")
    chain = "".join(f"[a{i}]" for i in clips)
    g = ";".join(parts) + f";{chain}concat=n=9:v=0:a=1,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    out = WORK / "voice.m4a"
    run(inp + ["-filter_complex", g, "-map", "[a]", "-c:a", "aac", "-b:a", "256k", "-ar", 48000, out])
    return out


def main():
    WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    clips = load_clips()
    w = {}
    def add(i, p, x, y, t0=0.15, slide=50): w.setdefault(i, []).append(dict(png=p, x=x, y=y, t0=t0, t1=clips[i]["d"], slide=slide))

    p = WORK / "w1.png"; pill_png("STARTUP REALITY CHECK", p, size=66); add(1, p, px(100), px(600))
    p = WORK / "w2.png"; pill_png("GRIMYAPPER  -  ASSAYER OF VENTURES", p, size=52); add(2, p, px(100), px(600))
    for i in range(3, 9):
        p = WORK / f"w{i}.png"; card_png(i - 2, STEP[i], p); add(i, p, px(100), px(600))
    p = WORK / "w9.png"; cta_png(p); add(9, p, f"({W}-{px(1600)})/2", px(500), slide=80)

    segs = []
    for i, c in clips.items():
        print("segment", i, f"{c['d']:.2f}s", flush=True)
        segs.append(render_segment(i, c, w.get(i, []), face_mode=i in (1, 2, 9)))
    audio = build_audio(clips)
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs))
    final = WORK / f"{VIDEO}_preview.mp4" if PREVIEW else OUT / f"{VIDEO}_reel_4k.mp4"
    run(["-f", "concat", "-safe", 0, "-i", lst, "-i", audio, "-c:v", "copy", "-c:a", "copy",
         "-shortest", "-movflags", "+faststart", final])
    print("done", final)


if __name__ == "__main__":
    main()
