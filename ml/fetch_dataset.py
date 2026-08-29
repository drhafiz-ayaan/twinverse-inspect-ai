#!/usr/bin/env python3
"""Download a Roboflow Universe dataset in YOLO format.

The API key is read from the environment (or backend/.env) and is never
printed, logged, or written to disk by this script.

Usage — from a Universe URL:
    python ml/fetch_dataset.py --url https://universe.roboflow.com/acme/concrete-cracks/dataset/3

Usage — explicit coordinates:
    python ml/fetch_dataset.py --workspace acme --project concrete-cracks --version 3

Roboflow exports already contain train/valid/test splits and a data.yaml, so
ml/prepare_dataset.py is NOT needed afterwards — that script is for flat,
unsplit datasets from other sources.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "ml" / "datasets"
ENV_FILE = REPO_ROOT / "backend" / ".env"

# Roboflow's export format identifier. yolov8 and yolov11 produce the same
# on-disk layout; many Universe projects only offer the older identifier, so it
# is a valid fallback rather than a downgrade.
DEFAULT_FORMAT = "yolov11"

URL_PATTERN = re.compile(
    r"universe\.roboflow\.com/"
    r"(?P<workspace>[^/]+)/"
    r"(?P<project>[^/]+)"
    r"(?:/(?:dataset|model)/(?P<version>\d+))?"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    src = p.add_argument_group("dataset location")
    src.add_argument("--url", help="Roboflow Universe dataset URL")
    src.add_argument("--workspace", help="Workspace slug")
    src.add_argument("--project", help="Project slug")
    src.add_argument("--version", type=int, help="Dataset version number")

    p.add_argument("--format", default=DEFAULT_FORMAT,
                   help=f"Export format (default: {DEFAULT_FORMAT}; try yolov8 "
                        "if the project does not offer it)")
    p.add_argument("--output", help="Destination directory "
                                    "(default: ml/datasets/<project>)")
    return p.parse_args()


def resolve_target(args: argparse.Namespace) -> tuple[str, str, int | None]:
    """Work out workspace/project/version from a URL or explicit flags."""
    if args.url:
        match = URL_PATTERN.search(args.url)
        if not match:
            sys.exit(
                "could not parse that URL.\n"
                "Expected something like:\n"
                "  https://universe.roboflow.com/<workspace>/<project>/dataset/<version>\n"
                "Or pass --workspace/--project/--version explicitly."
            )
        version = match.group("version")
        return (
            match.group("workspace"),
            match.group("project"),
            int(version) if version else args.version,
        )

    if not (args.workspace and args.project):
        sys.exit("supply --url, or both --workspace and --project")
    return args.workspace, args.project, args.version


def warn_on_duplicate_definitions() -> None:
    """Flag a variable defined more than once in .env.

    dotenv silently lets the *last* definition win, so a stale placeholder
    below a real key shadows it and the only symptom is an authentication
    failure that points nowhere useful.
    """
    if not ENV_FILE.is_file():
        return
    hits = [
        n
        for n, line in enumerate(ENV_FILE.read_text().splitlines(), 1)
        if line.strip().startswith("ROBOFLOW_API_KEY=")
    ]
    if len(hits) > 1:
        print(
            f"! ROBOFLOW_API_KEY is defined {len(hits)} times in {ENV_FILE.name} "
            f"(lines {', '.join(map(str, hits))}).\n"
            f"  The last one wins — line {hits[-1]} is the one in effect.\n"
            f"  Delete the duplicates.\n",
            file=sys.stderr,
        )


def load_api_key() -> str:
    """Read the key from the environment, falling back to backend/.env.

    Deliberately never echoes the value — not in errors, not in success output.
    """
    warn_on_duplicate_definitions()
    key = os.environ.get("ROBOFLOW_API_KEY", "").strip()

    if not key and ENV_FILE.is_file():
        try:
            from dotenv import dotenv_values

            key = (dotenv_values(ENV_FILE).get("ROBOFLOW_API_KEY") or "").strip()
        except ImportError:
            pass

    if not key or key.startswith("rf_replace_me"):
        sys.exit(
            "ROBOFLOW_API_KEY is not set.\n\n"
            f"  Put it in {ENV_FILE} (gitignored):\n"
            "      ROBOFLOW_API_KEY=your_key_here\n\n"
            "  Or export it for one command:\n"
            "      ROBOFLOW_API_KEY=... python ml/fetch_dataset.py ...\n\n"
            "  Get a key from app.roboflow.com -> Settings -> API Keys.\n"
            "  Never put it in backend/.env.example - that file is committed."
        )
    return key


def known_defect_aliases() -> set[str] | None:
    """The alias table from the inference service, if it can be imported.

    Imported rather than duplicated so there is one source of truth for which
    class names map onto a defect class. Returns None if the backend package is
    not importable, in which case the check is skipped rather than guessed at.
    """
    try:
        sys.path.insert(0, str(REPO_ROOT / "backend"))
        from app.services.inference import CLASS_ALIASES

        return set(CLASS_ALIASES)
    except Exception:
        return None


def report_classes(data_yaml: Path) -> None:
    """Show the dataset's classes and flag any that inference would discard."""
    try:
        import yaml

        config = yaml.safe_load(data_yaml.read_text())
    except Exception as exc:
        print(f"! could not read {data_yaml}: {exc}", file=sys.stderr)
        return

    names = config.get("names") or []
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names)]
    if not names:
        return

    print(f"\nclasses in this dataset ({len(names)}):")
    aliases = known_defect_aliases()
    unmapped: list[str] = []
    for name in names:
        key = str(name).strip().lower().replace("-", "_")
        if aliases is None:
            print(f"  - {name}")
        elif key in aliases:
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name}   <- will be DISCARDED by the detector")
            unmapped.append(str(name))

    if unmapped:
        print(
            "\n! "
            + ", ".join(repr(n) for n in unmapped)
            + " will not map to a defect class.\n"
            "  Detections for these are dropped rather than guessed at "
            "(README D-011).\n"
            "  Fix by adding aliases to CLASS_ALIASES in\n"
            "  backend/app/services/inference.py"
        )


