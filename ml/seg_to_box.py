#!/usr/bin/env python3
"""Convert a YOLO segmentation dataset into a detection dataset.

Several Roboflow projects advertise `object-detection` but export instance
segmentation: label rows carry a class index followed by an even number of
normalized polygon coordinates rather than four box values. Ultralytics will
happily train a detector on those files and learn nonsense from them, because
it reads the first four numbers after the class as cx/cy/w/h — which for a
polygon are the first two vertices.

The axis-aligned bounding box of a polygon is exactly the detection label, so
the conversion is lossless in the only sense that matters here.

    python ml/seg_to_box.py --source ml/datasets/crack-bphdr \\
        --output ml/datasets/crack-bphdr-box

Images are symlinked rather than copied — these sets run to gigabytes.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPLITS = ("train", "valid", "test")


def polygon_to_box(values: list[float]) -> tuple[float, float, float, float] | None:
    """Axis-aligned box of a normalized polygon, as (cx, cy, w, h)."""
    xs, ys = values[0::2], values[1::2]
    if not xs or not ys:
        return None
    x0, x1 = max(0.0, min(xs)), min(1.0, max(xs))
    y0, y1 = max(0.0, min(ys)), min(1.0, max(ys))
    w, h = x1 - x0, y1 - y0
    # A degenerate polygon — a line or a point — is not a trainable box.
    if w <= 1e-6 or h <= 1e-6:
        return None
    return (x0 + w / 2, y0 + h / 2, w, h)


def convert_label(path: Path) -> tuple[list[str], int, int]:
    """Return (rows, converted, already_boxes) for one label file."""
    rows: list[str] = []
    converted = already = 0
    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        cls, values = parts[0], [float(v) for v in parts[1:]]
        if len(values) == 4:
            # Already a detection row; pass it through untouched.
            rows.append(line.strip())
            already += 1
            continue
        if len(values) < 6 or len(values) % 2:
            continue  # not a polygon either; drop rather than guess
        box = polygon_to_box(values)
        if box is None:
            continue
        rows.append(f"{cls} " + " ".join(f"{v:.6f}" for v in box))
        converted += 1
    return rows, converted, already


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    source, output = args.source.resolve(), args.output.resolve()
    if not (source / "data.yaml").is_file():
        sys.exit(f"no data.yaml in {source}")

    shutil.rmtree(output, ignore_errors=True)
    total_conv = total_kept = total_files = 0

    for split in SPLITS:
        img_dir = source / split / "images"
        lbl_dir = source / split / "labels"
        if not img_dir.is_dir():
            continue
        out_img = output / split / "images"
        out_lbl = output / split / "labels"
        out_img.mkdir(parents=True, exist_ok=True)
        out_lbl.mkdir(parents=True, exist_ok=True)

        for image in sorted(img_dir.iterdir()):
            if not image.is_file():
                continue
            link = out_img / image.name
            if not link.exists():
                link.symlink_to(image)

            label = lbl_dir / (image.stem + ".txt")
            if label.is_file():
                rows, conv, kept = convert_label(label)
                total_conv += conv
                total_kept += kept
            else:
                rows = []          # no label file means a background image
            (out_lbl / (image.stem + ".txt")).write_text(
                "\n".join(rows) + ("\n" if rows else "")
            )
            total_files += 1

        print(f"  {split}: {len(list(out_img.iterdir()))} images")

    # data.yaml with absolute paths, matching what fetch_dataset.py produces.
    (output / "data.yaml").write_text(
        f"train: {output}/train/images\n"
        f"val: {output}/valid/images\n"
        f"test: {output}/test/images\n"
        "nc: 1\n"
        "names:\n"
        "- crack\n"
        f"path: {output}\n"
    )

    print(f"\n{total_files} label files written")
    print(f"  {total_conv} polygons converted to boxes")
    print(f"  {total_kept} rows already in box form, passed through")
    if total_conv == 0:
        print("\nNothing was converted — the source may already be a detection set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
