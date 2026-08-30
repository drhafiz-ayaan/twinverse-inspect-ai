#!/usr/bin/env python3
"""Merge several single-class YOLO datasets into one.

Built for combining crack datasets that label the same concept under different
names (`crack`, `Concrete-Crack`). Every source class is remapped to index 0.

Sources must be single-class. A multi-class source is rejected rather than
silently flattened — collapsing distinct defect types into one label is how
you end up training a model that calls a stain a crack.

Usage:
    python ml/merge_datasets.py --output ml/datasets/crack-merged \\
        --train ml/datasets/nitw-crack/train ml/datasets/crack-b/train \\
        --val   ml/datasets/nitw-crack/valid \\
        --test  ml/datasets/nitw-crack/test ml/datasets/crack-b/test

Files are symlinked, not copied — image datasets run to gigabytes and there is
no reason to hold two copies. Names are prefixed with the source directory so
collisions between datasets cannot silently drop images.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--output", required=True, help="Destination dataset root")
    p.add_argument("--train", nargs="+", required=True,
                   help="Source split directories (each holding images/ and labels/)")
    p.add_argument("--val", nargs="+", required=True)
    p.add_argument("--test", nargs="*", default=[])
    p.add_argument(
        "--backgrounds-from", nargs="*", default=[],
        help="Split directories to take ONLY defect-free images from (those "
             "with an empty label file), added to train. Backgrounds carry no "
             "annotations, so they import no labelling convention — this is "
             "how to borrow from a dataset whose boxes would conflict.",
    )
    p.add_argument("--class-name", default="crack",
                   help="Name for the single merged class (default: crack)")
    p.add_argument("--copy", action="store_true",
                   help="Copy files instead of symlinking")
    return p.parse_args()


def source_tag(split_dir: Path) -> str:
    """A short prefix identifying the originating dataset."""
    return split_dir.resolve().parent.name


def check_single_class(split_dir: Path) -> set[str]:
    """Return the class indices used, refusing anything but a single class."""
    labels = split_dir / "labels"
    indices: set[str] = set()
    for label in labels.glob("*.txt"):
        for line in label.read_text().splitlines():
            if line.strip():
                indices.add(line.split()[0])
    if len(indices) > 1:
        sys.exit(
            f"{split_dir} uses class indices {sorted(indices)}.\n"
            "  Only single-class sources can be merged. Flattening several "
            "defect types\n  into one label trains the model to confuse them."
        )
    return indices


def link(src: Path, dst: Path, copy: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    if copy:
        import shutil

        shutil.copy2(src, dst)
    else:
        dst.symlink_to(src.resolve())


def merge_split(sources: list[Path], out_root: Path, split: str,
                copy: bool) -> tuple[int, int, int]:
    """Returns (images, annotations, background_images)."""
    images = annotations = backgrounds = 0

    for src in sources:
        tag = source_tag(src)
        img_dir, lbl_dir = src / "images", src / "labels"
        if not img_dir.is_dir():
            sys.exit(f"no images/ directory under {src}")
        check_single_class(src)

        for image in sorted(img_dir.iterdir()):
            if image.suffix.lower() not in IMAGE_SUFFIXES or not image.is_file():
                continue
            stem = f"{tag}__{image.stem}"
            link(image, out_root / "images" / split / f"{stem}{image.suffix}", copy)
            images += 1

            label = lbl_dir / f"{image.stem}.txt"
            target = out_root / "labels" / split / f"{stem}.txt"
            if label.is_file():
                lines = [
                    l for l in label.read_text().splitlines() if l.strip()
                ]
                # Every source is single-class, so index 0 is already correct;
                # rewritten explicitly so the merged labels never depend on the
                # source's numbering.
                rewritten = "\n".join("0 " + " ".join(l.split()[1:]) for l in lines)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(rewritten + ("\n" if rewritten else ""))
                annotations += len(lines)
                if not lines:
                    backgrounds += 1
            else:
                # No label file at all is a background image, same as an empty
                # one. Written explicitly so YOLO does not warn about it.
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("")
                backgrounds += 1

    return images, annotations, backgrounds


def main() -> int:
    args = parse_args()
    out = Path(args.output).expanduser().resolve()

    splits = {
        "train": [Path(p) for p in args.train],
        "val": [Path(p) for p in args.val],
    }
    if args.test:
        splits["test"] = [Path(p) for p in args.test]

    print(f"merging into {out}\n")
    stats: dict[str, tuple[int, int, int]] = {}
    for split, sources in splits.items():
        for s in sources:
            if not s.is_dir():
                sys.exit(f"source not found: {s}")
        stats[split] = merge_split(sources, out, split, args.copy)
        imgs, annots, bg = stats[split]
        names = ", ".join(source_tag(s) for s in sources)
        print(f"  {split:5}  {imgs:5} images  {annots:5} annotations  "
              f"{bg:4} backgrounds   <- {names}")

    for src in (Path(p) for p in args.backgrounds_from):
        if not src.is_dir():
            sys.exit(f"backgrounds source not found: {src}")
        tag = source_tag(src)
        added = 0
        for label in sorted((src / "labels").glob("*.txt")):
            if label.stat().st_size > 0:
                continue
            for suffix in IMAGE_SUFFIXES:
                image = src / "images" / f"{label.stem}{suffix}"
                if image.is_file():
                    stem = f"{tag}_bg__{image.stem}"
                    link(image, out / "images" / "train" / f"{stem}{suffix}", copy=args.copy)
                    (out / "labels" / "train" / f"{stem}.txt").write_text("")
                    added += 1
                    break
        imgs, annots, bg = stats["train"]
        stats["train"] = (imgs + added, annots, bg + added)
        print(f"  train  +{added:4} backgrounds (no annotations)   <- {tag}")

    yaml_path = out / "data.yaml"
    lines = [
        "# Generated by ml/merge_datasets.py — do not edit by hand.",
        f"path: {out}",
        "train: images/train",
        "val: images/val",
    ]
    if "test" in stats:
        lines.append("test: images/test")
    lines += ["nc: 1", "names:", f"  0: {args.class_name}", ""]
    yaml_path.write_text("\n".join(lines))

    total_imgs = sum(s[0] for s in stats.values())
    total_bg = sum(s[2] for s in stats.values())
    print(f"\ntotal: {total_imgs} images, {total_bg} backgrounds "
          f"({total_bg / total_imgs:.1%})")
    print(f"data.yaml: {yaml_path}")
    print(f"\ntrain with:\n  python ml/train.py --data {yaml_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
