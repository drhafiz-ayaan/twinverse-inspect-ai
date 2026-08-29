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

## Preparing a set

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
