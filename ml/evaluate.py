#!/usr/bin/env python3
"""Evaluate a trained detector on defective and defect-free imagery.

Standard mAP tells you how well the model localises defects it was trained on.
It says nothing about what the model does when pointed at an intact surface —
and a detector that draws boxes on clean concrete fails the demo regardless of
its mAP.

This script measures both, across a sweep of confidence thresholds, because
the false-positive rate is a function of the threshold and picking one without
looking at the curve is guesswork.

Usage:
    # False positives on defect-free images
    python ml/evaluate.py --weights ml/weights/crack-detector.pt \\
        --clean-from-empty-labels ml/datasets/concrete-bridge-defect

    # Detection rate on images known to contain defects
    python ml/evaluate.py --weights ml/weights/crack-detector.pt \\
        --defective ml/datasets/nitw-crack/test/images
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
DEFAULT_SWEEP = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--weights", required=True, help="Path to a trained checkpoint")
    p.add_argument("--clean", help="Directory of images with NO defects")
    p.add_argument(
        "--clean-from-empty-labels",
        help="YOLO dataset root; images whose label file is empty are treated "
             "as defect-free. More reliable than eyeballing a folder.",
    )
    p.add_argument("--defective", help="Directory of images that DO contain defects")
    p.add_argument("--device", default="0")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument(
        "--thresholds", type=float, nargs="+", default=DEFAULT_SWEEP,
        help="Confidence thresholds to sweep",
    )
    p.add_argument("--limit", type=int, help="Cap images per set (quick checks)")
    return p.parse_args()


def gather_images(directory: Path, limit: int | None = None) -> list[Path]:
    files = sorted(
        f for f in directory.rglob("*")
        if f.suffix.lower() in IMAGE_SUFFIXES and f.is_file()
    )
    return files[:limit] if limit else files


def gather_empty_label_images(root: Path, limit: int | None = None) -> list[Path]:
    """Find images whose YOLO label file is empty — i.e. annotated as clean.

    These are ground truth for 'no defect here', which is stronger evidence
    than a folder someone believes is clean.
    """
    found: list[Path] = []
    for labels_dir in sorted(root.rglob("labels")):
        images_dir = labels_dir.parent / "images"
        if not images_dir.is_dir():
            continue
        for label in sorted(labels_dir.glob("*.txt")):
            if label.stat().st_size > 0:
                continue
            for suffix in IMAGE_SUFFIXES:
                candidate = images_dir / f"{label.stem}{suffix}"
                if candidate.is_file():
                    found.append(candidate)
                    break
    return found[:limit] if limit else found


def run(model, images: list[Path], imgsz: int, device: str,
        min_threshold: float) -> list[list[float]]:
    """Return per-image lists of detection confidences.

    Predicts once at the lowest threshold in the sweep and filters afterwards,
    rather than re-running the model per threshold.
    """
    per_image: list[list[float]] = []
    batch = 16
    for start in range(0, len(images), batch):
        chunk = [str(p) for p in images[start:start + batch]]
        for result in model.predict(
            chunk, conf=min_threshold, imgsz=imgsz, device=device, verbose=False
        ):
            boxes = getattr(result, "boxes", None)
            per_image.append(
                [float(c) for c in boxes.conf.tolist()] if boxes is not None else []
            )
    return per_image


def report(title: str, per_image: list[list[float]], thresholds: list[float],
           clean: bool) -> None:
    n = len(per_image)
    print(f"\n{title}  ({n} images)")
    print("-" * 62)
    label = "false-positive rate" if clean else "detection rate"
    print(f"{'conf':>6}  {'images flagged':>15}  {label:>20}  {'boxes':>7}")
    for t in thresholds:
        flagged = sum(1 for confs in per_image if any(c >= t for c in confs))
        boxes = sum(1 for confs in per_image for c in confs if c >= t)
        rate = flagged / n if n else 0.0
        marker = ""
        if clean and rate > 0.20:
            marker = "  <-- high"
        elif not clean and rate < 0.70:
            marker = "  <-- low"
        print(f"{t:>6.2f}  {flagged:>15}  {rate:>19.1%}  {boxes:>7}{marker}")

    all_conf = [c for confs in per_image for c in confs]
    if all_conf:
        all_conf.sort()
        mid = all_conf[len(all_conf) // 2]
        print(f"\n  confidence: min={all_conf[0]:.3f} median={mid:.3f} "
              f"max={all_conf[-1]:.3f}  ({len(all_conf)} boxes total)")


def main() -> int:
    args = parse_args()

    weights = Path(args.weights)
    if not weights.is_file():
        sys.exit(f"weights not found: {weights}")

    if not (args.clean or args.clean_from_empty_labels or args.defective):
        sys.exit("supply at least one of --clean, --clean-from-empty-labels, "
                 "--defective")

    from ultralytics import YOLO

    model = YOLO(str(weights))
    thresholds = sorted(args.thresholds)
    lowest = thresholds[0]
    print(f"weights   : {weights}")
    print(f"thresholds: {', '.join(f'{t:.2f}' for t in thresholds)}")

    clean_images: list[Path] = []
    if args.clean_from_empty_labels:
        clean_images = gather_empty_label_images(
            Path(args.clean_from_empty_labels), args.limit
        )
        if not clean_images:
            print("! no empty-label images found — is that a YOLO dataset root?",
                  file=sys.stderr)
    elif args.clean:
        clean_images = gather_images(Path(args.clean), args.limit)

    if clean_images:
        per_image = run(model, clean_images, args.imgsz, args.device, lowest)
        report("CLEAN SURFACES — every box here is a false positive",
               per_image, thresholds, clean=True)

    if args.defective:
        images = gather_images(Path(args.defective), args.limit)
        if images:
            per_image = run(model, images, args.imgsz, args.device, lowest)
            report("DEFECTIVE SURFACES — every miss here is a false negative",
                   per_image, thresholds, clean=False)

    print(
        "\nNote: 'detection rate' is per-image, not per-defect — it counts "
        "images with at least\none box, so it is an optimistic proxy for "
        "recall. Use mAP from training for localisation quality."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
