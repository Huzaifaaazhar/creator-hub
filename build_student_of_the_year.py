"""Student of the Year reel: voice clips 1m-10m + gameplay clips -> 9:16 4K.

Pipeline (Remotion does the graphics, ffmpeg does the heavy video):
  plan      voice timeline + shots -> reels-remotion/src/soy/edit.json (captions, stickers) + low-res preview cut
  base      4K base cut (voice-synced, gameplay sped up to match speech, face shots with the chin pinned)
  final     base + Remotion overlay PNG sequence + mixed audio -> media/upload_ready/4k/

Usage:  python build_student_of_the_year.py plan|base|final
"""
import json, subprocess, sys, wave
from pathlib import Path
import av
import imageio_ffmpeg
import numpy as np

ROOT = Path(__file__).parent
SRC = ROOT / "media" / "student_of_the_year"
WORK = SRC / "work"
REMO = ROOT / "reels-remotion"
OUT = ROOT / "media/upload_ready/4k"
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
MODE = sys.argv[1] if len(sys.argv) > 1 else "plan"
PREVIEW = MODE == "plan"                         # plan also renders the small preview base
W, H = (540, 960) if PREVIEW else (2160, 3840)
SIL, PAD, PAUSE = 0.38, 0.07, 1.8                # dead-air cut threshold, padding, scripted counter pause (s)
CHIN = {1: .62, 2: .64, 3: .62, 4: .62, 5: .62, 6: .62, 7: .65, 8: .62, 9: .64, 10: .66}
CHIN_PIN = 0.60
FIX = {2: {"their": "the Year"}, 5: {"learned": "learns,"}}
grid = lambda t: round(t * FPS) / FPS
norm = lambda w: w.lower().strip(",.?!'\"")


def run(args):
    r = subprocess.run([FF, "-v", "error", "-y", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-2500:])


def energy(i):
    c = av.open(str(SRC / f"{i}m.mp4")); r = av.AudioResampler(format="s16", layout="mono", rate=16000)
    x = np.concatenate([q.to_ndarray().ravel() for fr in c.decode(audio=0) for q in r.resample(fr)]).astype(float)
    return np.sqrt(np.convolve(x ** 2, np.ones(160) / 160, "same")[::160])


# ---------------- voice timeline ----------------------------------------------------------------
def build_voice():
    data = json.load(open(WORK / "words.json"))
    clips, t = {}, 0.0
    for i in range(1, 11):
        c = data[str(i)]
        words = [(FIX.get(i, {}).get(w, w), a, b) for w, a, b in c["words"]]
        s0 = grid(max(0, c["rms_start"] - 0.08)); e0 = grid(min(c["speech_end"] + 0.06, c["dur"] - 0.01))
        rms = energy(i); lo, hi = int(s0 * 100), int(e0 * 100)
        thr = 0.10 * np.percentile(rms[lo:hi], 75); quiet = rms[lo:hi] < thr
        ranges, cur, k = [], s0, 0
        while k < len(quiet):                              # cut dead air (never inside a word)
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
        if i == 6:                                         # scripted delay: counter rolls with no voice
            clips[i]["pause"] = (t, t + PAUSE); t += PAUSE
    return clips, t


def tl(clips, i, src):
    """source time in voice clip i -> timeline seconds (nearest kept piece)"""
    best = None
    for p in clips[i]["pieces"]:
        if p["a"] - 1e-6 <= src <= p["b"] + 1e-6:
            return p["off"] + (src - p["a"])
        d = min(abs(src - p["a"]), abs(src - p["b"]))
        if best is None or d < best[0]:
            best = (d, p["off"] + (min(max(src, p["a"]), p["b"]) - p["a"]))
    return best[1]


def anchors(clips):
    def W_(i, word, nth=1):
        n = 0
        for w, a, b in clips[i]["words"]:
            if norm(w) == norm(word):
                n += 1
                if n == nth:
                    return grid(tl(clips, i, a))
        raise KeyError((i, word))
    return W_


