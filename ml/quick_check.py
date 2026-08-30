#!/usr/bin/env python3
"""Fast go/no-go on a training idea — minutes instead of an hour.

Trains a small model on a subsample for a handful of epochs, then runs the
same clean-vs-defective separation test as a full evaluation. The point is to
find out whether an approach is *directionally* working before committing the
GPU to a full run.

This exists because of D-016: the first fine-tune took an hour to reach mAP50
0.442, and only then did testing on defect-free imagery reveal it fired on
88% of clean surfaces. mAP looked survivable the whole way; the failure was
invisible until the false-positive test ran. That test is cheap — so run it
first, on a small sample, and stop early when the answer is obviously no.

What a quick check CAN tell you:
  - the pipeline runs end to end and loss decreases
  - whether clean and defective confidences separate at all
  - roughly where a usable threshold might sit

What it CANNOT tell you:
  - final accuracy. A weak separation here may improve with full data; a
    strong one will not necessarily hold. Treat it as a smoke test, not a
    prediction.

Usage:
    python ml/quick_check.py \\
        --data ml/datasets/crack-merged/data.yaml \\
        --clean-from-empty-labels ml/datasets/concrete-bridge-defect
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import random
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUICK_ROOT = REPO_ROOT / "ml" / "runs" / "_quick"


def load_evaluate_module():
    spec = importlib.util.spec_from_file_location(
        "evaluate", REPO_ROOT / "ml" / "evaluate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--data", required=True, help="data.yaml of the full dataset")
    p.add_argument("--clean-from-empty-labels", required=True,
                   help="Dataset root supplying held-out defect-free images")
    p.add_argument("--sample", type=int, default=400,
                   help="Training images to sample (default: 400)")
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--model", default="yolo11n.pt",
                   help="Small model for speed (default: yolo11n.pt)")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--device", default="0")
    p.add_argument("--clean-limit", type=int, default=94)
    p.add_argument("--defective-limit", type=int, default=150)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--tag", help="Label for this run's working directory. "
                                 "Defaults to the dataset name. Two runs "
                                 "sharing a tag will overwrite each other.")
    p.add_argument("--keep", action="store_true",
                   help="Keep the temporary dataset and run directory")
    return p.parse_args()


def resolve_split(data_yaml: Path, key: str) -> Path | None:
    import yaml

    config = yaml.safe_load(data_yaml.read_text())
    value = config.get(key)
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = Path(str(config.get("path", data_yaml.parent))) / path
    return path if path.is_dir() else None


def label_path_for(image: Path) -> Path:
    """Map an image path to its YOLO label path.

    Uses the same rule Ultralytics does — swap the last `/images/` segment for
    `/labels/` — because both directory layouts are in use here:

        train/images/x.jpg  ->  train/labels/x.txt   (Roboflow export)
        images/train/x.jpg  ->  labels/train/x.txt   (merge_datasets.py output)

    Deriving it as `images_dir.parent / "labels"` only handles the first, and
    silently yields empty labels for the second — which trains a model on
    images with no annotations and looks like a bad model rather than a bug.
    """
    parts = str(image)
    sa, sb = f"{os.sep}images{os.sep}", f"{os.sep}labels{os.sep}"
    if sa in parts:
        parts = sb.join(parts.rsplit(sa, 1))
    return Path(parts).with_suffix(".txt")


def subsample(images_dir: Path, out_root: Path, split: str, n: int,
              seed: int) -> tuple[int, int, int]:
    """Symlink a random sample of images plus labels.

    Returns (images, backgrounds, annotations).
    """
    ev = load_evaluate_module()
    images = ev.gather_images(images_dir)
    random.Random(seed).shuffle(images)
    chosen = images[:n]

    backgrounds = annotations = 0
    for image in chosen:
        dst_img = out_root / "images" / split / image.name
        dst_img.parent.mkdir(parents=True, exist_ok=True)
        if dst_img.exists() or dst_img.is_symlink():
            dst_img.unlink()
        dst_img.symlink_to(image.resolve())

        label = label_path_for(image)
        dst_lbl = out_root / "labels" / split / f"{image.stem}.txt"
        dst_lbl.parent.mkdir(parents=True, exist_ok=True)
        content = label.read_text() if label.is_file() else ""
        dst_lbl.write_text(content)
        lines = [l for l in content.splitlines() if l.strip()]
        annotations += len(lines)
        if not lines:
            backgrounds += 1

    return len(chosen), backgrounds, annotations


def main() -> int:
    args = parse_args()
    started = time.time()

    data_yaml = Path(args.data).resolve()
    if not data_yaml.is_file():
        sys.exit(f"data.yaml not found: {data_yaml}")

    train_dir = resolve_split(data_yaml, "train")
    val_dir = resolve_split(data_yaml, "val")
    if train_dir is None or val_dir is None:
        sys.exit(f"could not resolve train/val image directories from {data_yaml}")

    import yaml

    class_name = "crack"
    config = yaml.safe_load(data_yaml.read_text())
    names = config.get("names")
    if isinstance(names, dict) and names:
        class_name = list(names.values())[0]
    elif isinstance(names, list) and names:
        class_name = names[0]

    # Per-run directory so concurrent or repeated checks cannot clobber each
    # other's sampled dataset and checkpoint.
    tag = args.tag or data_yaml.parent.name
    run_root = QUICK_ROOT / tag
    work = run_root / "dataset"
    if work.exists():
        shutil.rmtree(work)

    n_train, bg_train, ann_train = subsample(
        train_dir, work, "train", args.sample, args.seed
    )
    n_val, bg_val, ann_val = subsample(
        val_dir, work, "val", max(60, args.sample // 4), args.seed
    )

    # Guard against the failure that produced this check: silently empty
    # labels train a model on nothing and the result reads as a bad model
    # rather than a broken sample.
    if ann_train == 0:
        sys.exit(
            f"sampled {n_train} training images but found 0 annotations.\n"
            f"  Looked for labels beside: {train_dir}\n"
            f"  Example expected path   : {label_path_for(next(iter(load_evaluate_module().gather_images(train_dir))))}\n"
            "  Every label came back empty, so training would learn nothing.\n"
            "  Check the dataset's images/ and labels/ directory layout."
        )
    if bg_train == n_train:
        sys.exit(f"all {n_train} sampled training images are backgrounds")

    quick_yaml = work / "data.yaml"
    quick_yaml.write_text(
        f"path: {work}\ntrain: images/train\nval: images/val\n"
        f"nc: 1\nnames:\n  0: {class_name}\n"
    )

    print("=" * 62)
    print("QUICK CHECK — smoke test, not a prediction")
    print("=" * 62)
    print(f"  sampled   : {n_train} train ({bg_train} bg, {ann_train} annotations), {n_val} val")
    print(f"  model     : {args.model}   epochs: {args.epochs}")
    print()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=str(quick_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(run_root),
        name="run",
        exist_ok=True,
        plots=False,
        verbose=False,
    )

    ev = load_evaluate_module()
    weights = run_root / "run" / "weights" / "best.pt"
    if not weights.is_file():
        sys.exit(f"training produced no checkpoint at {weights}")

    trained = YOLO(str(weights))
    thresholds = ev.DEFAULT_SWEEP
    lowest = thresholds[0]

    clean_images = ev.gather_empty_label_images(
        Path(args.clean_from_empty_labels), args.clean_limit
    )
    defective_images = ev.gather_images(val_dir, args.defective_limit)

    if not clean_images:
        sys.exit("no defect-free images found — cannot measure separation")

    clean = ev.run(trained, clean_images, args.imgsz, args.device, lowest)
    defective = ev.run(trained, defective_images, args.imgsz, args.device, lowest)

    ev.report("CLEAN SURFACES", clean, thresholds, clean=True)
    ev.report("DEFECTIVE SURFACES", defective, thresholds, clean=False)
    j = ev.report_separation(clean, defective, thresholds)

    elapsed = time.time() - started
    print("\n" + "=" * 62)
    print(f"quick check finished in {elapsed / 60:.1f} min")
    if j < 0:
        # Silent model: no detections at all. Says nothing about the approach.
        print(f"  -> INCONCLUSIVE. {args.epochs} epochs on {n_train} images was")
        print("     not enough for the model to start detecting anything.")
        print("     Re-run with more, e.g. --sample 600 --epochs 30.")
    elif j < 0.15:
        print("  -> DO NOT launch a full run on this configuration.")
        print("     Change something structural: more/better data, background")
        print("     images, or a different task formulation (segmentation fits")
        print("     thin diagonal cracks far better than boxes).")
    elif j < 0.35:
        print("  -> Weak. A full run may improve it, but expect the same")
        print("     failure mode at larger scale. Consider fixing the data first.")
    else:
        print("  -> Promising enough to justify a full run.")
    print(f"\n  reference: the D-016 baseline scored 0.258 on this test after a")
    print("  full hour of training. Beat that, or the extra time is wasted.")
    print("=" * 62)

    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
