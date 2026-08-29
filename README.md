# TwinVerse Inspect AI

**AI-Powered Infrastructure Intelligence Platform**

> Analyze images and videos from drones, CCTV, robots, or smartphones to automatically detect infrastructure defects — cracks, corrosion, surface damage, equipment faults — assess severity, generate maintenance insights, and visualize asset health through an interactive digital twin.

**Status:** Pre-development. Planning complete, environment migration to Ubuntu 24.04 in progress.
**Target:** Hackathon MVP (see [Scope Triage](#scope-triage--what-ships-and-what-does-not)).

---

## Table of Contents

- [Submission Description](#submission-description)
- [Vision](#vision)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Development Machine Profile](#development-machine-profile)
- [Environment Setup — Ubuntu 24.04](#environment-setup--ubuntu-2404-noble)
- [Optional: ROS2 Jazzy + Gazebo Harmonic](#optional-ros2-jazzy--gazebo-harmonic--phase-6-not-mvp)
- [Development Roadmap](#development-roadmap--effort-estimates)
- [Scope Triage](#scope-triage--what-ships-and-what-does-not)
- [Severity Scoring Model](#severity-scoring-model)
- [Datasets](#datasets)
- [Repository Structure](#planned-repository-structure)
- [Demo Strategy](#demo-strategy)
- [Decision Log](#decision-log)
- [Pre-Migration Checklist](#pre-migration-checklist)

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

## Environment Setup — Ubuntu 24.04 (Noble)

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
sudo apt install -y nvidia-driver-570-open
```

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
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs
```

```bash
sudo apt install -y docker.io docker-compose-v2 && sudo usermod -aG docker $USER
```

Log out and back in for the docker group change to take effect.

### 5. Python environment

```bash
python3.12 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip
```

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

```bash
pip install ultralytics opencv-python fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary alembic python-multipart boto3 reportlab pydantic-settings
```

Verify the GPU is visible to PyTorch:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Expected output: `True NVIDIA GeForce RTX 3080 Laptop GPU`

### 6. Services

```bash
docker run -d --name twinverse-pg -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=twinverse -p 5432:5432 postgres:16
```

```bash
docker run -d --name twinverse-minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin quay.io/minio/minio server /data --console-address ":9001"
```

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

## Development Roadmap & Effort Estimates

Estimates assume a solo developer working with AI pair-programming assistance.

| Phase | Deliverable | Effort |
|---|---|---|
| **0** | Ubuntu migration, drivers, toolchain, repo scaffold | 0.5–1 d |
| **1** | Upload API — FastAPI + PostgreSQL + MinIO, image & video ingest | 1–1.5 d |
| **2** | **Defect detection** — dataset prep, YOLOv11 fine-tune, video frame pipeline | **2–4 d** — critical path |
| **3** | Severity scoring engine | 0.5 d |
| **4** | Dashboard + PDF report export (Next.js) | 1.5–2 d |
| **5** | Three.js digital twin viewer with defect markers | 1–2 d |
| **6** | JWT auth, Docker Compose, CI, documentation | 1 d |
| **7** | Demo script, pitch deck, recorded walkthrough | 1 d |

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

```
twinverse-inspect-ai/
├── backend/              # FastAPI service
│   ├── app/
│   │   ├── api/          # routers: upload, inspections, detections, reports
│   │   ├── core/         # config, security, JWT
│   │   ├── db/           # models, session, migrations
│   │   └── services/     # inference, severity, storage, reporting
│   └── tests/
├── frontend/             # Next.js dashboard + Three.js viewer
│   ├── app/
│   ├── components/
│   └── lib/
├── ml/                   # model training and evaluation
│   ├── datasets/         # (gitignored)
│   ├── notebooks/
│   ├── train.py
│   └── weights/          # (gitignored — use Git LFS or GitHub Releases)
├── infra/
│   ├── docker-compose.yml
│   └── .github/workflows/
├── docs/
└── README.md
```

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

---

## Pre-Migration Checklist

**Before wiping Windows**, preserve this work. This README and the proposal PDF are currently the only artifacts of the planning effort.

```bash
git init && git add . && git commit -m "Initial: proposal and development blueprint"
```

```bash
git branch -M main && git remote add origin https://github.com/<username>/twinverse-inspect-ai.git && git push -u origin main
```

Confirm the push succeeded on GitHub before reformatting the drive.

Also back up separately:
- `TwinVerse_Inspect_AI_Master_Proposal.pdf`
- Any datasets already downloaded (re-downloading costs hours)

---

## License

TBD — MIT recommended for hackathon submission.
