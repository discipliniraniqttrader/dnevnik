"""Final mux, <10 MB HEVC two-pass, contact sheet, report."""
import json, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from .common import F


def run(cmd): subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mux(parts, audio, final, workdir):
    lst = Path(workdir) / "_list.txt"; lst.write_text("".join(f"file '{p}'\n" for p in parts))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", str(final)])
    lst.unlink()
    for p in parts: Path(p).unlink()


def encode_9mb(final, out, dur, workdir, limit=9_700_000, preset="medium"):
    """libx265 two-pass, AAC 128k, -tag:v hvc1; shrinks the target until the file is under `limit` bytes."""
    vb = int((limit * 0.96 * 8 / dur - 128_000) / 1000)
    for attempt in range(4):
        stats = str(Path(workdir) / "x265_stats")
        base = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(final), "-c:v", "libx265", "-preset", preset, "-b:v", f"{vb}k", "-pix_fmt", "yuv420p", "-tag:v", "hvc1"]
        run(base + ["-x265-params", f"pass=1:stats={stats}:log-level=error", "-an", "-f", "null", "-"])
        run(base + ["-x265-params", f"pass=2:stats={stats}:log-level=error", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)])
        if Path(out).stat().st_size < limit: break
        vb = int(vb * .9)
    for p in Path(workdir).glob("x265_stats*"): p.unlink()
    return Path(out).stat().st_size, vb


def contact_sheet(video, out, dur, n=20, cols=5):
    tw, th = 216, 384
    rows = int(np.ceil(n / cols))
    sheet = Image.new("RGB", (tw * cols, th * rows), (12, 12, 14))
    ts = np.linspace(0.25, max(dur - 0.4, 0.5), n)
    tmp = Path(out).parent / "_sheet_frame.png"
    f = F("sans-black.ttf", 26)
    for i, t in enumerate(ts):
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(tmp)])
        im = Image.open(tmp).convert("RGB").resize((tw, th), Image.LANCZOS)
        d = ImageDraw.Draw(im); d.rectangle([0, 0, 92, 34], fill=(0, 0, 0)); d.text((6, 4), f"{t:5.1f}s", font=f, fill=(255, 230, 120))
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    tmp.unlink(missing_ok=True)
    sheet.save(out)
