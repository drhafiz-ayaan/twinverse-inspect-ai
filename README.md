# TwinVerse Inspect AI

**AI-Powered Infrastructure Intelligence Platform**

> Analyze images and videos from drones, CCTV, robots, or smartphones to automatically detect infrastructure defects — cracks, corrosion, surface damage, equipment faults — assess severity, generate maintenance insights, and visualize asset health through an interactive digital twin.

**Status:** **Phases 1–6 complete and verified.** Upload API, fine-tuned crack detector, severity scoring, dashboard, PDF reports, Three.js marker viewer, JWT auth with RBAC, and a Docker stack running end to end — 101 passing tests. Cracks only, at a measured 20% false-positive rate on clean concrete; see [Detection — Phase 2](#detection--phase-2). Remaining: Phase 7 demo preparation.
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
- [Dashboard — Phase 4](#dashboard--phase-4)
- [Security & Deployment — Phase 6](#security--deployment--phase-6)
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

### Status — working, with stated limits

**A fine-tuned crack detector is trained, evaluated and wired into the API.** Verified end to end on 2026-08-30: three held-out images uploaded through the API produced 10 crack detections in 6.1 s, with normalized boxes and areas persisted to PostgreSQL.

Current model: `ml/weights/crack-nitw-bg.pt` — YOLOv11n fine-tuned on [D-015](#d-015--training-dataset-nitw-concrete-crack-detection-v6)'s dataset plus background images.

| Metric | Value |
|---|---|
| mAP50 | 0.436 |
| mAP50-95 | 0.149 |
| **Separation** (clean vs cracked) | **0.611** — DECENT |
| Operating point | conf **0.30** → 20.2% false positives on clean, 81.3% detection on cracked |

**What this does not claim.** One defect class only — cracks. It has never seen corrosion, spalling or missing components, and `class_weight` is therefore constant at 1.0. One in five clean surfaces still draws a box. Separation was measured against 94 defect-free photographs from a single source, which is a real signal but not a broad one.

The honest framing for a demo: *this finds most cracks and is wrong about clean concrete roughly a fifth of the time.* That is a useful first-pass inspection tool and not an unattended one.

### How the numbers moved

| Configuration | mAP50 | Separation |
|---|---|---|
| `yolo11s`, nitw only, 80 epochs | 0.442 | 0.258 — POOR |
| `yolo11s`, merged datasets, 80 epochs | 0.373 | 0.000 — UNUSABLE |
| **`yolo11n`, nitw + backgrounds, 38 epochs** | **0.436** | **0.611 — DECENT** |

**mAP50 is flat across all three. Real-world usability varies by a factor of infinity.** The first and third models look interchangeable on the metric everyone reports; one fires on 51% of clean surfaces at its best operating point and the other on 20%. This is the whole argument of [D-016](#d-016--map-is-not-sufficient-evidence-false-positives-on-clean-surfaces-must-be-measured-separately) in three rows.

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

Fetch a pre-labelled dataset from Roboflow Universe (needs `ROBOFLOW_API_KEY` in `backend/.env`):

```bash
python ml/fetch_dataset.py --url https://universe.roboflow.com/<workspace>/<project>/dataset/<version>
```

Roboflow exports arrive already split, so skip straight to training. For a flat, unsplit dataset from elsewhere, use `prepare_dataset.py` instead:

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

### Check before you commit an hour

```bash
python ml/quick_check.py --data ml/datasets/crack-merged/data.yaml --clean-from-empty-labels ml/datasets/concrete-bridge-defect
```

Trains a small model on a subsample for a few epochs, then runs the full clean-vs-defective test. **Roughly two minutes instead of an hour.**

It reports one number — **separation**, the best achievable margin between detection rate and false-positive rate across thresholds (Youden's J). 0.0 means the model cannot distinguish cracked concrete from clean concrete at any threshold; 1.0 is perfect.

| Separation | Meaning |
|---|---|
| < 0 | Inconclusive — model detects nothing yet, train longer |
| < 0.15 | Unusable — do not spend an hour on this configuration |
| < 0.35 | Poor — will embarrass you on clean surfaces |
| 0.35–0.55 | Marginal — demoable with a carefully chosen threshold |
| > 0.55 | Decent or better |

**The D-016 baseline scored 0.258 after a full hour.** That is the bar any new configuration has to clear.

The negative case matters as much as the rest: a model that has not yet learned to fire produces no detections and scores 0, identical to one firing at random. Those need opposite responses — "train longer" versus "abandon the approach" — so the silent case is reported separately rather than collapsed into a verdict.

---

## Dashboard — Phase 4

Next.js 16 (App Router, TypeScript, Tailwind 4) in [`frontend/`](frontend), plus PDF export from the API.

### Run it

```bash
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

```bash
bash frontend/dev.sh
```

Dashboard at <http://localhost:3000>. It needs the API running; if it is not, the page says so and shows the command rather than failing blankly.

### What it shows

| View | Contents |
|---|---|
| `/` | Inspection list with asset, media count and status; the scoring model |
| `/inspections/[id]` | Stats, severity distribution, ranked detection table, per-image overlays, PDF download |

Detections are drawn as an SVG overlay with `viewBox="0 0 1 1"`, so the stored normalized boxes ([D-009](#d-009--detection-schema-lands-in-the-first-migration-bounding-boxes-are-normalized)) map straight onto the image at any rendered size with no pixel arithmetic. Hovering a detection highlights its box and shows the arithmetic behind its score.

### Explainability, end to end

The formula, class weights and band thresholds are **fetched from `GET /api/v1/severity/model`**, not hardcoded in the frontend — so what the dashboard shows cannot drift from what the server computes.

The same discipline applies to model capability. `GET /api/v1/detector` reports three separate things: the taxonomy the database supports, the raw labels the loaded checkpoint emits, and the intersection. The UI renders the intersection, currently *"detects only crack — the other 3 defect classes in the taxonomy are not covered by this model and will not be reported even if present"*. An earlier version displayed the taxonomy as though it were the model's capability, which overstated it fourfold.

### PDF reports

`GET /api/v1/inspections/{id}/report.pdf` — summary, severity distribution, the formula, the fifteen highest-severity detections, and a limitations page.

The limitations page is load-bearing rather than boilerplate: it states that severity is relative, that roughly one clean surface in five is flagged, that only cracks are detected, and that video counts are inflated by frame-level double counting. A test extracts the PDF text and asserts those statements are present, so a redesign cannot quietly drop them.

### Two environment gotchas

**Turbopack fails in this setup; the dev script uses webpack.** Next 16 defaults to Turbopack, which spawns worker processes that could not locate Node here — every page 500s with `spawning node pooled process: No such file or directory`. `next dev --webpack` works. Production builds are unaffected.

**Node is symlinked into `~/.local/bin`.** nvm installs under `~/.nvm`, which a login shell picks up from `.bashrc` but non-interactive spawns do not. Since `~/.local/bin` is already on the default `PATH`, symlinking `node`, `npm` and `npx` there makes them resolvable from any process:

```bash
ln -sf ~/.nvm/versions/node/v20.20.2/bin/{node,npm,npx} ~/.local/bin/
```

Re-run that after `nvm install` of a different version — the symlinks pin one version and will not follow `nvm use`.

---

## Security & Deployment — Phase 6

### Authentication

JWT bearer tokens, bcrypt passwords, three ranked roles.

| Role | Can |
|---|---|
| `viewer` | Read inspections, detections, reports |
| `inspector` | + upload media, run analysis, create/edit assets and inspections |
| `admin` | + delete assets, manage users |

**Everything under `/api/v1` requires at least a viewer.** The baseline is applied at router registration rather than per endpoint, so a newly added route is protected by default — forgetting a decorator fails closed instead of leaking data. Only `/health` and `/auth/login` are public.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Exchange credentials for a token |
| `GET` | `/api/v1/auth/me` | Current user |
| `POST` `GET` | `/api/v1/auth/users` | Create / list users — **admin only** |
| `PATCH` | `/api/v1/auth/users/{id}` | Change role or disable — **admin only** |

Decisions worth knowing:

- **The role is re-read from the database on every request**, not trusted from the token. A demotion takes effect immediately rather than when the token expires.
- **Wrong password and unknown address are indistinguishable** — same status, same body, and the password is verified even when no user matched so timing does not leak which addresses exist.
- **The last active admin cannot be demoted or disabled**, including by themselves. Otherwise an administrator can lock everyone out of user management.
- **Over-long passwords are rejected, not truncated.** bcrypt silently ignores input past 72 bytes, which would turn a long passphrase into a shorter effective secret without telling anyone.
- **The API refuses to start on the default `SECRET_KEY`** unless `DEBUG=true`. A deployment running on a signing key published in this repository is worse than one that will not boot.

### First admin

Set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`; an admin is created only while the users table is empty. Without it a fresh deployment has no way in, since every user-creation route needs an existing admin.

The address is validated against the login schema before the account is written. Reserved TLDs — `.local`, `.test`, `.invalid` — are rejected by the email validator, so an unvalidated bootstrap address produces an admin **you can never sign in as**, with no obvious reason why. That is not hypothetical: it happened during development with `admin@twinverse.local`.

### Dashboard sessions

The browser posts credentials to the dashboard's own `/api/session` route, which stores the token in an **httpOnly** cookie. A token in `localStorage` is readable by any script on the page, so one XSS bug becomes full account compromise; an httpOnly cookie is not. Verified: `document.cookie` is empty while signed in.

That means only Server Components can attach the token, which is why every data fetch happens server-side and the browser never talks to the API directly. Fetching lives in `lib/server-api.ts`; `lib/api.ts` holds only types and constants, because it is imported by Client Components and cannot pull in `next/headers`.

### Docker

```bash
cd infra && SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))") docker compose up --build
```

Five services: Postgres, MinIO, a one-shot `migrate` job, the API, and the dashboard. The API waits on migrations completing successfully, so it can never serve against an unmigrated schema. Compose fails fast if `SECRET_KEY` is unset.

`ml/weights` is mounted read-only rather than baked into the image — checkpoints are gitignored, and without the mount the service falls back to COCO weights that detect people rather than defects.

**Verified end to end.** The stack builds and runs: all five services healthy, auth enforced, the mounted checkpoint loaded, and a full upload → detect → score → PDF cycle completed inside the containers (3 images, 10 detections, 2.2 s on CPU, every severity score re-derivable from its own row).

Two bugs only surfaced by actually running it, both now fixed:

- `ensure_bucket` caught `ClientError` but not `BotoCoreError`, so a *connection* failure escaped and killed API startup — defeating the "logged, not fatal" behaviour the code claimed.
- The image shipped without torch or ultralytics. It started cleanly and reported an empty class list, meaning it served every endpoint except the one the product exists for. Inference dependencies are now a separate layer from PyTorch's CPU wheel index — see [`requirements-inference.txt`](backend/requirements-inference.txt).

**Note on the builder:** `buildx` is not installed here, so Docker falls back to the deprecated legacy builder. It works, but install the plugin if builds behave oddly:

```bash
sudo apt install -y docker-buildx
```

### CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) — three jobs on every push and PR:

- **backend** — pytest against real Postgres and MinIO service containers, since the suite deliberately does not mock them ([D-010](#d-010--phase-1-tests-run-against-real-postgres-and-minio-not-mocks))
- **frontend** — typecheck, lint, production build
- **secrets** — rejects credential-shaped values in tracked files, and fails if `backend/.env` ever becomes tracked

The secret scan exists because a real API key reached `.env.example` once and had to be scrubbed from history. It excludes obvious placeholders — a check that fails on its own repository gets disabled rather than fixed, so it was verified to pass clean here *and* to still catch a realistic leak.

---

## Development Roadmap & Effort Estimates

Estimates assume a solo developer working with AI pair-programming assistance.

| Phase | Deliverable | Effort | Status |
|---|---|---|---|
| **0** | Ubuntu migration, drivers, toolchain, repo scaffold | 0.5–1 d | ✅ done |
| **1** | Upload API — FastAPI + PostgreSQL + MinIO, image & video ingest | 1–1.5 d | ✅ done |
| **2** | **Defect detection** — dataset prep, YOLOv11 fine-tune, video frame pipeline | **2–4 d** — critical path | ✅ done — cracks only |
| **3** | Severity scoring engine | 0.5 d | ✅ done |
| **4** | Dashboard + PDF report export (Next.js) | 1.5–2 d | ✅ done |
| **5** | Three.js digital twin viewer with defect markers | 1–2 d | ✅ done |
| **6** | JWT auth, Docker Compose, CI, documentation | 1 d | ✅ done |
| **7** | Demo script, pitch deck, recorded walkthrough | 1 d | ⬜ next |

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

Bands:  <0.009 Low | 0.009-0.011 Medium | 0.011-0.014 High | >0.014 Critical
```

**The band thresholds are calibrated, not assumed.** The original proposal specified 0.25 / 0.50 / 0.75, which put **100% of 308 measured detections into Low** — a crack's bounding box covers 2–4% of the frame, so real scores land near 0.009 and the maximum observed was 0.021. The cut points above sit near the p52/p76/p94 of measured output, giving roughly 53/24/17/6 percent across the four bands. See [D-018](#d-018--severity-bands-are-calibrated-against-measured-output-not-assumed).

Served live at **`GET /api/v1/severity/model`** so the dashboard renders the formula, weights and thresholds actually in force rather than a hardcoded copy that can drift. Every detection row stores its own `normalized_area`, `confidence` and `class_weight`, so any score can be re-derived by hand from its own record — which is what makes "we show the formula" an honest claim rather than a slogan.

Thresholds are configuration, not model output. Change them in `.env` and `POST /api/v1/inspections/{id}/rescore` re-applies them to stored detections with no GPU time.

**Stated limitation:** this produces a *relative* severity ranking within and across inspections. It does **not** output engineering units (crack width in mm), because that requires camera calibration or a known scale reference in frame. Presenting it honestly is a strength, not a weakness — inflated claims are what judges probe hardest.

A second limitation now that the model exists: with **one defect class**, `class_weight` is constant at 1.0 and severity reduces in practice to `area × confidence`. The weight table is implemented and tested for all four classes, but only `crack` is reachable until the detector is trained on more.

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
│   │   │   └── routers/        ✅ health, assets, inspections, uploads,
│   │   │                          detections, reports
│   │   ├── core/               ✅ config          ⬜ security, JWT
│   │   ├── db/                 ✅ base, models, session, migrations/
│   │   ├── schemas/            ✅ asset, inspection, media, detection
│   │   └── services/           ✅ storage, media, inference, detection,
│   │                              severity, reporting
│   └── tests/                  ✅ 72 integration tests
├── ml/                         ◐ model training and evaluation
│   ├── requirements.txt        ✅ torch, ultralytics, roboflow
│   ├── fetch_dataset.py        ✅ Roboflow download + data.yaml repair
│   ├── prepare_dataset.py      ✅ split + data.yaml generation
│   ├── train.py                ✅ YOLOv11 fine-tune
│   ├── datasets/               ✅ README    ⬜ data (gitignored)
│   ├── notebooks/              ⬜
│   └── weights/                ⬜ (gitignored — Git LFS or GitHub Releases)
├── frontend/                   ✅ Next.js 16 dashboard
│   ├── app/                    ✅ list + inspection detail pages
│   ├── components/             ✅ overlays, severity bar, formula card
│   ├── lib/api.ts              ✅ typed API client
│   └── dev.sh                  ✅ dev server with nvm's Node on PATH
│                               ⬜ Three.js viewer (Phase 5)
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

### D-015 — Training dataset: NITW concrete crack detection v6

**Date:** 2026-08-30 · **Status:** Accepted

`research-cz7vi/nitw-concrete-crack-detection` v6 — CC BY 4.0, 1197 train / 355 val / 225 test, **4,320** training annotations, single class `crack` that maps directly onto `DefectClass.CRACK`.

*(An earlier revision of this entry said 3,123 annotations. That count came from `cat labels/*.txt | wc -l`, which undercounts by one per file because YOLO label files carry no trailing newline — `wc -l` counts newline characters, so the last annotation in every file was invisible. Count with `awk 'NF'` instead.)*

**Correction on record.** `ycc-otptp/concrete-bridge-defect` was selected first, on the basis that its project page lists four classes (`crack`, `spalling`, `exposed-bar`, `stain`) and multi-class data would make `class_weight` in the severity formula meaningful. That was wrong: the four classes describe the project's *annotations*, and **every exported version remaps them into a single generic `defect` label** — verified on v4 (3,166 annotations) and v6 (13,088), all class index 0.

That rules the dataset out for a reason beyond class count: a generic `defect` label is a union of crack, spalling, exposed rebar and staining, and there is no honest mapping from it to a specific defect class. Calling it `crack` would be precisely the overclaim [D-004](#d-004--severity-scoring-is-relative-not-absolute) exists to prevent. The lesson: **verify an actual export, not the project metadata.**

Two consequences of a single-class dataset, both to be stated in the demo rather than glossed:

- **`class_weight` is constant at 1.0**, so severity reduces to `area × confidence` in practice. The formula is unchanged and still worth showing on screen, but describing it as weighting *across defect types* would misrepresent what the model does.
- **The dataset contains zero background images** — every training image has at least one crack, so the model never sees clean concrete. Expect false positives on undamaged surfaces; it has no examples of "nothing here". `concrete-bridge-defect` v6 has 84 background images and both sets are CC BY 4.0, so grafting them in is an available mitigation.

### D-016 — mAP is not sufficient evidence; false positives on clean surfaces must be measured separately

**Date:** 2026-08-30 · **Status:** Accepted

The first fine-tune (`nitw-concrete-crack` alone, best epoch 50) reached mAP50 **0.442**, mAP50-95 **0.144** — mediocre but arguably demoable. Evaluated against 94 defect-free photographs it was not demoable at all:

| Threshold | False positives on clean | Detections on defective |
|---|---|---|
| 0.25 (configured default) | **88.3%** | 95.6% |
| 0.40 | 51.1% | 76.9% |
| 0.50 | 26.6% | 44.9% |
| 0.60 | **9.6%** | **4.9%** |

Confidence distributions were effectively identical — median 0.163 on clean surfaces against 0.177 on defective — so **no threshold separates them**. At 0.60 the false-positive rate *exceeds* the detection rate: the model was likelier to fire on intact concrete than on a crack.

The cause is [D-015](#d-015--training-dataset-nitw-concrete-crack-detection-v6)'s zero-background problem. A detector trained only on images that all contain cracks never learns what an absence looks like, and mAP cannot reveal this because it is computed over annotated defects only — there are no clean images in the validation set to get it wrong on.

**Consequence for this project:** mAP alone is never sufficient evidence that the detector works. Every model is evaluated with `ml/evaluate.py` against held-out defect-free imagery before any claim is made about it. The 94 bridge background images are reserved for this and deliberately excluded from training so the test stays honest.

Two confounds are acknowledged rather than hidden: the clean set comes from a different dataset, so part of the gap is domain shift; and those images are "clean" only because the bridge annotator drew no boxes, so a few may contain unlabelled hairline cracks. Neither explains identical median confidences.

### D-017 — Smaller model, backgrounds not more data; and check before committing an hour

**Date:** 2026-08-30 · **Status:** Accepted

Three controlled results, each contradicting the obvious move:

**Backgrounds help; the dataset they came from does not.** Merging `crack-b` wholesale drove separation to **0.000** — worse than doing nothing. Taking *only* its 120 background images lifted it from 0.406 to **0.622**. Backgrounds have no labels, so they import no convention — which is why `merge_datasets.py --backgrounds-from` exists.

> **Correction (2026-08-31).** The explanation above was wrong, and the conclusion drawn from it — that `crack-b`'s annotated images carry a harmful labelling convention — does not survive checking. `crack-b` is an **instance-segmentation export**: 1,932 of its 1,941 label rows are polygons, not boxes. Ultralytics trains on those files without complaint, reading the first two polygon vertices as `cx cy w h`, so the merge was trained on coordinates that mean nothing. The "3.61 boxes per image" figure was counting polygon rows against box rows. What the experiment actually measured was a **format mismatch**, not a data-quality problem. Converted with [`ml/seg_to_box.py`](ml/seg_to_box.py), `crack-b` yields 3,694 valid boxes across 1,809 genuinely cracked images, and it is now part of training — see [D-020](#d-020--three-independent-sources-and-what-that-cost-to-find-out). The lasting lesson is the one in [D-015](#d-015--training-dataset-nitw-concrete-crack-detection-v6), stated more strongly: **verify the label format before drawing any conclusion from a training run**, because a format bug and a data-quality problem produce the same symptom.

**`yolo11n` beats `yolo11s` here.** Every configuration improved on the smaller model, consistent with the train/val loss divergence measured on the first run (gap quadrupling from 0.32 to 1.30 over 80 epochs). 1197 images does not support `yolo11s`'s capacity. The final run early-stopped at epoch 38 against the baseline's 80.

**The two-minute check predicted the twenty-five-minute run to within 0.011** — forecast 0.622, actual 0.611. `quick_check.py` is therefore trustworthy for triage, and the standing rule is: **run it before committing the GPU to a full run.** Two hours were spent on two full runs that a pair of two-minute checks would have redirected.

A process note worth keeping: the first attempt at the background experiment returned a garbage result from a path-resolution bug in the sampler, not from the model. Empty labels trained a model on nothing, and the output read as "this configuration fails". `quick_check` now aborts loudly when a sample yields zero annotations, because a broken input that looks like a valid negative result is the most expensive kind of bug.

### D-018 — Severity bands are calibrated against measured output, not assumed

**Date:** 2026-08-30 · **Status:** Accepted

The proposal specifies bands at 0.25 / 0.50 / 0.75. Measured against 308 real detections from the trained model, **every single one fell into LOW**:

| Percentile | severity_score |
|---|---|
| p50 | 0.0087 |
| p75 | 0.0109 |
| p90 | 0.0129 |
| max | 0.0212 |

The maximum score the model can produce is roughly **one twelfth** of the MEDIUM threshold. The cause is structural rather than a tuning miss: `normalized_area` for a crack's bounding box is 2–4% of the frame, and multiplying by a confidence under 1.0 can only shrink it. Scores spanning 0..1 would require defects covering most of the image.

Bands are now **0.009 / 0.011 / 0.014**, near the p52/p76/p94 of measured output, producing roughly 53/24/17/6 percent across LOW/MEDIUM/HIGH/CRITICAL. Verified end to end: 12 images yielded 34 detections spread 13/9/7/5.

**The formula itself is unchanged.** Only the band boundaries moved, and they are exposed as configuration rather than baked in. `POST /inspections/{id}/rescore` re-applies new thresholds to stored rows without re-running inference, because a threshold change is a config change and should not cost GPU time.

Three things follow that are worth stating plainly:

- These cut points are **dataset- and model-relative**. They describe how this model scores this kind of imagery. They must be recalibrated after any model change, and a "CRITICAL" here means "in the worst few percent of what this model found", not an engineering judgement.
- This is consistent with [D-004](#d-004--severity-scoring-is-relative-not-absolute), which already committed to relative ranking. Calibrated bands make that concrete rather than contradicting it.
- A test asserts the thresholds stay below 0.05, so a well-meaning revert to the proposal's numbers fails loudly instead of silently turning the severity band into a constant.

---

### D-019 — Measured on a third-party dataset the model has never seen; it is weaker than our own test set says

**Date:** 2026-08-31 · **Status:** Accepted

Every number quoted up to here came from `nitw-crack`'s own test split — held out from training, but drawn from the same collection, the same cameras and the same surfaces. That measures memorisation less than it measures *distribution*. To find out whether the detector actually generalises, it was evaluated against **`university-bswxt/crack-bphdr` v2** (RF100 benchmark, public domain, 112 test images), a dataset from an unrelated source that contributed nothing to training.

At the deployed threshold of 0.30:

| | nitw-crack test (in-distribution) | crack-bphdr test (**unseen source**) |
|---|---|---|
| Detection rate | ~81% | **63.4%** |
| False-positive rate | ~20% | 20.2% *(same 94 clean images)* |
| Separation | 0.611 — DECENT | **0.432 — MARGINAL** |

**Roughly a third of cracks are missed on imagery that does not resemble the training set**, against about a fifth on imagery that does. The false-alarm rate is unchanged, because it is measured on the same clean images in both runs — only recall degrades.

Two things this changes:

- **What we claim.** The honest headline is "finds about 4 in 5 cracks on imagery like its training data, closer to 3 in 5 on an unfamiliar source". Quoting the 81% alone is the kind of number that collapses the first time someone points a different camera at a different wall.
- **What to do next.** The fix is more varied training data, not a threshold change: the sweep shows no threshold where the unseen-data separation reaches the in-distribution figure. Sweeping to 0.25 buys recall (72.3%) at a false-positive rate of 31.9% — worse separation, not better.

A methodological note, and a repeat of [D-015](#d-015--training-dataset-nitw-concrete-crack-detection-v6)'s lesson: the Roboflow project advertises `object-detection`, but the v2 export is **instance segmentation** — label rows carry 29–55 polygon coordinates, not 5 box values. It is usable here only because `ml/evaluate.py` reads labels solely to distinguish empty from non-empty. Training on it would need a polygon-to-box conversion first. **Verify the export, never the project metadata.**

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
