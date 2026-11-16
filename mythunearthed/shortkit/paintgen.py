"""Painted-style image worker (runs under voice/venv python, PYTHONPATH=voice/pylib_new for diffusers>=0.40).
  python paintgen.py jobs.json   jobs: {"model":..., "jobs":[{"key","prompt","neg","seed","w","h","steps","img","depth"}]}
Generates each missing image with SDXL-Turbo (bf16, CPU) and a depth map with depth-anything-small. Existing outputs are skipped (free re-renders)."""
import json, os, sys, time
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
import numpy as np, torch
from pathlib import Path
from PIL import Image
torch.set_num_threads(4)


def layout_image(L, w, h):
    """rough composition init (ours): dusk sky gradient, dark sea below `horizon`, black polygons in normalized coords. img2img then paints it."""
    from PIL import ImageDraw, ImageFilter
    hz = L.get("horizon", 0.69); ground = L.get("ground", "sea")
    y = np.arange(h)[:, None] / h; top = np.array(L.get("sky_top", [78, 46, 34]), float); bot = np.array(L.get("sky_bot", [236, 128, 52]), float)
    t = np.clip(y / max(hz, 1e-3), 0, 1) ** 1.3; a = top[None] * (1 - t) + bot[None] * t
    sea0 = np.array(L.get("sea_top", [92, 48, 28]), float); sea1 = np.array(L.get("sea_bot", [14, 10, 10]), float); u = np.clip((y - hz) / max(1 - hz, 1e-3), 0, 1)
    b = sea0[None] * (1 - u) + sea1[None] * u
    arr = np.where(y >= hz, b, a); arr = np.repeat(arr[:, None, :], w, 1).astype(np.uint8)
    rng = np.random.default_rng(5); cl = rng.random((h // 40 + 2, w // 160 + 2)).astype(np.float32)
    from PIL import ImageFilter as _IF
    cl = np.asarray(Image.fromarray((cl * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC).filter(_IF.GaussianBlur(6))).astype(np.float32) / 255.0
    sky = (np.arange(h)[:, None] < hz * h)[..., None]
    arr = np.where(sky, arr * (0.62 + 0.7 * cl[..., None]), arr)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); sx_, sy_ = L.get("sun", [0.5, hz - 0.01])
    g = np.clip(1 - np.sqrt(((xx - sx_ * w) / (0.35 * w)) ** 2 + ((yy - sy_ * h) / (0.2 * h)) ** 2), 0, 1) ** 2
    arr = np.clip(arr + g[..., None] * np.array([90, 60, 20], np.float32), 0, 255).astype(np.uint8)
    im = Image.fromarray(arr); d = ImageDraw.Draw(im)
    for sh in L.get("shapes", []):
        d.polygon([(px * w, py * h) for px, py in sh["poly"]], fill=tuple(sh.get("col", [10, 8, 7])))
    return im.filter(ImageFilter.GaussianBlur(5))


def main():
    cfg = json.load(open(sys.argv[1])); jobs = cfg["jobs"]
    need_img = [j for j in jobs if not Path(j["img"]).exists()]
    if need_img:
        from diffusers import AutoPipelineForText2Image
        pipe = AutoPipelineForText2Image.from_pretrained(cfg.get("model", "stabilityai/sdxl-turbo"), torch_dtype=torch.bfloat16, variant="fp16")
        pipe.set_progress_bar_config(disable=True)
        from diffusers import AutoPipelineForImage2Image
        pipe2 = AutoPipelineForImage2Image.from_pipe(pipe) if any(j.get("layout") or j.get("wide") for j in need_img) else None
        for j in need_img:
            t = time.time()
            if j.get("layout"):
                init = layout_image(j["layout"], j["w"], j["h"]); init.save(j["img"].replace(".png", "_layout.png"))
                im = pipe2(j["prompt"], image=init, strength=j["layout"].get("strength", 0.92), negative_prompt=j["neg"], num_inference_steps=j["layout"].get("steps", 5), guidance_scale=0.0,
                           generator=torch.Generator().manual_seed(j["seed"])).images[0]
            else:
                im = pipe(j["prompt"], negative_prompt=j["neg"], width=j["w"], height=j["h"], num_inference_steps=j["steps"], guidance_scale=0.0,
                          generator=torch.Generator().manual_seed(j["seed"])).images[0]
            tmp = j["img"] + ".tmp.png"; im.save(tmp); os.replace(tmp, j["img"])
            print(f"IMG {j['key']} {time.time() - t:.1f}s", flush=True)
        del pipe
    need_d = [j for j in jobs if not Path(j["depth"]).exists()]
    if need_d:
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation
        mid = "LiheYoung/depth-anything-small-hf"
        proc = AutoImageProcessor.from_pretrained(mid); model = AutoModelForDepthEstimation.from_pretrained(mid).eval()
        for j in need_d:
            im = Image.open(j["img"]).convert("RGB")
            with torch.no_grad():
                out = model(**proc(images=im, return_tensors="pt")).predicted_depth
            d = torch.nn.functional.interpolate(out[None], size=im.size[::-1], mode="bicubic", align_corners=False)[0, 0].numpy()
            lo, hi = np.percentile(d, [1, 99]); d = np.clip((d - lo) / (hi - lo + 1e-9), 0, 1)
            Image.fromarray((d * 65535).astype(np.uint16)).save(j["depth"])
            print(f"DEPTH {j['key']}", flush=True)


if __name__ == "__main__": main()
