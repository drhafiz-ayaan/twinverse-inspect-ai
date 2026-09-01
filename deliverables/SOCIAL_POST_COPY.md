# Social post copy

Two images are in this folder — pick by platform:

| File | Size | Use for |
|---|---|---|
| `demo_social_30s.mp4` | 1080 × 1080, 30s | **Lead with this.** Instagram, LinkedIn, TikTok — video outperforms a static card everywhere |
| `social_square_1080.jpg` | 1080 × 1080 | Instagram, LinkedIn, Facebook |
| `social_landscape_1200x630.jpg` | 1200 × 630 | X/Twitter, LinkedIn link preview |
| `demo_backup.mp4` | 1280 × 720, 70s | Not for social — the presentation backup, with the full unedited inference wait |

The 30-second cut is silent and autoplays muted, which is why the wordmark and
the tagline are burned into the frame rather than left to the caption.
Regenerate it against the current build with:

```bash
python deliverables/record_demo.py --short
```

---

## LinkedIn (long)

We built an AI that inspects infrastructure from a photograph.

Right now, checking a bridge for cracks means someone physically climbing it.
It is dangerous, slow, and two inspectors looking at the same crack will often
write down two different things.

TwinVerse Inspect AI takes ordinary imagery — drone, CCTV, or a phone — finds
the cracks, ranks them by severity, and produces a report. The engineer still
makes every decision. What changes is that they start from a sorted list of
findings instead of a memory card full of photographs.

The part we are most pleased with is not the model. It is that you can check
its work. Every severity score on screen is three numbers multiplied together,
and all three are shown. Nothing is a black box.

We also measured what it gets wrong, and we say so inside the product: it finds
cracks and only cracks, and it flags roughly three photographs in five for a
human to check. That is deliberate — a missed crack is found at the next survey
or when something fails, while a false alarm costs an engineer thirty seconds.
Those are not the same cost, so we did not tune for a metric that treats them
as the same.

The 84% on the card is the worst of four datasets, not the best — across them
it finds 84% to 100% of cracks, and 56% on the one source it has never seen at
all. We chose the operating point by simulating 500-photograph surveys and
picking the threshold that met a recall target, then published the whole curve
so anyone can pick a different one.

Built in a week by three of us at Bano Qabil, Alkhidmat Foundation Pakistan.

Ayaan Aatif · Muhammad Muneed · Inshrah Mehmood

#AI #ComputerVision #Infrastructure #CivilEngineering #MachineLearning #BanoQabil

---

## X / Twitter (short)

We built an AI that finds structural cracks from a photograph, ranks them by
severity, and shows its working.

No black box: every score on screen is three numbers multiplied together, and
all three are displayed.

We also published the trade-off: it flags 3 photographs in 5 for review, and
we picked that point by simulating surveys rather than tuning a metric that
prices a missed crack like a false alarm.

🔗 [link]

---

## Instagram (caption)

Someone has to climb the bridge to check it for cracks.

We built something that does that first pass from a photograph instead. 🛠️

It finds the cracks, ranks how serious each one is, and shows you exactly how
it reached that number — no black box.

It also tells you what it cannot do. It finds cracks and only cracks, and it
flags about three photographs in five for a human to check — on purpose,
because missing a real crack costs far more than a second look. It is a
screening tool, not a replacement for an engineer.

The 84% on the card is the worst of four datasets, not the best. On the one
source it has never seen at all, it finds 56%. We publish all of them.

Three of us. One week. Built at Bano Qabil.

Ayaan Aatif · Muhammad Muneed · Inshrah Mehmood

#AI #ComputerVision #CivilEngineering #Infrastructure #BanoQabil #Pakistan #MachineLearning #Innovation

---

## Before posting

- [ ] Swap in a real screenshot of the dashboard if you want higher engagement
      than the generated card — a real UI outperforms an illustration
- [ ] Add the repository or demo link where `[link]` appears
- [ ] Tag the event and organisers
- [ ] Post the video walkthrough as a follow-up; a 30-second screen recording
      of the 3D viewer will outperform any static image
