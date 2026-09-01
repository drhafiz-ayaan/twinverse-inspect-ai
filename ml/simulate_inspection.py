#!/usr/bin/env python3
"""Simulate a real inspection campaign to choose an operating threshold.

Every number in this project so far has been optimised for *separation* —
detection rate minus false-positive rate. That metric weights a missed crack
and a false alarm equally, and in structural inspection they are not remotely
equal:

  A missed crack propagates. It is found at the next survey, or it is found
  when something fails. A false alarm costs an engineer the thirty seconds it
  takes to look at a photograph and dismiss it.

So separation is the wrong objective, and picking a threshold to maximise it
produces a tool tuned for a symmetry the domain does not have. What an
inspection team actually needs to know is:

  "On a survey of this size, how many real defects will this miss, and how many
   photographs will somebody have to look at?"

That is what this simulates. It runs the detector once over known-defective and
known-clean imagery, caches the highest confidence per image, then replays
synthetic surveys at a given defect prevalence across a sweep of thresholds.

    python ml/simulate_inspection.py --weights ml/weights/crack-hardneg.pt \\
        --defective ml/datasets/_test_crackb \\
        --clean-from-empty-labels ml/datasets/concrete-bridge-defect

Prevalence defaults to 12%, which is the order of magnitude reported for
routine condition surveys of ageing concrete; pass --prevalence to match your
own asset. The output is a frontier, not a single answer — the choice of how
many misses is acceptable belongs to the engineer signing the report, not to
the model.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
SWEEP = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.70]


def gather(directory: Path, limit: int | None = None) -> list[Path]:
    files = sorted(f for f in directory.rglob("*")
                   if f.suffix.lower() in IMAGE_SUFFIXES and f.is_file())
    return files[:limit] if limit else files


def clean_from_empty_labels(root: Path) -> list[Path]:
    """Images whose label file is empty — defect-free by the annotator."""
    out = []
    for split in ("train", "valid", "test"):
        images, labels = root / split / "images", root / split / "labels"
        if not images.is_dir():
            continue
        for image in sorted(images.iterdir()):
            if image.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            label = labels / (image.stem + ".txt")
            if label.is_file() and not any(l.strip() for l in label.read_text().splitlines()):
                out.append(image)
    return out


def max_confidence(model, files: list[Path], imgsz: int, device: str) -> list[float]:
    """Highest-confidence detection per image, 0.0 if the model found nothing.

    Per-image rather than per-box on purpose: an inspector triages photographs,
    so what matters operationally is whether an image gets surfaced at all.
    """
    scores: list[float] = []
    for start in range(0, len(files), 32):
        batch = files[start:start + 32]
        for result in model.predict([str(f) for f in batch], conf=0.05,
                                    imgsz=imgsz, device=device, verbose=False):
            confs = [float(b.conf[0]) for b in result.boxes]
            scores.append(max(confs) if confs else 0.0)
    return scores


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--weights", required=True)
    p.add_argument("--defective", required=True, type=Path)
    p.add_argument("--clean", type=Path)
    p.add_argument("--clean-from-empty-labels", type=Path)
    p.add_argument("--prevalence", type=float, default=0.12,
                   help="Fraction of surveyed images that genuinely contain a defect")
    p.add_argument("--survey-size", type=int, default=500,
                   help="Photographs in one simulated survey")
    p.add_argument("--trials", type=int, default=400)
    p.add_argument("--review-seconds", type=float, default=30,
                   help="Engineer time to triage one flagged photograph")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="0")
    p.add_argument("--limit", type=int)
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--json", type=Path, help="Also write the frontier as JSON")
    args = p.parse_args()

    defective = gather(args.defective, args.limit)
    if args.clean_from_empty_labels:
        clean = clean_from_empty_labels(args.clean_from_empty_labels)
    elif args.clean:
        clean = gather(args.clean, args.limit)
    else:
        sys.exit("need --clean or --clean-from-empty-labels")
    if args.limit:
        clean = clean[:args.limit]
    if not defective or not clean:
        sys.exit("need both defective and clean imagery")

    from ultralytics import YOLO

    model = YOLO(args.weights)
    print(f"scoring {len(defective)} defective and {len(clean)} clean images...")
    def_scores = max_confidence(model, defective, args.imgsz, args.device)
    clean_scores = max_confidence(model, clean, args.imgsz, args.device)

    rng = random.Random(args.seed)
    n_def = round(args.survey_size * args.prevalence)
    n_clean = args.survey_size - n_def

    print(f"\nSimulated survey: {args.survey_size} photographs, "
          f"{args.prevalence:.0%} defect prevalence "
          f"({n_def} defective, {n_clean} clean), {args.trials} trials")
    print(f"Review cost: {args.review_seconds:.0f}s per flagged photograph\n")

    header = (f"  {'conf':>5} {'recall':>8} {'missed':>8} {'flagged':>9} "
              f"{'precision':>10} {'review':>9}")
    print(header)
    print("  " + "-" * (len(header) - 2))

    rows = []
    for t in SWEEP:
        missed_t = flagged_t = tp_t = 0.0
        for _ in range(args.trials):
            picked_def = [rng.choice(def_scores) for _ in range(n_def)]
            picked_clean = [rng.choice(clean_scores) for _ in range(n_clean)]
            tp = sum(s >= t for s in picked_def)
            fp = sum(s >= t for s in picked_clean)
            tp_t += tp
            missed_t += n_def - tp
            flagged_t += tp + fp
        missed = missed_t / args.trials
        flagged = flagged_t / args.trials
        tp = tp_t / args.trials
        recall = tp / n_def if n_def else 0.0
        precision = tp / flagged if flagged else 0.0
        hours = flagged * args.review_seconds / 3600
        rows.append({"conf": t, "recall": recall, "missed": missed,
                     "flagged": flagged, "precision": precision, "hours": hours})
        print(f"  {t:>5.2f} {recall:>7.1%} {missed:>8.1f} {flagged:>9.1f} "
              f"{precision:>9.1%} {hours:>8.1f}h")

    print("\n  missed   = real defects the survey does not surface. This is the"
          "\n             number that matters; the others are cost.")
    print("  flagged  = photographs a human has to look at.")
    print("  review   = engineer-hours to triage them, at "
          f"{args.review_seconds:.0f}s each.\n")

    # Recommend by recall target rather than by any symmetric score. A
    # screening pass exists to not miss things; the cheapest threshold that
    # meets the safety bar is the right one, and if none does, say so.
    for target in (0.95, 0.90, 0.80):
        ok = [r for r in rows if r["recall"] >= target]
        if ok:
            best = min(ok, key=lambda r: r["flagged"])
            print(f"  For {target:.0%} recall: conf {best['conf']:.2f} — "
                  f"misses {best['missed']:.1f} of {n_def}, "
                  f"flags {best['flagged']:.0f} photographs "
                  f"({best['hours']:.1f}h review)")
        else:
            print(f"  For {target:.0%} recall: NOT ACHIEVABLE at any threshold "
                  f"on this imagery.")

    if args.json:
        args.json.write_text(json.dumps(
            {"survey_size": args.survey_size, "prevalence": args.prevalence,
             "rows": rows}, indent=2))
        print(f"\n  wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
