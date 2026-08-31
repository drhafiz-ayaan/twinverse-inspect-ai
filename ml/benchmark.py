#!/usr/bin/env python3
"""Score a checkpoint against every held-out test split, in one table.

One dataset's test split tells you almost nothing about how a detector behaves
on someone else's photographs — that is the finding in README D-019. This runs
the same evaluation across each source's held-out split and prints them side by
side, so a change that helps one source and wrecks another cannot hide behind a
single average.

    python ml/benchmark.py --weights ml/weights/<model>.pt

Every set named below is images the model was **not** trained on. The clean set
is the same throughout, so the false-positive column is comparable across rows.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLEAN = REPO_ROOT / "ml" / "datasets" / "concrete-bridge-defect"

# source name -> directory of its annotated, never-trained-on test images
SETS = {
    "nitw-crack":    "_test_nitw",
    "crack-bphdr":   "_test_bphdr",
    "crack-b":       "_test_crackb",
    "bridge-defect": "_test_cbd",
}

# Which sources the checkpoint under test was trained on. This cannot be read
# from a .pt file, and getting it wrong turns the table into a false claim — an
# "unseen source" row the model actually trained on is precisely the
# overstatement this benchmark exists to prevent. So it is an explicit
# argument, defaulting to the current training set.
DEFAULT_TRAINED_ON = "nitw-crack,crack-bphdr,crack-b"

NUM = r"([0-9.]+)"


def run(weights: Path, defective: Path, device: str) -> dict[str, str]:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "ml" / "evaluate.py"),
         "--weights", str(weights),
         "--defective", str(defective),
         "--clean-from-empty-labels", str(CLEAN),
         "--device", device],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip().splitlines()[-1] if proc.stderr else "failed"}

    out = proc.stdout
    # Two tables share a column layout; the clean one comes first.
    rates = re.findall(rf"^\s+0\.30\s+\d+\s+{NUM}%", out, re.M)
    margin = re.search(rf"best margin \(detect - false alarm\):\s*{NUM}", out)
    verdict = re.search(r"verdict:\s*(\S+)", out)
    return {
        "fp": rates[0] if len(rates) > 0 else "—",
        "detect": rates[1] if len(rates) > 1 else "—",
        "margin": margin.group(1) if margin else "—",
        "verdict": verdict.group(1) if verdict else "—",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--weights", required=True, type=Path)
    p.add_argument("--device", default="0")
    p.add_argument("--trained-on", default=DEFAULT_TRAINED_ON,
                   help="Comma-separated sources this checkpoint trained on "
                        f"(default: {DEFAULT_TRAINED_ON})")
    args = p.parse_args()

    if not args.weights.is_file():
        sys.exit(f"no checkpoint at {args.weights}")

    trained = {s.strip() for s in args.trained_on.split(",") if s.strip()}
    unknown = trained - set(SETS)
    if unknown:
        sys.exit(f"--trained-on names unknown sources: {', '.join(sorted(unknown))}")

    print(f"\n{args.weights.name}   (held-out splits only, conf 0.30)\n")
    print(f"  {'source':<15} {'note':<14} {'detect':>8} {'false+':>8} "
          f"{'separation':>11}  verdict")
    print(f"  {'-' * 15} {'-' * 14} {'-' * 8} {'-' * 8} {'-' * 11}  {'-' * 10}")

    for name, folder in SETS.items():
        note = "in training" if name in trained else "UNSEEN SOURCE"
        target = REPO_ROOT / "ml" / "datasets" / folder
        if not target.is_dir():
            print(f"  {name:<15} {'missing':<14}")
            continue
        r = run(args.weights, target, args.device)
        if "error" in r:
            print(f"  {name:<15} {note:<14} {r['error']}")
            continue
        print(f"  {name:<15} {note:<14} {r['detect'] + '%':>8} {r['fp'] + '%':>8} "
              f"{r['margin']:>11}  {r['verdict']}")

    unseen = [n for n in SETS if n not in trained]
    print("\n  'in training' means other splits of that source were trained on;"
          "\n  these images were not. Unseen sources here: "
          + (", ".join(unseen) if unseen else "none") + ".")
    if "bridge-defect" in unseen:
        print("  bridge-defect labels a class of 'defect' rather than 'crack',"
              "\n  so some of what it marks is outside what this model does.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
