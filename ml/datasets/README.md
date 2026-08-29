# Datasets

Dataset contents are **gitignored** — they are large and re-downloadable, but
re-downloading costs hours, so back them up separately from the repo.

The README's guidance applies: **pick one asset type and go deep.** A demo that
convincingly nails concrete cracks beats one that half-detects five defect
classes across five asset types.

## Recommended starting point

**Concrete bridge and building defects.** Clear public data, high real-world
relevance, and visually legible in a demo — a judge can see the crack.

## Candidate sources

| Source | Contents | Format | Notes |
|---|---|---|---|
| **SDNET2018** | ~56k concrete crack images — decks, walls, pavement | Classification (cracked / uncracked) | **No bounding boxes.** Needs labelling before detection training, or use for a classifier baseline. |
| **CrackForest (CFD)** | 118 road crack images | Segmentation masks | Small; masks convert to boxes but the count is low for detection. |
| **Roboflow Universe** | Several crack and corrosion sets | **YOLO format, pre-labelled** | Fastest path to a trainable set. Check each set's licence. |
| **Kaggle** | Surface crack, corrosion/rust sets | Mixed | Quality varies considerably between sets. |

**The trap worth naming:** SDNET2018 is the most cited dataset here and the
first one most people reach for, but it is a *classification* dataset. Detection
training needs boxes. Either budget for labelling, or start with a Roboflow set
that already has them. The README puts Phase 2 at 2–4 days with the risk being
"dataset quality, not compute" — this is that risk, concretely.

## Fetching from Roboflow (recommended path)

```bash
python ml/fetch_dataset.py --url https://universe.roboflow.com/<workspace>/<project>/dataset/<version>
```

The API key is read from `ROBOFLOW_API_KEY` in the environment or
`backend/.env`. It is **never printed, logged, or written to disk** by the
script — including in error messages, which report the exception type rather
than echoing a failed request.

Get a key from app.roboflow.com → Settings → API Keys. Put it in
`backend/.env` (gitignored), **never** in `backend/.env.example`, which is
committed.

The script also:

- **Rewrites `data.yaml` split paths to absolute.** Roboflow emits relative
  paths like `../train/images` that resolve against the working directory —
  the single most common cause of a "dataset not found" failure once training
  is launched from the repo root rather than the dataset folder.
- **Reports the dataset's class names** and flags any that the detector would
  discard, importing the alias table from
  [`inference.py`](../../backend/app/services/inference.py) so there is one
  source of truth rather than two lists that drift.
- **Warns if `ROBOFLOW_API_KEY` is defined more than once** in `.env`. dotenv
  lets the last definition silently win, so a stale placeholder below a real
  key shadows it and the only symptom is an auth failure pointing nowhere.

Roboflow exports arrive already split into train/valid/test with a `data.yaml`,
so `prepare_dataset.py` is **not** needed afterwards — go straight to training.

## Preparing a set from another source

`prepare_dataset.py` is for **flat, unsplit** datasets — Kaggle downloads,
manually labelled sets, anything that is not already organised into splits.
Once a YOLO-format dataset is downloaded:

```bash
python ml/prepare_dataset.py --source ~/downloads/concrete-cracks --output ml/datasets/concrete --classes crack corrosion surface_damage
```

Class names should match the aliases in
[`backend/app/services/inference.py`](../../backend/app/services/inference.py).
Names outside that table are **discarded rather than guessed at** — a model
class of `person` silently filed under `crack` would corrupt every downstream
severity number.

The script prints per-class instance counts. A class showing zero instances
almost always means the label indices do not line up with the `--classes` order.

## Training

```bash
python ml/train.py --data ml/datasets/concrete/data.yaml --epochs 100
```

Checkpoints land in `ml/weights/`. Point the API at one:

```bash
MODEL_WEIGHTS=/abs/path/to/ml/weights/defect-detector.pt
```

Weights are gitignored too — use Git LFS or attach them to a GitHub Release.
