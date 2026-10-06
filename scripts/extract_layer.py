"""Cut a separated layer out of a shot master and rebuild the plate behind it.

For projects that only have finished masters: extract a prop (with its rider)
as a full-canvas transparent PNG, fill the background it leaves behind, and
write a review sheet a person must look at before the layer is used.

    python scripts/extract_layer.py extract <project> --master shots/s3/master.png \
        --name capy_horse --rect 705,110,1185,680 [hints...]
    python scripts/extract_layer.py approve <project> layers/capy_horse.extract.json --note "edges checked"

Coordinates are pixels on the master canvas. Hints (all repeatable):
  --fg-box x0,y0,x1,y1      definitely part of the layer (e.g. a white shirt next to a white wall)
  --fg-line "x,y x,y ..."   a stroke that is definitely the layer (thin parts such as a rocker arc)
  --bg-box x0,y0,x1,y1      definitely background, used during segmentation
  --bg-poly "x,y x,y ..."   carved out after segmentation (e.g. furniture seen through a gap)
  --line-art x0,y0,x1,y1    add dark line pixels in this box (whiskers, hair strands)
Plate:
  --extend-down-until Y     rebuild wall rows above Y column by column (keeps vertical edges straight)
Review preview:
  --pivot x,y --max-angle D show the layer tilted ±D degrees over the plate

Outputs (in --out, default layers/): <name>.png, <name>_plate.png,
<name>_review.png and <name>.extract.json. Pass --hints with a hints JSON or a
previous .extract.json to rerun with the same settings.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np

VERSION = "0.1"
HINT_KEYS = ("rect", "fg_box", "fg_line", "bg_box", "bg_poly", "line_art", "extend_down_until", "pivot", "max_angle")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _numbers(text, count=None):
    values = [int(round(float(v))) for v in str(text).replace(",", " ").split()]
    if count and len(values) != count:
        raise ValueError(f"expected {count} numbers, got {text!r}")
    return values


def _points(text):
    values = _numbers(text)
    if len(values) < 4 or len(values) % 2:
        raise ValueError(f"expected x,y pairs, got {text!r}")
    return [(values[i], values[i + 1]) for i in range(0, len(values), 2)]


def normalise_hints(raw):
    """Turn CLI strings or JSON values into one canonical hints dict."""
    def boxes(key):
        return [list(_numbers(v, 4)) if isinstance(v, str) else list(v) for v in raw.get(key) or []]

    def polys(key):
        return [[list(p) for p in (_points(v) if isinstance(v, str) else v)] for v in raw.get(key) or []]

    rect = raw.get("rect")
    if rect is None:
        raise ValueError("--rect is required")
    pivot = raw.get("pivot")
    return {
        "rect": list(_numbers(rect, 4)) if isinstance(rect, str) else list(rect),
        "fg_box": boxes("fg_box"),
        "fg_line": polys("fg_line"),
        "bg_box": boxes("bg_box"),
        "bg_poly": polys("bg_poly"),
        "line_art": boxes("line_art"),
        "extend_down_until": int(raw["extend_down_until"]) if raw.get("extend_down_until") is not None else None,
        "pivot": (list(_numbers(pivot, 2)) if isinstance(pivot, str) else list(pivot)) if pivot is not None else None,
        "max_angle": float(raw.get("max_angle") if raw.get("max_angle") is not None else 3.0),
    }


def segment(image, hints):
    """Two GrabCut passes (box only, then with hints), merged and cleaned."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = hints["rect"]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    if x1 - x0 < 8 or y1 - y0 < 8:
        raise ValueError("rect is too small or outside the master")

    def keep_large(mask):
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        if n <= 1:
            return mask
        largest = stats[1:, cv2.CC_STAT_AREA].max()
        out = np.zeros_like(mask)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] >= max(200, 0.05 * largest):
                out[labels == i] = 255
        return out

    # pass 1: rectangle only — usually gets the main body (heads, large shapes)
    mask = np.zeros((h, w), np.uint8)
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(image, mask, (x0, y0, x1 - x0, y1 - y0), bgd, fgd, 8, cv2.GC_INIT_WITH_RECT)
    first = keep_large(np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8))

    # pass 2: hints recover parts that look like the background
    mask = np.full((h, w), cv2.GC_BGD, np.uint8)
    mask[y0:y1, x0:x1] = cv2.GC_PR_FGD
    for bx0, by0, bx1, by1 in hints["bg_box"]:
        mask[by0:by1, bx0:bx1] = cv2.GC_BGD
    for bx0, by0, bx1, by1 in hints["fg_box"]:
        mask[by0:by1, bx0:bx1] = cv2.GC_FGD
    for line in hints["fg_line"]:
        cv2.polylines(mask, [np.array(line, np.int32)], False, cv2.GC_FGD, 7)
    if (mask == cv2.GC_FGD).any():
        bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
        cv2.grabCut(image, mask, None, bgd, fgd, 10, cv2.GC_INIT_WITH_MASK)
        second = keep_large(np.where((mask == 1) | (mask == 3), 255, 0).astype(np.uint8))
        merged = cv2.bitwise_or(first, second)
    else:
        merged = first
    for bx0, by0, bx1, by1 in hints["bg_box"]:
        merged[by0:by1, bx0:bx1] = 0

    # fill only small enclosed holes (specks, gaps between strokes), never large floor gaps
    hole_limit = max(200, int(h * w * 0.001))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.bitwise_not(merged), connectivity=4)
    for i in range(1, n):
        bx, by, bw, bh, area = stats[i]
        if area < hole_limit and bx > 0 and by > 0 and bx + bw < w and by + bh < h:
            merged[labels == i] = 255
    merged = cv2.morphologyEx(merged, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    for poly in hints["bg_poly"]:
        cv2.fillPoly(merged, [np.array(poly, np.int32)], 0)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(merged)
    if n > 1:
        merged = np.where(labels == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA])), 255, 0).astype(np.uint8)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    for bx0, by0, bx1, by1 in hints["line_art"]:
        box = np.zeros_like(merged)
        box[by0:by1, bx0:bx1] = 255
        dark = ((gray < 150) & (box > 0)).astype(np.uint8) * 255
        merged = cv2.bitwise_or(merged, cv2.dilate(dark, np.ones((3, 3), np.uint8)))
    if not merged.any():
        raise ValueError("segmentation found nothing; adjust --rect or add --fg-box hints")
    return merged


