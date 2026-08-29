#!/usr/bin/env python3
"""Fine-tune YOLOv11 on an infrastructure defect dataset.

Usage:
    python ml/train.py --data ml/datasets/concrete/data.yaml --epochs 100

The resulting checkpoint is written to ml/weights/. Point the API at it with:
    MODEL_WEIGHTS=/abs/path/to/ml/weights/best.pt

Defaults are tuned for the development machine in the README (RTX 3080 Laptop,
16 GB VRAM): YOLOv11s at 640 px with batch 16 leaves headroom. Raise the batch
size for the nano model, lower it for medium.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS_DIR = REPO_ROOT / "ml" / "weights"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", required=True,
                   help="Path to the dataset data.yaml (YOLO format)")
    p.add_argument("--model", default="yolo11s.pt",
                   help="Base checkpoint to fine-tune from (default: yolo11s.pt)")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16,
                   help="Lower this if you hit CUDA out-of-memory")
    p.add_argument("--device", default="0",
                   help='CUDA index, or "cpu"')
    p.add_argument("--patience", type=int, default=25,
                   help="Early-stopping patience in epochs")
    p.add_argument("--name", default="defect-detector",
                   help="Run name under ml/runs/")
    p.add_argument("--resume", action="store_true",
                   help="Resume the most recent interrupted run")
    return p.parse_args()


def check_gpu(device: str) -> None:
    """Fail loudly rather than silently training on CPU for a week.

    README D-002 exists precisely because a stale driver made the GPU invisible
    to PyTorch. A run that quietly falls back to CPU is the same failure wearing
    a different hat.
    """
    if device == "cpu":
        print("! device=cpu requested — training will be very slow", file=sys.stderr)
        return

    import torch

    if not torch.cuda.is_available():
        sys.exit(
            "CUDA is not available to PyTorch.\n"
            "  Check: nvidia-smi\n"
            "  Check: python -c 'import torch; print(torch.cuda.is_available())'\n"
            "  Pass --device cpu to train anyway (slow)."
        )
    name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"GPU: {name} ({vram:.1f} GB)")


def main() -> int:
    args = parse_args()

    data_path = Path(args.data).resolve()
    if not data_path.is_file():
        sys.exit(f"dataset config not found: {data_path}\n"
                 "Run ml/prepare_dataset.py first, or see ml/datasets/README.md")

    check_gpu(args.device)

    from ultralytics import YOLO

    model = YOLO(args.model)
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        patience=args.patience,
        project=str(REPO_ROOT / "ml" / "runs"),
        name=args.name,
        exist_ok=True,
        resume=args.resume,
        plots=True,
    )

    # Copy the best checkpoint somewhere stable. The run directory gets a new
    # suffix on every re-run, so pointing the API at it directly would break.
    best = Path(results.save_dir) / "weights" / "best.pt"
    if best.is_file():
        DEFAULT_WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
        target = DEFAULT_WEIGHTS_DIR / f"{args.name}.pt"
        shutil.copy2(best, target)
        print(f"\nbest checkpoint -> {target}")
        print(f"point the API at it:\n  MODEL_WEIGHTS={target}")
    else:
        print(f"! expected checkpoint not found at {best}", file=sys.stderr)

    print(f"\nrun artifacts (curves, confusion matrix): {results.save_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
