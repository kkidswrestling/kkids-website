#!/usr/bin/env python3
"""Process photos listed in data/photos.toml into web-ready files.

For each photo whose `file` exists (relative to --src or absolute), this writes
  assets/img/photos/<id>-<width>.webp   for every width in `widths`
  assets/img/photos/<id>.jpg            one JPEG fallback (<= 1200px wide)
and records the output sizes in assets/img/photos/manifest.json, which the page
builder reads for width/height attributes and srcset lists.

Photos whose source file is missing are left as they are, so this can be re-run
any time to add or re-crop a single photo:

    python3 tools/images.py --src /path/to/extracted/images [--only hero-circle]
"""
import argparse, json, os, sys, tomllib
from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "img", "photos")
Image.MAX_IMAGE_PIXELS = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=".", help="folder that `file` paths are relative to")
    ap.add_argument("--only", nargs="*", help="process only these photo ids")
    args = ap.parse_args()

    catalog = tomllib.load(open(os.path.join(ROOT, "data", "photos.toml"), "rb"))["photo"]
    os.makedirs(OUT, exist_ok=True)
    man_path = os.path.join(OUT, "manifest.json")
    manifest = json.load(open(man_path)) if os.path.exists(man_path) else {}

    ids = [p["id"] for p in catalog]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        sys.exit(f"duplicate photo ids: {sorted(dupes)}")

    for p in catalog:
        if args.only and p["id"] not in args.only:
            continue
        src = p.get("file", "")
        path = src if os.path.isabs(src) else os.path.join(args.src, src)
        if not src or not os.path.exists(path):
            if p["id"] not in manifest:
                print(f"  missing source, skipped: {p['id']}")
            continue
        im = Image.open(path)
        im = ImageOps.exif_transpose(im).convert("RGB")
        if "crop" in p:
            im = im.crop(tuple(p["crop"]))
        if p.get("gray"):
            im = ImageOps.grayscale(im).convert("RGB")
        w0, h0 = im.size
        # remove stale files for this id
        for f in os.listdir(OUT):
            if f.startswith(p["id"] + "-") and f.endswith(".webp") or f == p["id"] + ".jpg":
                os.remove(os.path.join(OUT, f))
        widths = sorted({min(w, w0) for w in p.get("widths", [640, 1200])})
        out = []
        for w in widths:
            h = round(h0 * w / w0)
            r = im if w == w0 else im.resize((w, h), Image.LANCZOS)
            r.save(os.path.join(OUT, f"{p['id']}-{w}.webp"), "WEBP", quality=74, method=6)
            out.append([w, h])
        fw = min(1200, w0)
        fh = round(h0 * fw / w0)
        fb = im if fw == w0 else im.resize((fw, fh), Image.LANCZOS)
        fb.save(os.path.join(OUT, f"{p['id']}.jpg"), "JPEG", quality=80, optimize=True, progressive=True)
        manifest[p["id"]] = {"w": w0, "h": h0, "widths": out, "fallback": [fw, fh]}
        print(f"  {p['id']}: {w0}x{h0} -> {[w for w, _ in out]}")

    known = set(ids)
    for k in list(manifest):
        if k not in known:
            del manifest[k]
    json.dump(manifest, open(man_path, "w"), indent=1, sort_keys=True)
    print(f"{len(manifest)} photos in manifest")


if __name__ == "__main__":
    main()