def normalize_data_yaml(data_yaml: Path) -> None:
    """Rewrite split paths to absolute.

    Roboflow emits relative paths like `../train/images`, which resolve against
    the working directory and break the moment training is launched from
    anywhere other than the dataset folder. This is the single most common
    cause of a "dataset not found" failure mid-training.
    """
    try:
        import yaml

        config = yaml.safe_load(data_yaml.read_text())
    except Exception:
        return

    root = data_yaml.parent
    changed = False
    for split in ("train", "val", "test"):
        value = config.get(split)
        if not value or Path(str(value)).is_absolute():
            continue
        candidates = [
            root / str(value),
            root / str(value).lstrip("./").lstrip("../"),
            root / split / "images",
            root / "images" / split,
        ]
        for candidate in candidates:
            if candidate.is_dir():
                config[split] = str(candidate.resolve())
                changed = True
                break

    if changed:
        config["path"] = str(root.resolve())
        data_yaml.write_text(yaml.safe_dump(config, sort_keys=False))
        print(f"\nnormalized split paths to absolute in {data_yaml.name}")


def main() -> int:
    args = parse_args()
    workspace, project_slug, version = resolve_target(args)
    api_key = load_api_key()

    try:
        from roboflow import Roboflow
    except ImportError:
        sys.exit(
            "the roboflow package is not installed.\n"
            "  pip install -r ml/requirements.txt"
        )

    print(f"workspace : {workspace}")
    print(f"project   : {project_slug}")

    try:
        rf = Roboflow(api_key=api_key)
        project = rf.workspace(workspace).project(project_slug)
        selected = project.version(version) if version else project.versions()[0]
    except Exception as exc:
        # Never let an exception carry the key into the terminal.
        sys.exit(
            f"could not reach that Roboflow project: {type(exc).__name__}\n"
            "  Check the workspace/project slugs and that your API key is valid.\n"
            "  Slugs are the URL segments, not the display names."
        )

    output = Path(args.output).expanduser() if args.output else (
        DEFAULT_OUTPUT_ROOT / project_slug
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"version   : {getattr(selected, 'version', version)}")
    print(f"format    : {args.format}")
    print(f"output    : {output}\n")

    try:
        selected.download(args.format, location=str(output), overwrite=True)
    except Exception as exc:
        sys.exit(
            f"download failed: {type(exc).__name__}: {exc}\n"
            f"  If the format was rejected, try --format yolov8 "
            "(same layout, more widely offered)."
        )

    data_yaml = output / "data.yaml"
    if not data_yaml.is_file():
        found = list(output.rglob("data.yaml"))
        if found:
            data_yaml = found[0]

    if data_yaml.is_file():
        normalize_data_yaml(data_yaml)
        report_classes(data_yaml)
        print(f"\ndataset ready: {output}")
        print("\ntrain with:")
        print(f"  python ml/train.py --data {data_yaml}")
    else:
        print(f"\n! downloaded to {output} but no data.yaml was found — "
              "inspect the directory before training", file=sys.stderr)
        return 1

    print(
        "\nreminder: datasets are gitignored. Back this up separately — "
        "re-downloading costs hours."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