# ---------------- edit decision list ------------------------------------------------------------
def build_edl(clips, total):
    Wd = anchors(clips)
    S = lambda i: clips[i]["start"]
    E = lambda i: clips[i]["end"]
    PE = clips[6]["pause"][1]
    game = lambda t0, t1, f, a, b: dict(kind="game", t0=t0, t1=t1, src=f, a=a, b=b)
    face = lambda t0, t1, i, z: dict(kind="face", t0=t0, t1=t1, clip=i, z=z)
    shots = [
        game(0, E(1), "01-corridor", 0.0, 6.0),
        face(S(2), Wd(2, "student"), 2, 1.10), face(Wd(2, "student"), E(2), 2, 1.30),
        game(S(3), Wd(3, "choose"), "02-enrol", 0.8, 2.4),
        game(Wd(3, "choose"), Wd(3, "red"), "02-enrol", 2.4, 3.3),
        game(Wd(3, "red"), E(3), "02-enrol", 3.4, 4.6),
        game(S(4), Wd(4, "because"), "02-enrol", 5.3, 7.8),
        game(Wd(4, "because"), Wd(4, "you"), "02-enrol", 7.9, 10.4),
    ]
    mont = [("03-football", 0.3), ("04-quiz", 0.3), ("05-hunt", 0.3), ("06-dance", 0.3)]     # round title cards
    a0, a1 = Wd(4, "you"), E(4); step = (a1 - a0) / 4
    for k, (f, s0) in enumerate(mont):
        shots.append(game(grid(a0 + k * step) if k else a0, grid(a0 + (k + 1) * step) if k < 3 else a1, f, s0, s0 + 0.9))
    shots += [
        game(S(5), Wd(5, "quiz"), "03-football", 1.9, 4.0),
        game(Wd(5, "quiz"), Wd(5, "treasure"), "04-quiz", 6.9, 9.0),
        game(Wd(5, "treasure"), Wd(5, "dance"), "05-hunt", 3.4, 5.5),
        game(Wd(5, "dance"), E(5), "06-dance", 9.0, 13.0),
        face(S(6), Wd(6, "student"), 6, 1.10), face(Wd(6, "student"), Wd(6, "you", 2), 6, 1.28),
        game(Wd(6, "you", 2), PE, "07-finale", 0.2, 5.3),
        game(S(7), Wd(7, "name"), "07-finale", 5.4, 8.6),
        game(Wd(7, "name"), E(7), "08-trophy", 0.0, 2.0),
        face(S(8), Wd(8, "and"), 8, 1.28), face(Wd(8, "and"), E(8), 8, 1.10),
        face(S(9), Wd(9, "if"), 9, 1.28), face(Wd(9, "if"), E(9), 9, 1.10),
        game(S(10), E(10), "08-trophy", 1.6, 6.0),
    ]
    for s in shots:
        s["t0"], s["t1"] = grid(s["t0"]), grid(s["t1"])
    # frame-exact chain
    for a, b in zip(shots, shots[1:]):
        b["t0"] = a["t1"]
    shots[-1]["t1"] = grid(total)

    def seg(t, c): return {"text": t, "color": c}
    L = lambda size, *segs: {"size": size, "segs": list(segs)}
    st = [
        dict(id="hook", top=560, t0=0.0, t1=grid(Wd(1, "we") + 0.6), lines=[L(54, seg("I MADE A", "navy")), L(66, seg("STUDENT OF THE YEAR", "red")), L(54, seg("GAME", "navy"))]),
        dict(id="house", t0=S(3), t1=grid(E(3) + 0.3), lines=[L(78, seg("RED HOUSE", "red")), L(58, seg("or ", "maroon"), seg("BLUE HOUSE?", "navy"))]),
        dict(id="rounds", t0=Wd(4, "you"), t1=E(4), lines=[L(84, seg("4 ROUNDS", "red")), L(52, seg("TO SURVIVE", "navy"))]),
        dict(id="r1", top=1010, t0=S(5), t1=Wd(5, "quiz"), lines=[L(48, seg("ROUND 1", "red")), L(84, seg("PENALTIES", "navy"))]),
        dict(id="r2", t0=Wd(5, "quiz"), t1=Wd(5, "treasure"), lines=[L(48, seg("ROUND 2", "red")), L(84, seg("QUIZ", "navy"))]),
        dict(id="r3", t0=Wd(5, "treasure"), t1=Wd(5, "dance"), lines=[L(48, seg("ROUND 3", "red")), L(70, seg("TREASURE HUNT", "navy"))]),
        dict(id="r4", t0=Wd(5, "dance"), t1=E(5), lines=[L(48, seg("ROUND 4", "red")), L(70, seg("DANCE BATTLE", "navy"))]),
        dict(id="hit", t0=Wd(6, "you", 2), t1=PE, count=dict(to=850, label="CAN YOU HIT 850?", rollSeconds=1.7)),
        dict(id="score", t0=Wd(7, "student"), t1=Wd(7, "name"), lines=[L(130, seg("883", "red")), L(56, seg("STUDENT OF THE YEAR", "navy"))]),
        dict(id="free", t0=S(8), t1=E(8), top=300, lines=[L(76, seg("FREE", "red"), seg(" · NO APP", "navy")), L(44, seg("PLAY IN YOUR BROWSER", "maroon"))]),
        dict(id="link", t0=S(9), t1=E(9), top=300, lines=[L(70, seg("COMMENT BELOW", "red")), L(48, seg("FOR THE LINK", "navy"))]),
        dict(id="next", t0=Wd(10, "another"), t1=E(10), lines=[L(70, seg("NEXT GAME?", "red")), L(48, seg("YOUR FAVORITE MOVIE", "navy"))]),
    ]
    for s in st:
        s["t0"], s["t1"] = round(float(s["t0"]), 3), round(float(s["t1"]), 3)
    caps, prev_start = [], -1
    for i in range(1, 11):
        for w, a, b in clips[i]["words"]:
            ta = int(tl(clips, i, a) * 1000); tb = int(tl(clips, i, min(b, clips[i]["pieces"][-1]["b"])) * 1000)
            ta = max(ta, prev_start + 60)                      # Whisper gives some words identical times:
            tb = max(tb, ta + 80)                              # keep starts strictly increasing, ends after starts
            if caps:
                caps[-1]["endMs"] = min(caps[-1]["endMs"], ta)
                caps[-1]["timestampMs"] = (caps[-1]["startMs"] + caps[-1]["endMs"]) // 2
            caps.append(dict(text=" " + w, startMs=ta, endMs=tb, timestampMs=(ta + tb) // 2, confidence=None))
            prev_start = ta
    return shots, st, caps


# ---------------- rendering ---------------------------------------------------------------------
def render_shot(k, sh, clips):
    d = round((sh["t1"] - sh["t0"]) * FPS) / FPS
    out = WORK / f"shot_{k:02d}{'_p' if PREVIEW else ''}.mp4"
    common = ["-c:v", "libx264", "-preset", "veryfast", "-crf", 24 if PREVIEW else 14, "-pix_fmt", "yuv420p", "-r", FPS, "-an"]
    if sh["kind"] == "game":
        span = sh["b"] - sh["a"]; sp = span / d
        if sp >= 1:
            vf = f"setpts=(PTS-STARTPTS)/{sp:.5f},fps={FPS}"
            inp = ["-ss", sh["a"], "-t", span, "-i", SRC / f"{sh['src']}.mp4"]
        else:                                              # source shorter than speech: play 1x, hold last frame
            vf = f"fps={FPS},tpad=stop_mode=clone:stop_duration={d - span + 0.1:.3f}"
            inp = ["-ss", sh["a"], "-t", span, "-i", SRC / f"{sh['src']}.mp4"]
        if PREVIEW:
            vf += f",scale={W}:{H}"
        run(inp + ["-vf", vf, "-t", f"{d:.3f}", *common, out])
        return out
    # face shot: map the timeline interval back to source time (pieces split at removed dead air)
    i, parts = sh["clip"], []
    for n, p in enumerate(clips[i]["pieces"]):
        lo, hi = max(sh["t0"], p["off"]), min(sh["t1"], p["off"] + p["b"] - p["a"])
        if hi - lo > 1e-6:
            parts.append((p["a"] + lo - p["off"], hi - lo))
    files = []
    ys = f"min(max(ih*{CHIN[i]}-{CHIN_PIN * H:.1f},0),ih-{H})"
    for n, (a, dd) in enumerate(parts):
        f = WORK / f"shot_{k:02d}_{n}{'_p' if PREVIEW else ''}.mp4"
        vf = (f"fps={FPS},scale={int(W * sh['z'])}:-2:flags=lanczos,crop={W}:{H}:x='(iw-{W})/2':y='{ys}',"
              f"eq=contrast=1.05:saturation=1.08,unsharp=5:5:0.4,setsar=1")
        run(["-ss", f"{a:.3f}", "-t", f"{dd:.3f}", "-i", SRC / f"{i}m.mp4", "-vf", vf, *common, f])
        files.append(f)
    if len(files) == 1:
        return files[0]
    lst = WORK / f"part_{k:02d}.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in files))
    run(["-f", "concat", "-safe", 0, "-i", lst, "-c", "copy", out])
    return out


def build_audio(clips, total):
    inp, parts, n = [], [], 0
    for i in range(1, 11):
        for p in clips[i]["pieces"]:
            inp += ["-ss", f"{p['a']:.3f}", "-t", f"{p['b'] - p['a']:.3f}", "-i", SRC / f"{i}m.mp4"]
            parts.append(f"[{n}:a]aresample=48000,afade=t=in:d=0.006,afade=t=out:st={p['b'] - p['a'] - 0.006:.3f}:d=0.006[a{n}]"); n += 1
        if i == 6:
            inp += ["-f", "lavfi", "-t", f"{PAUSE:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            parts.append(f"[{n}:a]anull[a{n}]"); n += 1
    # quiet score-roll ticks during the scripted pause
    sr = 48000; buf = np.zeros(int((total + 0.5) * sr)); t0 = clips[6]["pause"][0]
    t = t0 + 0.05
    while t < t0 + PAUSE - 0.2:
        a = int(t * sr); m = int(0.012 * sr); x = np.arange(m) / sr
        buf[a:a + m] += np.sin(2 * np.pi * 1800 * x) * np.exp(-x * 400) * 0.18
        t += 0.14 - 0.1 * (t - t0) / PAUSE
    wavp = WORK / "sfx.wav"
    with wave.open(str(wavp), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(sr)
        wv.writeframes(np.repeat((np.clip(buf, -1, 1) * 32767).astype(np.int16), 2).tobytes())
    inp += ["-i", wavp]
    chain = "".join(f"[a{k}]" for k in range(n))
    g = (";".join(parts) + f";{chain}concat=n={n}:v=0:a=1,aformat=channel_layouts=stereo[v];"
         f"[{n}:a]aformat=channel_layouts=stereo[s];[v][s]amix=inputs=2:normalize=0:duration=first,"
         "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    out = WORK / "voice_mix.m4a"
    run(inp + ["-filter_complex", g, "-map", "[a]", "-c:a", "aac", "-b:a", "256k", "-ar", 48000, out])
    return out


def concat_shots(files, tag):
    lst = WORK / f"concat_{tag}.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in files))
    return lst


def main():
    WORK.mkdir(exist_ok=True)
    clips, total = build_voice()
    shots, stickers, caps = build_edl(clips, total)
    json.dump(dict(fps=FPS, durationInFrames=round(total * FPS), captions=caps, stickers=stickers),
              open(REMO / "src/soy/edit.json", "w"), indent=1)
    json.dump(shots, open(WORK / "shots.json", "w"), indent=1)
    print(f"{len(shots)} shots, {total:.2f}s, {round(total * FPS)} frames", flush=True)
    if len(sys.argv) > 2 and sys.argv[2] == "json":
        return
    for k, s in enumerate(shots):
        print(k, s["kind"], s.get("src", f"face{s.get('clip')}"), f"{s['t0']:.2f}-{s['t1']:.2f}",
              (f"x{(s['b'] - s['a']) / (s['t1'] - s['t0']):.2f}" if s["kind"] == "game" else f"z{s['z']}"))
    if MODE == "final":                                    # reuse the 4K shots rendered by `base`
        files = [next(q for q in (WORK / f"shot_{k:02d}.mp4", WORK / f"shot_{k:02d}_0.mp4") if q.exists()) for k in range(len(shots))]
    else:
        files = [render_shot(k, s, clips) for k, s in enumerate(shots)]
    audio = build_audio(clips, total)
    lst = concat_shots(files, "p" if PREVIEW else "4k")
    if PREVIEW:
        run(["-f", "concat", "-safe", 0, "-i", lst, "-i", audio, "-c:v", "copy", "-c:a", "aac", "-shortest",
             REMO / "public/soy_base_preview.mp4"])
        print("preview base ready")
        return
    if MODE == "base":
        print("4K shots ready"); return
    # final: overlay frames from Remotion
    frames = sorted((REMO / "out/overlay").glob("*.png"))
    pat = frames[0].name.replace(frames[0].stem.split("-")[-1], "%0" + str(len(frames[0].stem.split("-")[-1])) + "d")
    OUT.mkdir(parents=True, exist_ok=True)
    final = OUT / "student_of_the_year_reel_4k.mp4"
    run(["-f", "concat", "-safe", 0, "-i", lst, "-framerate", FPS, "-i", REMO / "out/overlay" / pat, "-i", audio,
         "-filter_complex", f"[0:v][1:v]overlay=0:0:format=auto,scale=in_range=auto:out_range=tv,format=yuv420p[v]",
         "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "medium", "-crf", 16, "-colorspace", "bt709",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "copy", "-shortest", "-movflags", "+faststart", final])
    print("done", final)


if __name__ == "__main__":
    main()
