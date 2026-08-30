# TwinVerse Inspect AI — Operating Guide

Everything you need to run, demo, and explain the system. Written so a team
member who has never opened the repository can get a working demo on screen.

> **Read this first if you are demoing:** jump to
> [Demo runbook](#7-demo-runbook). It is the only section that matters on the day.

---

## Contents

1. [What this is](#1-what-this-is)
2. [Prerequisites](#2-prerequisites)
3. [Fastest start — Docker](#3-fastest-start--docker)
4. [Development start — two terminals](#4-development-start--two-terminals)
5. [First login and creating users](#5-first-login-and-creating-users)
6. [Running an inspection end to end](#6-running-an-inspection-end-to-end)
7. [Demo runbook](#7-demo-runbook)
8. [Training a better model](#8-training-a-better-model)
9. [What to say about limitations](#9-what-to-say-about-limitations)
10. [Troubleshooting](#10-troubleshooting)
11. [Who does what](#11-who-does-what)

---

## 1. What this is

Upload photos or video of a structure. The system finds cracks, scores how
serious each one is, shows them on the image and on a 3D model, and exports a
PDF report.

Four moving parts:

| Part | What it does | Where |
|---|---|---|
| **API** | Ingest, inference, scoring, reports | `backend/` — FastAPI, port 8000 |
| **Dashboard** | Everything you show a judge | `frontend/` — Next.js, port 3000 |
| **Model** | The trained crack detector | `ml/weights/crack-nitw-bg.pt` |
| **Storage** | Postgres + MinIO | Docker containers |

---

## 2. Prerequisites

Already installed and verified on the development laptop. On a fresh machine:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
```

**Log out and back in** after `usermod`, or the Docker socket refuses you.

For development (not needed if you only run Docker):

```bash
sudo apt install -y python3.12 python3.12-venv
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
nvm install 20 && nvm alias default 20
ln -sf ~/.nvm/versions/node/v20.20.2/bin/{node,npm,npx} ~/.local/bin/
```

That last line matters: nvm installs outside the system path, and tooling that
spawns Node without a login shell will not find it otherwise.

---

## 3. Fastest start — Docker

One command brings up all five services.

```bash
cd infra
```

Create `infra/.env` (it is gitignored — never commit it):

```bash
cat > .env <<'EOF'
SECRET_KEY=paste-a-generated-key-here
BOOTSTRAP_ADMIN_EMAIL=admin@twinverse-inspect.com
BOOTSTRAP_ADMIN_PASSWORD=pick-a-real-password
DEBUG=false
INFERENCE_DEVICE=cpu
MODEL_WEIGHTS=/weights/crack-nitw-bg.pt
EOF
```

Generate the key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then:

```bash
docker compose up --build -d
```

| Service | URL |
|---|---|
| Dashboard | <http://localhost:3000> |
| API docs | <http://localhost:8000/docs> |
| MinIO console | <http://localhost:9001> |

Check everything is healthy:

```bash
docker compose ps
```

Stop it:

```bash
docker compose down
```

Add `-v` to that if you also want to wipe the database and stored images.

**If a build behaves oddly**, install the BuildKit plugin — this machine falls
back to Docker's deprecated legacy builder without it:

```bash
sudo apt install -y docker-buildx
```

**Two things worth knowing.** The API refuses to start if `SECRET_KEY` is
missing or left at the built-in default — that is deliberate, so a deployment
can never quietly run on a signing key published in this repository. And
`ml/weights` is mounted into the container rather than baked into the image,
because trained checkpoints are gitignored; without that mount the service
falls back to generic weights that detect people and cars rather than cracks.

---

## 4. Development start — two terminals

Use this when changing code — it gives hot reload and GPU inference.

**Terminal 1 — services and API:**

```bash
docker start twinverse-pg twinverse-minio
```

```bash
cd backend && PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — dashboard:**

```bash
bash frontend/dev.sh
```

Configuration lives in `backend/.env`. Copy it from the template the first
time:

```bash
cp backend/.env.example backend/.env
```

Then edit it. Put real secrets **only** in `.env` — `.env.example` is committed
to git and must contain placeholders only.

---

## 5. First login and creating users

On first start with `BOOTSTRAP_ADMIN_*` set, an admin account is created
automatically. It runs only while the users table is empty, so it cannot
resurrect an account you deliberately deleted.

Sign in at <http://localhost:3000> and **change that password immediately.**

Three roles, each including the one before it:

| Role | Can do |
|---|---|
| `viewer` | Read inspections, detections, reports |
| `inspector` | Upload media, run analysis, create assets and inspections |
| `admin` | Delete assets, create and manage users |

Create a teammate an account (admin only):

```bash
curl -X POST http://localhost:8000/api/v1/auth/users \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"email":"muneed@example.com","password":"choose-something","role":"inspector"}'
```

Get `$TOKEN` by logging in:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@twinverse-inspect.com","password":"your-password"}'
```

**A note on email addresses:** reserved domains like `.local`, `.test` and
`.invalid` are rejected by the validator. Using one creates an account nobody
can ever sign in to, so the system now refuses rather than letting you.

---

## 6. Running an inspection end to end

**The quick way — one command:**

```bash
./demo.sh
```

That signs in, creates the asset, opens an inspection, uploads eight images
from the crack test set, runs detection, waits for it to finish and prints the
dashboard URL. Pass a number for a different image count (`./demo.sh 12`).
Run it before you present so there is always a finished inspection on screen,
and again live if you want to show the pipeline actually working.

**Note:** the dashboard is a read-only view — there is no upload button in the
UI. Imagery enters through the API, which is what `demo.sh` and the steps below
do. If you would rather click than type, everything below is also a form in the
API docs at `/docs`.

**The manual way, step by step:**

**1. Create an asset** — the physical structure.

```bash
curl -X POST http://localhost:8000/api/v1/assets \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Riverside Viaduct","asset_type":"bridge","location":"North Span"}'
```

**2. Open an inspection** against it — one survey visit.

```bash
curl -X POST http://localhost:8000/api/v1/inspections \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"asset_id":"<asset-id>","title":"North span deck survey"}'
```

**3. Upload imagery.** Images or video, up to 50 files per request.

```bash
curl -X POST http://localhost:8000/api/v1/inspections/<id>/uploads \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@photo1.jpg" -F "files=@photo2.jpg"
```

One bad file does not reject the batch — each file reports its own outcome.

**4. Run detection.**

```bash
curl -X POST http://localhost:8000/api/v1/inspections/<id>/detect \
  -H "Authorization: Bearer $TOKEN"
```

Returns immediately; the inspection status moves `pending → processing →
completed`. Watch it change on the dashboard.

**5. Look at it.** Open the inspection in the dashboard. Download the PDF from
the button at the top right.

---

## 7. Demo runbook

Rehearse this. It takes about four minutes.

### Before you start

- [ ] `docker compose ps` — all services healthy
- [ ] `./demo.sh` run once, so an analysed inspection is already on screen
- [ ] Signed in, dashboard open on the inspection list
- [ ] A terminal open on `./demo.sh 6` if you want to run the pipeline live
- [ ] **PDF already downloaded** as a fallback
- [ ] **Recorded video ready** — live demos fail; this is insurance

### The four minutes

**1. Lead with the problem (30s).** Inspectors climb bridges, rappel down dams
and walk pipelines with clipboards. It is slow, dangerous and inconsistent.
Do not open with the model architecture.

**2. Show the dashboard (45s).** Inspection list, then open one. Point at the
severity distribution — critical findings first.

**3. Show a detection (60s).** Hover a detection in the media panel; its box
lights up on the image. Then hover the score: the arithmetic appears —
`0.0288 × 0.558 × 1.0 = 0.01606`. Say the important line here:

> "Every number on this screen can be recomputed by hand from the row it came
> from. Nothing is a black box."

**4. Show the 3D viewer (45s).** Orbit it, click a marker. Then immediately say
what it is not — see below. Saying it before a judge asks is worth more than
the feature.

**5. Export the report (30s).** Click download. Open the last page. Read one
limitation aloud from it.

**6. Close on the story (30s).** Not "we used YOLOv11". Something like:

> "This does not replace an engineer. It does the first pass so the engineer
> spends their time on judgement instead of data collection — and it tells you
> exactly how much to trust it."

---

## 8. Training a better model

Current model detects **cracks only**. To improve or extend it:

**Check before committing an hour of GPU time:**

```bash
python ml/quick_check.py --data ml/datasets/<set>/data.yaml \
  --clean-from-empty-labels ml/datasets/concrete-bridge-defect
```

Two and a half minutes, and it reports one number — *separation*, the margin
between detection rate and false-alarm rate. Anything at or below **0.258** is
not worth a full run; that is what the first hour-long training achieved.

**Fetch a dataset** (needs `ROBOFLOW_API_KEY` in `backend/.env`):

```bash
python ml/fetch_dataset.py --url https://universe.roboflow.com/<workspace>/<project>/dataset/<version>
```

**Train:**

```bash
python ml/train.py --data ml/datasets/<set>/data.yaml --model yolo11n.pt --epochs 100 --patience 15
```

Use `yolo11n`, not `yolo11s` — on a dataset this size the smaller model won
every comparison, because the larger one memorised the training images.

**Evaluate before trusting it:**

```bash
python ml/evaluate.py --weights ml/weights/<new>.pt \
  --clean-from-empty-labels ml/datasets/concrete-bridge-defect \
  --defective ml/datasets/nitw-crack/test/images
```

Then point the API at it — `MODEL_WEIGHTS` in `backend/.env` — and restart.

---

## 9. What to say about limitations

Say these before anyone asks. Naming a weakness costs far less than being
caught by it, and the whole design is built to be defensible rather than
impressive.

**"It only finds cracks."** One defect class. It has never seen corrosion,
spalling or missing components and will not report them even if they are in
frame.

**"About one clean surface in five gets flagged."** Measured against 94
defect-free photographs. It is a screening tool that errs toward flagging.

**"Severity is a ranking, not a measurement."** It does not output crack width
in millimetres — that needs camera calibration or a scale reference in frame.
It tells you which crack to look at first, not how wide it is.

**"The 3D view is illustrative, not surveyed."** The structure is a generic
model and marker positions come from capture order, not real coordinates.
Nothing in the pipeline recovers where a photo was taken from.

**"Video counts are inflated."** Frames are analysed independently, so one
crack visible across ten frames counts ten times.

If someone asks *"why so honest about the flaws?"* — because the alternative is
a judge finding them first.

---

## 10. Troubleshooting

**`permission denied` on the Docker socket.** You were added to the `docker`
group but your shell predates it. Log out and back in, or prefix a single
command: `sg docker -c "docker ps"`.

**API exits with "SECRET_KEY is the built-in development default".** Working as
intended. Set `SECRET_KEY` in `infra/.env` or `backend/.env`.

**Dashboard says "Cannot reach the API".** The API is not running or is on a
different port. Check `docker compose ps`, or that uvicorn is up on 8000.

**Every page bounces to the login screen.** Session expired — tokens last 12
hours by default. Sign in again.

**Dashboard shows "no defect classes reachable".** The loaded model emits no
label the system recognises. Either `MODEL_WEIGHTS` points at generic weights,
or the checkpoint is missing and it fell back. Check `/api/v1/detector`.

**`next dev` fails with "spawning node pooled process".** Turbopack cannot find
Node. The dev script already uses `--webpack` to avoid this; if you invoke Next
directly, add that flag.

**Tests fail with a connection error.** They run against real Postgres and
MinIO by design. Start them: `docker start twinverse-pg twinverse-minio`.

**A Docker build appears frozen with no output.** It is probably fine. Docker's
build output is buffered when piped, and the *client* uses almost no CPU
because the daemon does the work. Check real progress instead:

```bash
docker ps
```

A container running `pip install` means it is downloading. The inference layer
pulls several hundred megabytes and takes a while on a first build.

**Port already in use.** Something else is on 3000 or 8000:

```bash
ss -ltnp | grep -E ':(3000|8000)'
```

---

## 11. Who does what

| | Name | Focus |
|---|---|---|
| **Lead** | Ayaan Aatif | Architecture, ML pipeline, demo delivery |
| **Team** | Muhammad Muneed | *[fill in]* |
| **Team** | Inshrah Mehmood | *[fill in]* |

**Before the presentation:**

- [ ] Change the bootstrap admin password
- [ ] Run the full Docker stack once on the demo machine
- [ ] Record the backup video
- [ ] Decide who speaks to which section
- [ ] Rehearse the limitations answers — those are the questions that get asked

---

*Detailed engineering rationale, including every design decision and the
reasoning behind it, is in [README.md](README.md) — see the Decision Log.*