def build_plate(base, mask, extend_down_until=None):
    """Fill what the layer covered. Walls are rebuilt column by column so edges stay straight."""
    hole = cv2.dilate(mask, np.ones((15, 15), np.uint8)) > 0
    plate = cv2.inpaint(base, hole.astype(np.uint8) * 255, 9, cv2.INPAINT_TELEA)
    if extend_down_until:
        limit = min(int(extend_down_until), base.shape[0])
        columns = np.where(hole[:limit].any(axis=0))[0]
        for x in columns:
            column = hole[:limit, x]
            top = int(np.argmax(column))
            if top == 0:
                continue
            plate[top:limit, x][column[top:]] = base[top - 1, x]
        band = np.zeros(hole.shape, bool)
        band[max(0, limit - 10):limit + 11] = True
        band &= hole
        blur = cv2.GaussianBlur(plate, (0, 0), 4)
        plate[band] = blur[band]
    return plate


def layer_rgba(image, mask):
    rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = cv2.GaussianBlur(mask, (3, 3), 0.8)
    return rgba


def _tilt(layer, plate, pivot, angle):
    m = cv2.getRotationMatrix2D((float(pivot[0]), float(pivot[1])), angle, 1.0)
    moved = cv2.warpAffine(layer, m, (plate.shape[1], plate.shape[0]), borderValue=(0, 0, 0, 0))
    a = moved[:, :, 3:4].astype(np.float32) / 255
    return (moved[:, :, :3] * a + plate * (1 - a)).astype(np.uint8)


