#!/usr/bin/env python3
"""Mine defect-free crops from annotated images, to use as training backgrounds.

Backgrounds are what stop a detector firing on clean concrete — README D-017
measured them lifting separation from 0.406 to 0.622. But they only work in
proportion: going from one dataset to three took the training set from 1,317
images to 6,615 while the background count stayed at 120, diluting them from
9% to under 2%. The detector's recall went up on every source and its
false-positive rate went from 20% to 65%, which is a worse model.

There is no fourth dataset of clean concrete to hand, but there is a great deal
of clean concrete *inside* the images already collected — every region of a
cracked photograph that the annotator did not draw a box around. This crops
those regions out.

    python ml/mine_backgrounds.py --source ml/datasets/nitw-crack/train \\
        --output ml/datasets/_mined-bg --per-image 2

The result is a split directory of images with empty label files, consumable by
`merge_datasets.py --backgrounds-from`.

A caution worth stating: this assumes the annotations are complete. Where a
real crack was missed by the annotator, this will mine it as "clean" and teach
the model to ignore it. `--margin` keeps crops well clear of known boxes, which
limits the damage but cannot eliminate it.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def read_boxes(label: Path) -> list[tuple[float, float, float, float]]:
    """Normalized (x0, y0, x1, y1) for each annotation."""
    boxes = []
    if not label.is_file():
        return boxes
    for line in label.read_text().splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        cx, cy, w, h = (float(v) for v in parts[1:])
        boxes.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    return boxes


def overlaps(crop, boxes, margin: float) -> bool:
    """True if the crop comes within `margin` of any annotation."""
    x0, y0, x1, y1 = crop
    for bx0, by0, bx1, by1 in boxes:
        if (x0 < bx1 + margin and x1 > bx0 - margin
                and y0 < by1 + margin and y1 > by0 - margin):
            return True
    return False


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", nargs="+", required=True, type=Path,
                   help="Split directories holding images/ and labels/")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--per-image", type=int, default=2,
                   help="Crops to attempt per source image")
    p.add_argument("--size", type=float, nargs=2, default=(0.30, 0.55),
                   help="Crop side as a fraction of the image, min and max")
    p.add_argument("--margin", type=float, default=0.04,
                   help="Normalized clearance to keep from any annotation")
    p.add_argument("--attempts", type=int, default=25,
                   help="Random placements tried per crop before giving up")
    p.add_argument("--limit", type=int, help="Cap source images per split")
    p.add_argument("--seed", type=int, default=11)
    args = p.parse_args()

    from PIL import Image

    rng = random.Random(args.seed)
    out_img = args.output / "images"
    out_lbl = args.output / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    written = skipped = 0
    for split in args.source:
        images = sorted(f for f in (split / "images").iterdir()
                        if f.suffix.lower() in IMAGE_SUFFIXES)
        if args.limit:
            images = images[:args.limit]
        tag = split.resolve().parent.name

        for image_path in images:
            boxes = read_boxes(split / "labels" / (image_path.stem + ".txt"))
            # An image with no annotations is already a background; mining it
            # would just duplicate what merge_datasets picks up directly.
            if not boxes:
                continue

            try:
                img = Image.open(image_path).convert("RGB")
            except Exception:
                continue
            w, h = img.size

            made = 0
            for _ in range(args.attempts):
                if made >= args.per_image:
                    break
                side = rng.uniform(*args.size)
                x0 = rng.uniform(0, 1 - side)
                y0 = rng.uniform(0, 1 - side)
                crop = (x0, y0, x0 + side, y0 + side)
                if overlaps(crop, boxes, args.margin):
                    continue
                px = (int(x0 * w), int(y0 * h),
                      int((x0 + side) * w), int((y0 + side) * h))
                if px[2] - px[0] < 32 or px[3] - px[1] < 32:
                    continue
                name = f"{tag}__{image_path.stem}__bg{made}.jpg"
                img.crop(px).save(out_img / name, quality=92)
                (out_lbl / f"{tag}__{image_path.stem}__bg{made}.txt").write_text("")
                made += 1
                written += 1
            if made == 0:
                skipped += 1

        print(f"  {split}: {len(images)} images scanned")

    print(f"\n{written} background crops written to {args.output}")
    print(f"{skipped} images yielded none (annotations covered too much of the frame)")
    if written == 0:
        sys.exit("no backgrounds mined — try a smaller --size or --margin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
