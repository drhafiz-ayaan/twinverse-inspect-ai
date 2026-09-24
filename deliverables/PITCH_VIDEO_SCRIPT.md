# Pitch video — full production script

One script, three cuts from the same shoot:

| Cut | Length | For |
|---|---|---|
| **A — Full pitch** | 2:30 | Judges, investors, the website |
| **B — Social** | 0:45 | LinkedIn feed, Instagram, Facebook |
| **C — Vertical hook** | 0:20 | Reels, TikTok, Shorts |

Shoot once, in the order below. Cuts B and C are subsets — no reshoot.

---

## Before you record

- [ ] `cd infra && docker compose up -d` — all five services healthy
- [ ] `./demo.sh 8` — one finished inspection already on screen
- [ ] Browser at 1920×1080, **zoom 100%**, bookmarks bar hidden
- [ ] Sign in beforehand. Nobody needs to watch you type a password
- [ ] A folder of images open and ready to drag
- [ ] `sim_survey_dual.mp4` open in a second tab, paused at 0:00
- [ ] Phone on silent, notifications off, second monitor disconnected

Record at **1080p60** if your tool allows. Screen capture at 30 looks fine
until it is cut against 60 fps simulation footage, and then it looks broken.

---

## Cut A — the full pitch (2:30)

### 0:00–0:20 · The problem

**On screen:** stock or your own footage of an inspector on a bridge or at
height. If you have none, the external chase view from `sim_survey_dual.mp4`
works — a drone under a bridge soffit reads as the same idea.

> "Every bridge, dam and tunnel has to be inspected. Today that means someone
> physically getting close enough to see the concrete — climbing it, rappelling
> down it, or walking it with a clipboard.
>
> It's slow, it's dangerous, and it's inconsistent. Two inspectors looking at
> the same crack will write down two different things."

**Do not** open with the model, the stack, or the word "AI". Twenty seconds on
the problem buys you the next two minutes.

### 0:20–0:40 · What it is

**On screen:** the dashboard, inspection list, then open one.

> "TwinVerse Inspect AI does the first pass from a photograph. Drone, CCTV, or
> a phone — it finds the cracks, ranks them by severity, and produces a report
> an engineer can act on.
>
> The engineer still makes every decision. What changes is that they start from
> a sorted list of findings instead of a memory card full of photographs."

### 0:40–1:10 · Live run

**On screen:** click **+ New inspection**. Name the structure, drop in the
images, press **Upload and analyse**. Let the progress bar run — do not cut it.

> "This is running now. Eight photographs, straight into the pipeline.
>
> That pause is real inference — nothing here is pre-baked."

When it lands, point at the severity distribution.

> "Critical findings first. An inspector opens this and already knows which
> three photographs to look at."

### 1:10–1:35 · The differentiator

**On screen:** hover a detection so its box lights up. Then hover the score.

> "Every severity score on screen is three numbers multiplied together — how
> much of the frame the defect covers, how confident the model is, and a weight
> for the defect class. All three are stored and displayed.
>
> **Every number on this screen can be recomputed by hand from the row it came
> from. Nothing is a black box.**"

Pause for a beat after that line. It is the most important sentence in the
video.

### 1:35–2:05 · The simulation

**On screen:** cut to `sim_survey_dual.mp4`, full width.

> "A crack photograph doesn't record how far away the camera was, or where the
> crack is in space. So we built a bridge where we already know.
>
> Cracks cut from real photographs, placed at known 3D positions, and a
> simulated drone flying the survey into the same upload endpoint a real drone
> would use.
>
> **Red is what the model found. Green is what we know is there.**"

Then the numbers, on screen as text over the footage:

> "It gave us three things nobody can get from a public dataset. A working
> standoff window — one-point-two to three-point-five metres. Survey recall
> against cracks we placed ourselves. And markers that land a median
> **four-point-six centimetres** from the real crack."

### 2:05–2:30 · Honesty and close

**On screen:** the limitations slide, or the dashboard's own limitations panel.

> "It finds cracks and only cracks. It flags about three photographs in five
> for a human to check — deliberately, because missing a crack costs far more
> than a second look. And on a dataset it had never seen, it found 56%.
>
> We publish all of it.
>
> This doesn't replace an engineer. It does the first pass, so the engineer
> spends their time on judgement instead of data collection."

**End card:** wordmark, one line, three names, contact.

---

## Cut B — social, 45 seconds

Same footage, tighter. Burn subtitles in — most of the feed is muted.

| Time | Source | Line |
|---|---|---|
| 0:00–0:06 | inspector / drone | "Checking a bridge for cracks means someone has to climb it." |
| 0:06–0:16 | live run, sped 2× | "We built something that does the first pass from a photograph." |
| 0:16–0:26 | hover the arithmetic | "Every score shows its working. Nothing is a black box." |
| 0:26–0:38 | `sim_survey_dual.mp4` | "We built a bridge where we already know where every crack is. Markers land a median 4.6 cm from the real thing." |
| 0:38–0:45 | end card | "It doesn't replace an engineer. It does the first pass." |

**Hook rule:** the first three seconds decide whether the rest is watched. Lead
with the climbing shot, never with a logo.

---

## Cut C — vertical hook, 20 seconds

9:16. One idea only.

| Time | Source | Text on screen |
|---|---|---|
| 0:00–0:03 | drone under soffit | **"Nobody should have to climb this."** |
| 0:03–0:10 | onboard view, boxes appearing | "AI finds the cracks from a photograph" |
| 0:10–0:16 | dual view, counter rising | "We tested it on cracks we placed ourselves" |
| 0:16–0:20 | end card | **"4.6 cm accurate. And we publish what it misses."** |

---

## Posting plan

**Order matters.** Video first, then the carousel, then the write-up. The video
earns the reach the other two borrow.

| Day | Platform | Asset | Caption |
|---|---|---|---|
| 1 | LinkedIn | Cut B | Long caption from `SOCIAL_POST_COPY.md` |
| 1 | Instagram Reels | Cut C | Short caption, 5–8 tags |
| 2 | X / Twitter | Cut C + `social_landscape_1200x630.jpg` | Short caption, link to repo |
| 3 | LinkedIn | `sim_survey_dual.mp4` raw | "How we tested it" — technical audience |
| 5 | All | Cut A | "Full walkthrough", pinned |

### What to say in comments, not in the video

Keep these for replies. They are credibility, not hook material.

- The model detects **cracks only** — no corrosion, spalling or missing components
- **56%** on the one wholly unseen dataset; 84–100% on the three it trained on
- Simulated false-positive rate is a **floor**; synthetic concrete lacks joints and staining
- The drone is teleported, not flown — this measures perception, not a flight stack

### Three rules

1. **Never post an accuracy number without the dataset beside it.** The moment
   "84%" travels alone it becomes a claim you cannot defend.
2. **Say "first-pass screening", never "automated inspection".** The second one
   implies a level of assurance the product does not have, and an engineer in
   your audience will know.
3. **Do not remove the limitations to make a cut fit.** Cut a feature instead.
   The honesty is the differentiator; without it this is one of many crack
   detectors.