def review_sheet(image, mask, layer, plate, pivot, max_angle):
    """Four panels: cut-out over dimmed master, plate alone, tilted ±max_angle over the plate."""
    ys, xs = np.where(mask > 0)
    h, w = mask.shape
    pad = 40
    x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + pad)
    y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + pad)
    overlay = image.copy()
    overlay[mask == 0] = (overlay[mask == 0] * 0.3).astype(np.uint8)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(overlay, contours, -1, (0, 0, 255), 1)
    panels = [("cut-out", overlay), ("plate", plate),
              (f"tilt +{max_angle:g}", _tilt(layer, plate, pivot, max_angle)),
              (f"tilt -{max_angle:g}", _tilt(layer, plate, pivot, -max_angle))]
    crops = []
    for label, panel in panels:
        crop = panel[y0:y1, x0:x1].copy()
        cv2.rectangle(crop, (0, 0), (crop.shape[1] - 1, 24), (30, 30, 30), -1)
        cv2.putText(crop, label, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        crops.append(crop)
    sep = np.full((y1 - y0, 6, 3), 255, np.uint8)
    return np.hstack([crops[0], sep, crops[1], sep, crops[2], sep, crops[3]])


def extract(project, master, name, out="layers", hints=None, base=None):
    project = Path(project).resolve()
    master_path = project / master
    image = cv2.imread(str(master_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"cannot read master {master_path}")
    hints = normalise_hints(hints or {})
    base_image = image if base is None else cv2.imread(str(project / base), cv2.IMREAD_COLOR)
    if base_image is None or base_image.shape != image.shape:
        raise ValueError("--base must be an image with the master's size")
    mask = segment(image, hints)
    layer = layer_rgba(image, mask)
    plate = build_plate(base_image, mask, hints["extend_down_until"])
    ys, xs = np.where(mask > 0)
    pivot = hints["pivot"] or [int(xs.mean()), int(ys.max())]
    folder = project / out
    folder.mkdir(parents=True, exist_ok=True)
    paths = {
        "layer": folder / f"{name}.png",
        "plate": folder / f"{name}_plate.png",
        "review": folder / f"{name}_review.png",
    }
    cv2.imwrite(str(paths["layer"]), layer)
    cv2.imwrite(str(paths["plate"]), plate)
    cv2.imwrite(str(paths["review"]), review_sheet(image, mask, layer, plate, pivot, hints["max_angle"]))
    manifest = {
        "version": VERSION,
        "tool": "extract_layer",
        "master": Path(master).as_posix(),
        "master_sha256": sha256(master_path),
        "base": Path(base).as_posix() if base else None,
        "hints": {**hints, "pivot": pivot},
        "bbox": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
        "mask_pixels": int((mask > 0).sum()),
        "outputs": {key: {"path": path.relative_to(project).as_posix(), "sha256": sha256(path)} for key, path in paths.items()},
        "reviewed": False,
        "review_note": None,
    }
    manifest_path = folder / f"{name}.extract.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path, manifest


def stale_outputs(project, manifest):
    """Outputs whose files changed (or vanished) since extraction or approval."""
    project = Path(project)
    stale = []
    for key, item in manifest.get("outputs", {}).items():
        path = project / item["path"]
        if key != "review" and (not path.is_file() or sha256(path) != item["sha256"]):
            stale.append(item["path"])
    master = project / manifest.get("master", "")
    if not master.is_file() or sha256(master) != manifest.get("master_sha256"):
        stale.append(manifest.get("master"))
    return stale


def approve(project, manifest_path, note=None):
    project = Path(project).resolve()
    manifest_path = (project / manifest_path) if not Path(manifest_path).is_absolute() else Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stale = stale_outputs(project, manifest)
    if stale:
        raise ValueError("files changed since extraction; rerun extract first: " + ", ".join(map(str, stale)))
    manifest["reviewed"] = True
    manifest["review_note"] = note or "review sheet inspected"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def manifest_for_asset(project, asset):
    """Find the extraction manifest that produced a layer or plate asset, if any."""
    asset = Path(asset)
    for candidate in (asset.with_name(asset.stem + ".extract.json"),
                      asset.with_name(asset.stem.removesuffix("_plate") + ".extract.json")):
        path = Path(project) / candidate
        if path.is_file():
            return path
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("extract", help="segment a layer and rebuild its plate")
    ex.add_argument("project", type=Path)
    ex.add_argument("--master", required=True, help="master image, relative to the project")
    ex.add_argument("--name", required=True, help="layer name, e.g. capy_horse")
    ex.add_argument("--out", default="layers", help="output folder inside the project")
    ex.add_argument("--base", help="image to fill instead of the master (e.g. an earlier plate)")
    ex.add_argument("--hints", type=Path, help="hints JSON or a previous .extract.json")
    ex.add_argument("--rect")
    for key in ("fg-box", "fg-line", "bg-box", "bg-poly", "line-art"):
        ex.add_argument(f"--{key}", action="append", default=None)
    ex.add_argument("--extend-down-until", type=int)
    ex.add_argument("--pivot")
    ex.add_argument("--max-angle", type=float)
    ap = sub.add_parser("approve", help="record that the review sheet was inspected")
    ap.add_argument("project", type=Path)
    ap.add_argument("manifest")
    ap.add_argument("--note")
    args = parser.parse_args(argv)
    try:
        if args.command == "approve":
            manifest = approve(args.project, args.manifest, args.note)
            print(json.dumps({"status": "APPROVED", "outputs": manifest["outputs"]}, ensure_ascii=False))
            return 0
        hints = {}
        if args.hints:
            loaded = json.loads(args.hints.read_text(encoding="utf-8"))
            hints = dict(loaded.get("hints", loaded))
        for key in HINT_KEYS:
            value = getattr(args, key, None)
            if value is not None:
                hints[key] = value
        manifest_path, manifest = extract(args.project, args.master, args.name, args.out, hints, args.base)
        print(json.dumps({"status": "REVIEW_REQUIRED", "manifest": str(manifest_path),
                          "review": manifest["outputs"]["review"]["path"],
                          "next": f"open the review sheet, then: python scripts/extract_layer.py approve {args.project} {Path(manifest_path).relative_to(Path(args.project).resolve()).as_posix()}"},
                         ensure_ascii=False))
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
