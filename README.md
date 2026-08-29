# TwinVerse Inspect AI

**AI-Powered Infrastructure Intelligence Platform**

> Analyze images and videos from drones, CCTV, robots, or smartphones to automatically detect infrastructure defects — cracks, corrosion, surface damage, equipment faults — assess severity, generate maintenance insights, and visualize asset health through an interactive digital twin.

**Status:** **Phase 1 complete; Phase 2 pipeline complete, model not yet trained.** Environment verified ([Environment Status](#environment-status)); upload API and detection pipeline shipped with 47 passing integration tests. Inference runs on the GPU in 7 ms, but on COCO weights that do not detect defects — the remaining work is a labelled dataset and a fine-tune. See [Detection — Phase 2](#detection--phase-2) for the honest breakdown.
**Target:** Hackathon MVP (see [Scope Triage](#scope-triage--what-ships-and-what-does-not)).
**Repository:** `drhafiz-ayaan/twinverse-inspect-ai` (private)

---

## Table of Contents

- [Submission Description](#submission-description)
- [Vision](#vision)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Development Machine Profile](#development-machine-profile)
- [Environment Status](#environment-status)
- [Environment Setup — Ubuntu 24.04](#environment-setup--ubuntu-2404-noble)
- [Optional: ROS2 Jazzy + Gazebo Harmonic](#optional-ros2-jazzy--gazebo-harmonic--phase-6-not-mvp)
- [API — Phase 1](#api--phase-1)
- [Detection — Phase 2](#detection--phase-2)
- [Development Roadmap](#development-roadmap--effort-estimates)
- [Scope Triage](#scope-triage--what-ships-and-what-does-not)
- [Severity Scoring Model](#severity-scoring-model)
- [Datasets](#datasets)
- [Repository Structure](#planned-repository-structure)
- [Demo Strategy](#demo-strategy)
- [Decision Log](#decision-log)
- [Backup & Repository](#backup--repository)

---

## Submission Description

TwinVerse Inspect AI is an AI-powered Infrastructure Intelligence Platform that analyzes images and videos from drones, CCTV cameras, robots, or smartphones to automatically detect infrastructure defects such as cracks, corrosion, surface damage, and equipment faults. Using advanced computer vision and AI, the platform assesses defect severity, generates actionable maintenance insights, and visualizes asset health through an interactive digital twin. By enabling faster, safer, and more accurate inspections, it helps organizations reduce maintenance costs, improve safety, and transition from reactive to predictive infrastructure management.

---

## Vision

Infrastructure inspection today is manual, slow, dangerous, and inconsistent. Engineers climb bridges, rappel down dams, and walk pipelines with clipboards. TwinVerse Inspect AI replaces that first pass with automated visual analysis, so human experts spend their time on judgment rather than data collection.

The long-term goal is a shift from **reactive** maintenance (fix it after it fails) to **predictive** maintenance (fix it before it fails), driven by a continuously updated digital twin of each asset.

---

## System Architecture

```
Data Sources          Upload Service       AI Inference Engine
(drone / CCTV    ──>  (FastAPI +      ──>  (YOLOv11 / RT-DETR
 robot / phone)        object storage)      + OpenCV)
                                                   |
                                                   v
                            +------------------------------+
                            |  Defect Database (PostgreSQL) |
                            +------------------------------+
                                       |
                    +------------------+------------------+
                    v                  v                  v
            Severity Assessment   Dashboard         Digital Twin Viewer
            (heuristic scorer)    (Next.js)         (Three.js)
                    |                  |
                    +-------> Reports (PDF) <-------+
```

---

## Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React + Next.js | App Router, TypeScript |
| Backend | FastAPI (Python 3.12) | Async, auto OpenAPI docs |
| Database | PostgreSQL 16 | Via Docker |
| Object Storage | MinIO (S3-compatible) | Swappable for Alibaba Cloud OSS / AWS S3 |
| AI / CV | YOLOv11 (Ultralytics) + OpenCV | RT-DETR as alternative |
| 3D Visualization | Three.js | GLB asset + defect markers |
| Reports | ReportLab / WeasyPrint | PDF export |
| Deployment | Docker Compose + GitHub Actions | |
| Digital Twin (future) | Gaussian Splatting / NeRF | Out of MVP scope |
| Simulation (future) | Gazebo Harmonic, NVIDIA Isaac Sim | Out of MVP scope |

**Cloud note:** the S3-compatible storage layer means MinIO can be swapped for **Alibaba Cloud OSS** with a config change only. See [Demo Strategy](#demo-strategy) for cloud-sponsored events.

---

## Development Machine Profile

Captured so the environment can be reproduced after the OS migration.

| Component | Spec |
|---|---|
| Laptop | MSI GS66 Stealth 11UH |
| CPU | Intel Core i9-11900H — 8 cores / 16 threads |
| RAM | 32 GB |
| GPU | **NVIDIA GeForce RTX 3080 Laptop — 16 GB VRAM** (Ampere, GA104M) |
| iGPU | Intel UHD Graphics (Optimus hybrid + MUX switch present) |
| Storage | Multiple volumes, 150 GB+ free on primary |

**Assessment:** hardware is not a constraint. 16 GB of VRAM comfortably fine-tunes YOLOv11 s/m at 640px, and is above what most hackathon teams bring.

---

## Environment Status

Verified on the development machine **2026-08-30**. The [setup guide below](#environment-setup--ubuntu-2404-noble) remains the reproduction procedure for a fresh machine; this table is the current state of *this* one.

| Component | Verified state |
|---|---|
| OS | Ubuntu 24.04.4 LTS ✅ |
| NVIDIA driver | 580.173.02, CUDA 13.0 ✅ |
| GPU visible to `nvidia-smi` | RTX 3080 Laptop, 16384 MiB ✅ |
| Python | 3.12.3 ✅ |
| Docker engine | 29.1.3 installed ✅ |
| Git | 2.43.0 ✅ |
| Free disk | 153 GB ✅ |
| Python venv | ✅ `.venv/` — Python 3.12.3 |
| PyTorch | ✅ **2.13.0+cu130** — `torch.cuda.is_available()` returns `True` |
| GPU compute | ✅ verified — 4096² matmul, 6.3 TFLOP/s fp32, cuDNN 9.2 |
| Ultralytics / OpenCV | ✅ 8.4.135 / 5.0.0 |
| FastAPI / SQLAlchemy / Alembic | ✅ 0.141.1 / 2.0.52 / 1.19.1 |
| boto3 / ReportLab / pydantic-settings | ✅ installed |
| Dependency pinning | ✅ [`requirements.txt`](requirements.txt) — direct deps pinned, dry-run verified against this environment |
| Docker group membership | ✅ `ak` in `docker` group |
| Node.js | ✅ v20.20.2 / npm 10.8.2 (via nvm) |
| PostgreSQL container | ✅ `twinverse-pg` — Postgres 16.15, `twinverse` DB, port 5432 |
| MinIO container | ✅ `twinverse-minio` — health 200, console 9001, bucket `twinverse-inspections` |
| DB + storage from Python | ✅ verified end to end via SQLAlchemy/psycopg2 and boto3 |
| GPU mode (`prime-select`) | `on-demand` — switch to `nvidia` before training runs |
| GPU power cap | 80 W reported by `nvidia-smi`. Low for a GS66 3080; check the MSI power/thermal profile before benchmarking Phase 2 training throughput. |

### Remaining setup

**None — Phase 0 environment is complete.** Node was installed via **nvm** rather than the NodeSource method in step 4 below; it needs no root and avoids running a remote script under `sudo`.

One gotcha worth remembering: after `sudo usermod -aG docker $USER`, a shell that was already open still fails with a permission-denied socket error, because process credentials are fixed at login. Log out and back in, or prefix commands for the current session only:

```bash
sg docker -c "docker ps"
```

---

## Environment Setup — Ubuntu 24.04 (Noble)

> **Already done on this machine.** Steps 1–4 below are complete except for the docker group membership; step 5 is in progress. This section is retained as the reproduction procedure for a fresh install. See [Environment Status](#environment-status) for what actually remains.

### Read first: NVIDIA drivers are NOT preinstalled

Ubuntu 24.04 boots using the open-source **Nouveau** driver, which has **no CUDA support**. The proprietary driver must be installed manually. This is a one-command job, but it is not automatic.

**If Secure Boot is enabled**, the installer prompts you to create a MOK (Machine Owner Key) password, and you must **enroll the key on the next reboot** via the blue MOK Manager screen. Skipping that step silently leaves the driver unloaded and `nvidia-smi` will fail.

### 1. NVIDIA driver

```bash
sudo apt update && sudo apt upgrade -y
```

```bash
ubuntu-drivers devices
```

```bash
sudo ubuntu-drivers install
```

Reboot, then verify — this must print the GPU name and 16384 MiB:

```bash
nvidia-smi
```

If `ubuntu-drivers` picks an unexpected version, pin explicitly (Ampere supports the open kernel modules):

```bash
sudo apt install -y nvidia-driver-580-open
```

*(This machine resolved to **580.173.02 / CUDA 13.0** automatically. An earlier draft of this README suggested `nvidia-driver-570-open`; that is now older than the default and should not be used as a pin.)*

### 2. CUDA toolkit — you probably do NOT need it

PyTorch wheels bundle their own CUDA runtime. Installing the full CUDA toolkit is only necessary when compiling custom CUDA kernels. **Skip it.** The driver alone is enough.

### 3. Hybrid graphics (Optimus)

The GS66 has a MUX switch. To force the discrete GPU for training:

```bash
sudo prime-select nvidia
```

`sudo prime-select on-demand` restores battery-friendly hybrid mode. Reboot after either change.

### 4. Core toolchain

```bash
sudo apt install -y build-essential git curl wget python3.12 python3.12-venv python3-pip
```

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash && source ~/.bashrc && nvm install 20 && nvm alias default 20
```

Node 20 via **nvm**, chosen over the NodeSource `curl … | sudo -E bash -` method: it needs no root, does not execute a remote script as superuser, and makes version switching trivial. Ubuntu's own `apt install nodejs` is not used — Noble ships Node 18.19, which is end-of-life.

```bash
sudo apt install -y docker.io docker-compose-v2 && sudo usermod -aG docker $USER
```

Log out and back in for the docker group change to take effect.

### 5. Python environment

```bash
python3.12 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip
```

```bash
pip install -r requirements.txt
```

[`requirements.txt`](requirements.txt) pins the direct dependencies to the versions verified on this machine. Note it carries **no `--index-url`**: on Linux the default PyPI wheels are CUDA builds, and `torch==2.13.0` resolves to a `+cu130` wheel matching the installed 580 driver. An earlier draft pinned `--index-url https://download.pytorch.org/whl/cu124`, which would install a runtime *older* than the driver for no benefit. See [D-006](#d-006--nodejs-via-nvm-not-nodesource).

Verify the GPU is visible to PyTorch:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Expected output: `True NVIDIA GeForce RTX 3080 Laptop GPU`

### 6. Services

> **Local development credentials only.** `devpass` and `minioadmin/minioadmin` are fine on a laptop but must never reach a deployed environment — the proposal's security requirements call for encrypted secrets. Move these to `.env` (already gitignored) before Phase 6.

Both services mount a **named volume**. Without one, `docker rm` destroys the database — the container's writable layer is not persistent storage.

```bash
docker volume create twinverse_pgdata && docker volume create twinverse_miniodata
```

```bash
docker run -d --name twinverse-pg -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=twinverse -p 5432:5432 -v twinverse_pgdata:/var/lib/postgresql/data postgres:16
```

```bash
docker run -d --name twinverse-minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin -v twinverse_miniodata:/data quay.io/minio/minio server /data --console-address ":9001"
```

Verify both are serving:

```bash
docker exec twinverse-pg pg_isready -d twinverse -U postgres && curl -s -o /dev/null -w "minio %{http_code}\n" http://localhost:9000/minio/health/live
```

MinIO console: <http://localhost:9001> · Postgres DSN: `postgresql+psycopg2://postgres:devpass@localhost:5432/twinverse`

---

## Optional: ROS2 Jazzy + Gazebo Harmonic — Phase 6, NOT MVP

ROS2 is **not required for any MVP phase (1–5)**. It matters only for drone/robot integration and simulation. Install it after the MVP is demoable.

ROS2 **Jazzy Jalisco** is the distribution matched to Ubuntu 24.04, and pairs with **Gazebo Harmonic**.

```bash
sudo apt install -y ros-dev-tools ros-jazzy-desktop
```

```bash
source /opt/ros/jazzy/setup.bash
```

---

## API — Phase 1

FastAPI service under [`backend/`](backend). Asset and inspection records, plus image and video ingest into S3-compatible storage.

### Run it

```bash
source .venv/bin/activate && cd backend && alembic upgrade head
```

```bash
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Interactive docs at <http://localhost:8000/docs>. Requires the Postgres and MinIO containers from [setup step 6](#6-services).

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness — process is up, touches nothing |
| `GET` | `/health/ready` | Readiness — pings Postgres and object storage; **503** if either is down |
| `POST` `GET` | `/api/v1/assets` | Create / list assets (filter by `asset_type`) |
| `GET` `PATCH` `DELETE` | `/api/v1/assets/{id}` | Fetch, partial update, cascade delete |
| `POST` `GET` | `/api/v1/inspections` | Create / list inspections (list includes `media_count`) |
| `GET` `PATCH` `DELETE` | `/api/v1/inspections/{id}` | Fetch, partial update, delete |
| `GET` | `/api/v1/inspections/{id}/media` | List media with presigned download URLs |
| `POST` | `/api/v1/inspections/{id}/uploads` | **Multi-file image/video ingest** |
| `GET` `DELETE` | `/api/v1/media/{id}` | Fetch with download URL / delete row and object |

### Upload behaviour

Uploads are streamed to a temp file in 1 MiB chunks, hashed, probed for metadata, then streamed into the bucket — a 500 MB video is never held in memory. Size limits are enforced against **bytes actually read**, not the client's `Content-Length`.

Each file in a batch succeeds or fails independently, and the response reports both counts:

```json
{
  "inspection_id": "…",
  "accepted_count": 2,
  "rejected_count": 1,
  "results": [
    {"filename": "deck.jpg", "accepted": true,  "media_file": {"…": "…"}},
    {"filename": "notes.pdf", "accepted": false, "error": "content type 'application/pdf' is not accepted; …"}
  ]
}
```

A batch where *nothing* was accepted returns **400**; a partial success returns **201**.

### Tests

```bash
cd backend && ../.venv/bin/pytest
```

22 integration tests against the real Postgres and MinIO — not mocks. They create and drop a `twinverse_test` database and a `twinverse-test` bucket, so development data is never touched. The suite applies the **Alembic migration** rather than `create_all`, so it fails if the migration drifts from the models.

### Configuration

Copy [`backend/.env.example`](backend/.env.example) to `backend/.env` and edit. Defaults match the local dev services, so a fresh checkout runs with no `.env` at all. Swapping MinIO for Alibaba Cloud OSS or AWS S3 is a change to `S3_*` values only.

---

## Detection — Phase 2

### Honest status

**The pipeline is built, tested and running on the GPU. It does not yet detect real defects.**

Inference currently loads `yolo11n.pt`, which is **COCO-pretrained** — it detects people, cars and traffic lights, not cracks. Verified on this machine: weights load, warm inference runs in **7 ms** on the RTX 3080, and the class mapper correctly discards every COCO label because none of them are defect classes. That is the pipeline working exactly as designed and finding nothing, which is the correct outcome for the wrong weights.

What remains is the part the README always said was the risk: **a labelled dataset and a fine-tune**. See [`ml/datasets/README.md`](ml/datasets/README.md) — including the trap that SDNET2018, the most-cited option, is a *classification* set with no bounding boxes.

Until `MODEL_WEIGHTS` points at a fine-tuned checkpoint, no claim about defect detection is defensible. Stating that plainly is the same discipline as [D-004](#d-004--severity-scoring-is-relative-not-absolute).

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/media/{id}/detect` | Run inference on one file, synchronous, returns detections |
| `GET` | `/api/v1/media/{id}/detections` | Detections for one file, confidence-ordered |
| `POST` | `/api/v1/inspections/{id}/detect` | Dispatch across an inspection — **202**, poll `status` |
| `GET` | `/api/v1/inspections/{id}/detections` | All detections in an inspection |
| `GET` | `/api/v1/inspections/{id}/detections/summary` | Counts by defect class, for the dashboard |
| `GET` | `/api/v1/detector` | Which weights are actually loaded |

That last endpoint exists because "which model produced these boxes" is the first question anyone asks of a detection, and inferring it from config is not good enough.

### Video handling

Video is **sampled, not decoded frame by frame**. A 60-second clip at 30 fps is 1800 frames, and adjacent frames show the same defect from nearly the same angle — processing all of them multiplies runtime and fills the table with near-duplicate rows. Default stride is 15 frames, capped at 300 analyzed frames. Detections carry `frame_index` so the dashboard can seek to them.

### Training a real detector

```bash
python ml/prepare_dataset.py --source ~/downloads/concrete-cracks --output ml/datasets/concrete --classes crack corrosion surface_damage
```

```bash
python ml/train.py --data ml/datasets/concrete/data.yaml --epochs 100
```

```bash
MODEL_WEIGHTS=/abs/path/to/ml/weights/defect-detector.pt uvicorn app.main:app
```

`train.py` **exits rather than falling back to CPU** if CUDA is unavailable. A run that silently trains on CPU for a week is the same failure as [D-002](#d-002--windows-nvidia-driver-was-critically-outdated) wearing a different hat.

---

## Development Roadmap & Effort Estimates

Estimates assume a solo developer working with AI pair-programming assistance.

| Phase | Deliverable | Effort | Status |
|---|---|---|---|
| **0** | Ubuntu migration, drivers, toolchain, repo scaffold | 0.5–1 d | ✅ done |
| **1** | Upload API — FastAPI + PostgreSQL + MinIO, image & video ingest | 1–1.5 d | ✅ done |
| **2** | **Defect detection** — dataset prep, YOLOv11 fine-tune, video frame pipeline | **2–4 d** — critical path | ◐ pipeline done; **needs dataset + fine-tune** |
| **3** | Severity scoring engine | 0.5 d | ⬜ |
| **4** | Dashboard + PDF report export (Next.js) | 1.5–2 d | ⬜ |
| **5** | Three.js digital twin viewer with defect markers | 1–2 d | ⬜ |
| **6** | JWT auth, Docker Compose, CI, documentation | 1 d | ⬜ |
| **7** | Demo script, pitch deck, recorded walkthrough | 1 d | ⬜ |

**Total: 9–14 focused working days** (~8–10 days full-time, or 2.5–3 weeks part-time).

**Crunch fallback (~3 days):** upload → pretrained detector → severity → dashboard with bounding-box overlays. Drop the 3D viewer, auth, and Docker. Still demonstrates the core thesis.

---

## Scope Triage — What Ships and What Does Not

### In scope — straightforward (~70% of MVP)

- Image/video upload API with object storage
- PostgreSQL schema for assets, inspections, detections
- Defect detection using YOLOv11 (pretrained first, fine-tuned second)
- Heuristic severity scoring with a visible, explainable formula
- Dashboard: inspection list, annotated image overlays, severity distribution chart
- PDF report generation
- Three.js viewer: GLB asset model + colored defect markers, click for detail
- Docker Compose, README, GitHub Actions CI

### In scope — this is where the days actually go

- Training a genuinely *good* custom detector — **risk is dataset quality, not compute**
- Video pipeline throughput and frame sampling strategy
- JWT + RBAC implemented properly rather than cosmetically

### Explicitly cut — document as roadmap, do not attempt

| Cut | Why |
|---|---|
| Real digital twin (NeRF / Gaussian Splatting) | Weeks of work. Ship the marker viewer as "Digital Twin v1". |
| NVIDIA Isaac Sim synthetic data | Enormous setup cost, near-zero demo payoff |
| Predictive maintenance | Requires longitudinal data that does not exist yet. If a trend chart is shown, **label it simulated**. |
| Thermal anomaly detection | Requires thermal camera hardware |
| Crack width in real-world millimetres | Genuine research problem — needs camera calibration or a scale reference. Without it, only **relative** severity is defensible. **State this limitation openly in the demo.** |
| Live drone integration | Phase 6. Show a pre-recorded flythrough instead. |

---

## Severity Scoring Model

Deliberately simple, deliberately **visible**. Explainability is a stated judging advantage, so the formula is shown in the UI rather than hidden.

```
severity_score = normalized_area x detection_confidence x class_weight

class_weight:  crack 1.0 | corrosion 0.9 | surface_damage 0.6 | missing_component 1.0

Bands:  0.00-0.25 Low | 0.25-0.50 Medium | 0.50-0.75 High | 0.75-1.00 Critical
```

**Stated limitation:** this produces a *relative* severity ranking within and across inspections. It does **not** output engineering units (crack width in mm), because that requires camera calibration or a known scale reference in frame. Presenting it honestly is a strength, not a weakness — inflated claims are what judges probe hardest.

---

## Datasets

Candidate public sources for Phase 2. **Pick one asset type and go deep** rather than covering many shallowly.

- **SDNET2018** — concrete crack images (bridge decks, walls, pavement)
- **CrackForest (CFD)** — road/pavement crack segmentation
- **Roboflow Universe** — several pre-labeled crack and corrosion detection sets in YOLO format
- **Kaggle** — surface crack detection, corrosion/rust classification sets

Recommended focus: **concrete bridge and building defects**. Clear public data, high real-world relevance, visually legible in a demo.

---

## Planned Repository Structure

Built (✅) versus planned (⬜):

```
twinverse-inspect-ai/
├── backend/                    ✅ FastAPI service
│   ├── alembic.ini             ✅
│   ├── pytest.ini              ✅
│   ├── requirements.txt        ✅ service deps (no CUDA stack)
│   ├── .env.example            ✅
│   ├── app/
│   │   ├── main.py             ✅ app factory, CORS, lifespan
│   │   ├── api/
│   │   │   ├── deps.py         ✅ shared 404 lookups
│   │   │   └── routers/        ✅ health, assets, inspections, uploads, detections
│   │   │                       ⬜ reports
│   │   ├── core/               ✅ config          ⬜ security, JWT
│   │   ├── db/                 ✅ base, models, session, migrations/
│   │   ├── schemas/            ✅ asset, inspection, media, detection
│   │   └── services/           ✅ storage, media, inference, detection
│   │                           ⬜ severity, reporting
│   └── tests/                  ✅ 47 integration tests
├── ml/                         ◐ model training and evaluation
│   ├── requirements.txt        ✅ torch, torchvision, ultralytics
│   ├── prepare_dataset.py      ✅ split + data.yaml generation
│   ├── train.py                ✅ YOLOv11 fine-tune
│   ├── datasets/               ✅ README    ⬜ data (gitignored)
│   ├── notebooks/              ⬜
│   └── weights/                ⬜ (gitignored — Git LFS or GitHub Releases)
├── frontend/                   ⬜ Next.js dashboard + Three.js viewer
├── infra/                      ⬜ docker-compose.yml, .github/workflows/
├── docs/                       ⬜
├── requirements.txt            ✅ aggregate of backend + ml, for one dev venv
└── README.md                   ✅
```

**On the requirements split:** `backend/requirements.txt` deliberately excludes `torch`, `torchvision` and `ultralytics`. The API service does not run inference in-process, so bundling the CUDA stack would add several GB to its container image for code it never calls. The root `requirements.txt` is a two-line aggregate (`-r backend/…`, `-r ml/…`) so a single development venv still covers everything.

---

## Demo Strategy

1. **Go deep on one asset type.** A demo that convincingly nails concrete cracks beats one that half-detects five defect classes across five asset types.
2. **Show the severity formula on screen.** Explainability is a listed judging advantage; half a day of work serves it directly.
3. **State limitations proactively.** Naming the scale-calibration problem before a judge finds it builds far more credibility than it costs.
4. **Lead with the safety and cost narrative**, not the model architecture. The story is "inspectors stop rappelling down dams," not "we used YOLOv11."
5. **Record a backup video.** Live demos fail. A 2-minute recorded walkthrough is insurance.
6. **If the event is cloud-sponsored**, map the architecture onto the sponsor's services — the S3-compatible storage layer swaps to Alibaba Cloud OSS via config alone, and PostgreSQL maps to ApsaraDB RDS.

---

## Decision Log

Recorded so the reasoning survives the OS migration and any team handoff.

### D-001 — Migrate development environment from Windows 11 to Ubuntu 24.04

**Date:** 2026-08-29 · **Status:** Accepted

Original analysis recommended staying on Windows with WSL2 Ubuntu 24.04, on the grounds that no MVP phase (1–5) requires ROS2, Gazebo, or Isaac Sim, and that a full OS migration costs 1–2 days plus bootloader and Optimus risk on this specific laptop.

The decision was made to migrate natively anyway. Supporting rationale: native Ubuntu is genuinely superior for the Phase 6 robotics work (ROS2 Jazzy, Gazebo Harmonic, Isaac Sim), avoids WSLg rendering limitations for GUI simulation tools, and gives better Docker performance.

**Correction on record:** the migration was partly motivated by a belief that NVIDIA drivers ship preinstalled with Ubuntu. **They do not** — Ubuntu 24.04 defaults to Nouveau with no CUDA support, and the proprietary driver must be installed manually (see [setup step 1](#1-nvidia-driver)). The saving versus Windows is real but modest: one apt command instead of a manual installer download.

### D-002 — Windows NVIDIA driver was critically outdated

**Date:** 2026-08-29 · **Status:** Resolved by D-001

The Windows install carried driver **471.41** (mid-2021), which predates CUDA 12 and would have caused all PyTorch 2.x GPU builds to fail. The Ubuntu migration installs a current driver, resolving this. Retained here because it explains why the fresh driver install must be **verified with `nvidia-smi`** before any ML work begins.

### D-003 — Ship a marker-based viewer, not a real digital twin

**Date:** 2026-08-29 · **Status:** Accepted

NeRF and Gaussian Splatting pipelines are weeks of work. The MVP ships a Three.js scene with a GLB asset model and colored, clickable defect markers, presented honestly as "Digital Twin v1". This delivers the highest visual impact per hour of any remaining feature.

### D-004 — Severity scoring is relative, not absolute

**Date:** 2026-08-29 · **Status:** Accepted

Absolute measurements (crack width in mm) require camera calibration or an in-frame scale reference. The MVP outputs a relative severity band and states this limitation explicitly in both the UI and the pitch.

### D-005 — Migration executed and verified; D-001 and D-002 closed

**Date:** 2026-08-30 · **Status:** Resolved

The Ubuntu 24.04 migration decided in D-001 is complete. Verified state: Ubuntu 24.04.4 LTS, NVIDIA **580.173.02 / CUDA 13.0**, RTX 3080 Laptop reporting the full 16384 MiB under `nvidia-smi`, Python 3.12.3, Docker 29.1.3.

This closes D-002 — the critically outdated Windows driver 471.41 is gone, and the replacement is current. The `nvidia-smi` verification D-002 insisted on before any ML work has been performed and passed.

**Correction on record:** the [Pre-Migration Checklist](#backup--repository) required pushing the planning artifacts to GitHub *before* wiping Windows. The wipe was done first and the push was not done at all, leaving this README and the proposal PDF with no off-machine copy. Caught and remediated on 2026-08-30. The ordering error, not the migration, was the real risk.

### D-006 — Node.js via nvm, not NodeSource

**Date:** 2026-08-30 · **Status:** Accepted

The original setup step piped a NodeSource script into `sudo -E bash -`. Replaced with nvm: it installs into the user's home directory, requires no root, avoids executing a remote script with superuser rights, and makes Node version switching trivial. Ubuntu's packaged `nodejs` was rejected — Noble ships 18.19, which is end-of-life.

Similarly, the PyTorch `--index-url .../cu124` pin was dropped in favour of the default PyPI wheels, which carry a CUDA runtime matched to the installed 580 driver. Pinning an older runtime than the driver buys nothing here.

### D-007 — Object storage is written before the database row, and rolled back on failure

**Date:** 2026-08-30 · **Status:** Accepted

An upload touches two systems that cannot share a transaction. The order chosen is: stream the object into the bucket first, then commit the row; if the commit fails, delete the object.

The failure mode this avoids is a row pointing at an object that was never written — a broken image in the dashboard with no way to tell whether ingest or storage was at fault. The failure mode it accepts is a brief orphaned object if the process dies between the two steps, which is recoverable by a sweep and harms nothing in the meantime.

Related: deleting an **asset** cascades to its rows but deliberately leaves objects in the bucket, so a mistaken delete stays recoverable. Deleting a **single media file** is an explicit act and does reclaim the object.

### D-008 — Batch uploads isolate per-file failures

**Date:** 2026-08-30 · **Status:** Accepted

A drone run produces dozens of stills at once. Rejecting an entire batch because one file is a stray PDF would be hostile in exactly the situation the tool exists for. Each file is validated and stored independently, and the response carries `accepted_count`, `rejected_count`, and a per-file result with the reason for each rejection.

A batch where nothing was accepted returns 400; a partial success returns 201. Silently returning 201 for a batch that stored nothing would be the worst option.

### D-009 — Detection schema lands in the first migration; bounding boxes are normalized

**Date:** 2026-08-30 · **Status:** Accepted

The `detections` table is created in the Phase 1 migration even though nothing writes to it until Phase 2, so the schema arrives in one reviewable migration rather than being bolted on later.

Bounding boxes are stored **normalized to 0..1** against the source frame rather than in pixels, so they survive resizing and can be overlaid on any rendition — thumbnail, full image, or Three.js marker — without carrying original dimensions around.

The severity *inputs* (`normalized_area`, `class_weight`, `confidence`) are stored alongside `severity_score`, not just the final number. [D-004](#d-004--severity-scoring-is-relative-not-absolute) commits to showing the formula in the UI; that is only honest if the score can be re-derived from stored values rather than taken on trust.

### D-010 — Phase 1 tests run against real Postgres and MinIO, not mocks

**Date:** 2026-08-30 · **Status:** Accepted

The entire claim of the upload path is that bytes land in object storage and a row lands in the database. A mocked S3 client would prove neither, so the suite runs against the real local services, creating and dropping a `twinverse_test` database and `twinverse-test` bucket.

The suite also applies the **Alembic migration** rather than `Base.metadata.create_all`, so it fails when the migration drifts from the models — the drift being the thing most likely to break a deployment while every unit test still passes.

Cost: the tests need Docker running. That is an acceptable trade at this stage and is documented in the [API section](#api--phase-1).

### D-011 — Unrecognized model classes are discarded, never guessed

**Date:** 2026-08-30 · **Status:** Accepted

Fine-tuned checkpoints from different datasets use different label vocabularies (`crack`, `cracks`, `spalling`, `rust`). An alias table in `inference.py` maps them onto the four defect classes; anything not in the table returns `None` and the box is dropped.

The alternative — defaulting unknown labels to some class — would let a COCO model's `person` detection be filed as a crack, and every downstream severity number computed from it would be wrong while looking entirely plausible. Dropping data is recoverable; silently corrupting it is not.

### D-012 — Video is sampled, not decoded frame by frame

**Date:** 2026-08-30 · **Status:** Accepted

A 60-second clip at 30 fps is 1800 frames. Adjacent frames show the same defect from nearly the same angle, so full decoding multiplies inference time and fills the detections table with near-duplicate rows carrying no extra information.

Default stride is 15 frames with a 300-frame cap, both configurable. Detections carry `frame_index` so the dashboard can seek to the source moment.

Known limitation, worth stating before a judge finds it: **the same physical crack appearing in twelve sampled frames currently produces twelve detection rows.** Cross-frame deduplication (tracking, or IoU-based merging) is not implemented. Until it is, video defect *counts* overstate reality — image counts do not.

### D-013 — Phase 2 writes geometry, not severity

**Date:** 2026-08-30 · **Status:** Accepted

Detection rows are written with `normalized_area` populated — it is free, being just `bbox_width × bbox_height` — but `class_weight`, `severity_score` and `severity_band` are left **null**.

Writing placeholder scores now would make unscored rows indistinguishable from scored ones the moment Phase 3 lands, and a null is an honest "not computed yet" in a way that `0.0` is not.

### D-014 — The detector sits behind a protocol so the pipeline is testable without weights

**Date:** 2026-08-30 · **Status:** Accepted

`inference.py` exposes a `Detector` protocol with a swappable implementation. Tests inject a stub returning fixed boxes.

This keeps the suite from depending on a model download, and draws the right line: whether storage → inference → database persistence works is a question about *this code* and is tested here; whether YOLO actually finds cracks is a question about *weights and training data*, and is answered by training metrics, not by unit tests. Conflating the two produces tests that pass while the product does nothing useful.

---

## Backup & Repository

**Done — 2026-08-30.** This section previously read "Pre-Migration Checklist" and described work to do *before* wiping Windows. The migration happened first and the backup did not, so the planning artifacts survived on a single disk with no remote copy for a period. That gap is now closed.

Current state:

- Repository initialized on `main`, initial commit `c1c0454`
- Pushed to **`git@github.com:drhafiz-ayaan/twinverse-inspect-ai.git`** — **private**
- Tracked: `README.md`, `TwinVerse_Inspect_AI_Master_Proposal.pdf`, `.gitignore`
- `.gitignore` excludes `.venv/`, `node_modules/`, secrets, and — per the [repository structure](#planned-repository-structure) — `ml/datasets/` and `ml/weights/`

Flip to public before hackathon submission if required:

```bash
gh repo edit drhafiz-ayaan/twinverse-inspect-ai --visibility public
```

**Still not backed up anywhere:** any datasets downloaded for Phase 2. These are deliberately gitignored (too large for the repo), so they need separate backup — re-downloading costs hours. Use Git LFS or GitHub Releases for trained weights.

---

## License

TBD — MIT recommended for hackathon submission.
