/**
 * TwinVerse Inspect AI — pitch deck generator.
 *
 * Palette and dark treatment deliberately mirror the product's own interface,
 * so the deck and the live demo read as one thing.
 */
const pptxgen = require("pptxgenjs");

// ---------------------------------------------------------------- palette
const BG = "070B14";        // deep navy — app background
const PANEL = "111A2E";     // glass panel
const LINE = "1E2B44";
const TEXT = "E8EEF8";
const MUTED = "9FB0CC";
const DIM = "64748B";
const CYAN = "22D3EE";
const INDIGO = "6366F1";
const VIOLET = "A78BFA";

// Severity colours are reserved for severity, never decoration.
const SEV_LOW = "10B981";
const SEV_MED = "F59E0B";
const SEV_HIGH = "F97316";
const SEV_CRIT = "F43F5E";

const H = "Calibri";
const B = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
pres.author = "Ayaan Aatif";
pres.company = "TwinVerse Inspect AI";
pres.title = "TwinVerse Inspect AI";

const W = 13.3;
const HGT = 7.5;
const M = 0.75; // margin

/** Dark canvas + a soft corner glow, repeated on every slide as the motif. */
function base(slide, { glow = true } = {}) {
  slide.background = { color: BG };
  if (glow) {
    slide.addShape(pres.ShapeType.ellipse, {
      x: -2.2, y: -2.6, w: 7.5, h: 7.5,
      fill: { color: INDIGO, transparency: 88 }, line: { type: "none" },
    });
    slide.addShape(pres.ShapeType.ellipse, {
      x: W - 4.6, y: HGT - 4.2, w: 7.0, h: 7.0,
      fill: { color: CYAN, transparency: 91 }, line: { type: "none" },
    });
  }
}

function card(slide, x, y, w, h, opts = {}) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.12,
    fill: { color: opts.fill || PANEL, transparency: opts.transparency ?? 18 },
    line: { color: opts.line || LINE, width: 1 },
    shadow: { type: "outer", color: "000000", blur: 14, offset: 3, angle: 90, opacity: 0.35 },
  });
}

function eyebrow(slide, text, y = 0.62) {
  slide.addText(text.toUpperCase(), {
    x: M, y, w: 9, h: 0.3, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 11, bold: true, color: CYAN, charSpacing: 2.4,
  });
}

function title(slide, text, y = 0.98, opts = {}) {
  slide.addText(text, {
    x: M, y, w: opts.w || 11.8, h: opts.h || 0.95, isTextBox: true, margin: 0,
    fontFace: H, fontSize: opts.fontSize || 38, bold: true, color: TEXT,
  });
}

function dot(slide, x, y, color, size = 0.13) {
  slide.addShape(pres.ShapeType.ellipse, {
    x, y, w: size, h: size, fill: { color }, line: { type: "none" },
  });
}

// ============================================================ 1. TITLE
{
  const s = pres.addSlide();
  base(s, { glow: false });
  s.addShape(pres.ShapeType.ellipse, {
    x: -3, y: -3.4, w: 10, h: 10,
    fill: { color: INDIGO, transparency: 86 }, line: { type: "none" },
  });
  s.addShape(pres.ShapeType.ellipse, {
    x: W - 5.4, y: HGT - 5.0, w: 9, h: 9,
    fill: { color: CYAN, transparency: 88 }, line: { type: "none" },
  });

  s.addText("AUTONOMOUS STRUCTURAL SCREENING", {
    x: M, y: 2.05, w: 10, h: 0.35, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 13, bold: true, color: CYAN, charSpacing: 3,
  });
  s.addText("TwinVerse Inspect AI", {
    x: M, y: 2.5, w: 11.5, h: 1.15, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 58, bold: true, color: TEXT,
  });
  s.addText("Inspect the unreachable.", {
    x: M, y: 3.62, w: 11.5, h: 0.6, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 27, color: CYAN,
  });
  s.addText(
    "Drone, CCTV and handheld imagery in — located defects, ranked severity, and a shareable report out.",
    { x: M, y: 4.32, w: 9.4, h: 0.6, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 15, color: MUTED },
  );

  [["Ayaan Aatif", "Team Lead"], ["Muhammad Muneed", "Team Member"], ["Inshrah Mehmood", "Team Member"]]
    .forEach(([name, role], i) => {
      const x = M + i * 3.5;
      dot(s, x, 5.52, [CYAN, INDIGO, VIOLET][i], 0.11);
      s.addText(name, {
        x: x + 0.22, y: 5.4, w: 3.1, h: 0.3, isTextBox: true, margin: 0,
        fontFace: B, fontSize: 14, bold: true, color: TEXT,
      });
      s.addText(role, {
        x: x + 0.22, y: 5.68, w: 3.1, h: 0.28, isTextBox: true, margin: 0,
        fontFace: B, fontSize: 11.5, color: DIM,
      });
    });

  s.addText("[ Event / Track ]   ·   [ Date ]   ·   Bano Qabil · Alkhidmat Foundation Pakistan", {
    x: M, y: 6.62, w: 11.8, h: 0.3, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 11, color: DIM,
  });
  s.addNotes(
    "Open on the problem, not the product. 'Inspectors climb bridges, rappel down dams, and walk pipelines with clipboards.' Then introduce the team.",
  );
}

// ============================================================ 2. PROBLEM
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "The problem");
  title(s, "Inspection today is manual, slow,\nand genuinely dangerous.", 0.98, { h: 1.5, fontSize: 34 });

  const items = [
    ["Dangerous", "Engineers rappel down dams and climb bridge soffits to look at concrete with their own eyes.", SEV_CRIT],
    ["Slow", "A single span can take days to survey. Backlogs mean structures go years between inspections.", SEV_HIGH],
    ["Inconsistent", "Two inspectors, two clipboards, two different answers about the same crack.", SEV_MED],
    ["Reactive", "Defects are found after they matter, not before. Maintenance is repair, not prevention.", VIOLET],
  ];
  items.forEach(([h, body, c], i) => {
    const x = M + (i % 2) * 6.05;
    const y = 2.72 + Math.floor(i / 2) * 1.72;
    card(s, x, y, 5.6, 1.45);
    dot(s, x + 0.32, y + 0.34, c, 0.16);
    s.addText(h, {
      x: x + 0.62, y: y + 0.22, w: 4.6, h: 0.35, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 16, bold: true, color: TEXT,
    });
    s.addText(body, {
      x: x + 0.62, y: y + 0.6, w: 4.75, h: 0.72, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: MUTED,
    });
  });
  s.addNotes("Keep this to 30 seconds. The audience already believes the problem — do not over-sell it.");
}

// ============================================================ 3. SOLUTION
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "What we built");
  title(s, "A first pass that never has to climb anything.");

  const steps = [
    ["01", "Capture", "Drone, CCTV, robot or a phone. Images or video.", CYAN],
    ["02", "Detect", "A fine-tuned YOLOv11 model locates cracks and draws a box around each one.", INDIGO],
    ["03", "Score", "Every detection gets a severity score from a formula shown on screen.", VIOLET],
    ["04", "Report", "Annotated images, a 3D view, and a PDF anyone can forward.", SEV_LOW],
  ];
  steps.forEach(([n, h, body, c], i) => {
    const x = M + i * 3.05;
    card(s, x, 2.5, 2.8, 2.9);
    s.addText(n, {
      x: x + 0.28, y: 2.72, w: 1, h: 0.5, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 26, bold: true, color: c,
    });
    s.addText(h, {
      x: x + 0.28, y: 3.3, w: 2.3, h: 0.35, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 17, bold: true, color: TEXT,
    });
    s.addText(body, {
      x: x + 0.28, y: 3.72, w: 2.32, h: 1.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: MUTED,
    });
    if (i < 3) {
      s.addText("›", {
        x: x + 2.86, y: 3.62, w: 0.2, h: 0.4, isTextBox: true, margin: 0,
        fontFace: H, fontSize: 22, bold: true, color: DIM, align: "center",
      });
    }
  });

  s.addText(
    "The engineer still decides. The system removes the part of the job that is climbing, photographing, and sorting.",
    { x: M, y: 5.75, w: 11.8, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 14, italic: true, color: CYAN },
  );
  s.addNotes("This is the elevator pitch slide. If you only get one slide, use this one.");
}

// ============================================================ 4. WHAT'S REAL
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "Status");
  title(s, "Not a mockup. A running system.");

  const stats = [
    ["104", "automated tests", CYAN],
    ["23", "endpoints", INDIGO],
    ["6.1s", "to analyse 8 images", VIOLET],
    ["7ms", "inference per image", SEV_LOW],
  ];
  stats.forEach(([big, label, c], i) => {
    const x = M + i * 3.05;
    card(s, x, 2.45, 2.8, 1.6);
    s.addText(big, {
      x: x + 0.28, y: 2.62, w: 2.3, h: 0.72, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 40, bold: true, color: c,
    });
    s.addText(label, {
      x: x + 0.28, y: 3.38, w: 2.3, h: 0.35, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: MUTED,
    });
  });

  const built = [
    "Upload API with S3-compatible object storage",
    "Fine-tuned crack detector, trained on 1,317 images",
    "Severity engine with a formula served live to the UI",
    "Next.js dashboard with 3D digital twin viewer",
    "PDF reports with a limitations page",
    "JWT auth, three roles, Docker Compose, CI",
  ];
  card(s, M, 4.3, 11.8, 2.15);
  built.forEach((t, i) => {
    const x = M + 0.4 + (i % 2) * 5.75;
    const y = 4.55 + Math.floor(i / 2) * 0.56;
    dot(s, x, y + 0.09, SEV_LOW, 0.1);
    s.addText(t, {
      x: x + 0.24, y, w: 5.3, h: 0.34, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, color: TEXT,
    });
  });
  s.addNotes("Switch to the live demo after this slide if the room is going well.");
}

// ============================================================ 5. EXPLAINABILITY
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "Explainability");
  title(s, "Every number can be recomputed by hand.");

  card(s, M, 2.45, 7.1, 3.5);
  s.addText("severity  =  area  ×  confidence  ×  class weight", {
    x: M + 0.4, y: 2.75, w: 6.3, h: 0.5, isTextBox: true, margin: 0,
    fontFace: "Courier New", fontSize: 16, bold: true, color: CYAN,
  });
  s.addText("A real detection from the demo data:", {
    x: M + 0.4, y: 3.42, w: 6.3, h: 0.3, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 12, color: MUTED,
  });
  s.addText("0.0288  ×  0.558  ×  1.0  =  0.01606", {
    x: M + 0.4, y: 3.78, w: 6.3, h: 0.45, isTextBox: true, margin: 0,
    fontFace: "Courier New", fontSize: 17, bold: true, color: TEXT,
  });
  s.addText(
    "The formula, the weights and the band thresholds are served by the API and rendered live — so what the dashboard shows can never drift from what the server computed.",
    { x: M + 0.4, y: 4.35, w: 6.3, h: 1.1, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, color: MUTED },
  );

  card(s, M + 7.45, 2.45, 4.35, 3.5);
  s.addText("SEVERITY BANDS", {
    x: M + 7.8, y: 2.7, w: 3.6, h: 0.3, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 11, bold: true, color: DIM, charSpacing: 1.8,
  });
  [["Critical", "> 0.014", SEV_CRIT], ["High", "0.011 – 0.014", SEV_HIGH],
   ["Medium", "0.009 – 0.011", SEV_MED], ["Low", "< 0.009", SEV_LOW]]
    .forEach(([name, range, c], i) => {
      const y = 3.12 + i * 0.62;
      dot(s, M + 7.8, y + 0.1, c, 0.14);
      s.addText(name, {
        x: M + 8.06, y, w: 1.6, h: 0.32, isTextBox: true, margin: 0,
        fontFace: B, fontSize: 13.5, bold: true, color: TEXT,
      });
      s.addText(range, {
        x: M + 9.6, y, w: 1.8, h: 0.32, isTextBox: true, margin: 0,
        fontFace: "Courier New", fontSize: 12, color: MUTED, align: "right",
      });
    });
  s.addText("Calibrated against 308 real detections, not assumed.", {
    x: M + 7.8, y: 5.6, w: 3.6, h: 0.3, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 10.5, italic: true, color: DIM,
  });
  s.addNotes("This is the differentiator. Most teams show a number. We show where the number came from.");
}

// ============================================================ 6. THE METRIC
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "The measurement that mattered");
  title(s, "The standard metric said all three models\nwere the same. They were not.", 0.98, { h: 1.5, fontSize: 32 });

  s.addChart(
    pres.ChartType.bar,
    [
      { name: "mAP50 (standard metric)", labels: ["Model A", "Model B", "Model C"], values: [0.442, 0.373, 0.436] },
      { name: "Separation (does it actually work)", labels: ["Model A", "Model B", "Model C"], values: [0.258, 0.0, 0.611] },
    ],
    {
      x: M, y: 2.62, w: 7.2, h: 3.35,
      barDir: "col", barGapWidthPct: 55,
      chartColors: [DIM, CYAN],
      showTitle: false, showLegend: true, legendPos: "t", legendColor: MUTED, legendFontSize: 10,
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: TEXT,
      dataLabelFontSize: 9, dataLabelFormatCode: "0.000",
      catAxisLabelColor: MUTED, catAxisLabelFontSize: 11,
      valAxisLabelColor: DIM, valAxisLabelFontSize: 9,
      valAxisMaxVal: 0.8, valGridLine: { color: LINE, size: 1 },
      catGridLine: { style: "none" }, plotArea: { fill: { color: BG } },
      chartArea: { fill: { color: BG } },
    },
  );

  card(s, M + 7.55, 2.62, 4.25, 3.35);
  s.addText("What we learned", {
    x: M + 7.9, y: 2.85, w: 3.6, h: 0.32, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 15, bold: true, color: TEXT,
  });
  s.addText(
    "mAP is computed only over defects that are labelled. A validation set with no clean images cannot catch a model that fires on everything.\n\n" +
    "So we tested each model against 94 defect-free photographs.\n\n" +
    "Model A looked fine and flagged half of all clean concrete. Model C flags one in five.\n\n" +
    "Then we asked the harder question: does it hold up on imagery from somewhere else?",
    { x: M + 7.9, y: 3.28, w: 3.6, h: 2.5, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: MUTED, lineSpacingMultiple: 1.12 },
  );
  s.addNotes(
    "If a judge asks one technical question, it will probably be about evaluation. This slide is the answer. Then turn the page — the next slide is the one they will remember.",
  );
}

// ================================================= 6b. THE GENERALISATION TEST
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "The number most teams never check");
  title(s, "Then we tested it on three datasets\nit had never seen.", 0.98, { h: 1.5, fontSize: 32 });

  s.addText(
    "Every accuracy figure above came from our own dataset's held-out split — different photographs, "
    + "but the same cameras and the same walls. So we ran it against three public datasets from "
    + "unrelated sources, none of which contributed anything to training.",
    { x: M, y: 2.32, w: 11.6, h: 0.8, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, color: MUTED, lineSpacingMultiple: 1.1 },
  );

  s.addChart(
    pres.ChartType.bar,
    [
      // All four sources, not the flattering one. Quoting only crack-bphdr
      // would be picking the best of the three unseen results, and the first
      // judge to ask "which dataset?" finds the other two.
      {
        name: "Cracks found",
        labels: ["nitw-crack\n(ours)", "crack-bphdr", "bridge-defect", "crack-b"],
        values: [0.813, 0.634, 0.126, 0.077],
      },
    ],
    {
      x: M, y: 3.3, w: 7.2, h: 2.75,
      barDir: "col", barGapWidthPct: 55,
      chartColors: [CYAN, DIM, DIM, DIM],
      varyColors: true,
      showTitle: false, showLegend: false,
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: TEXT,
      dataLabelFontSize: 11, dataLabelFormatCode: "0%",
      catAxisLabelColor: MUTED, catAxisLabelFontSize: 10,
      valAxisLabelColor: DIM, valAxisLabelFontSize: 9,
      valAxisMaxVal: 1.0, valGridLine: { color: LINE, size: 1 },
      catGridLine: { style: "none" }, plotArea: { fill: { color: BG } },
      chartArea: { fill: { color: BG } },
    },
  );

  card(s, M + 7.55, 3.3, 4.25, 2.75);
  s.addText("What this means", {
    x: M + 7.9, y: 3.52, w: 3.6, h: 0.32, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 15, bold: true, color: TEXT,
  });
  s.addText(
    "Four in five cracks on imagery like our training set. On three we had never seen, between "
    + "63% and 8%.\n\n"
    + "We could have shown you only the 63%. We are showing you all four, because the honest "
    + "claim is that this is tuned to one kind of concrete photography.",
    { x: M + 7.9, y: 3.95, w: 3.6, h: 2.0, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11.5, color: MUTED, lineSpacingMultiple: 1.12 },
  );

  s.addText(
    "We would rather tell you this than have you find it.",
    { x: M, y: 6.4, w: 11.8, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 14, italic: true, color: CYAN, align: "center" },
  );
  s.addNotes(
    "Deliver this confidently. Most teams quote the number from their own test split and have never "
    + "run this experiment. Volunteering the weaker figure, with the dataset named, is what separates "
    + "a measured system from a demo. If asked why it drops: the training set is one collection of "
    + "concrete from one campus. More varied data is the fix, not a threshold.",
  );
}

// ============================================================ 7. DIGITAL TWIN
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "Visualisation");
  title(s, "From a photograph to a structure you can orbit.");

  card(s, M, 2.5, 5.75, 3.5);
  s.addText("On the image", {
    x: M + 0.4, y: 2.78, w: 4.9, h: 0.35, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 16, bold: true, color: TEXT,
  });
  ["Bounding boxes drawn over each detection",
   "Colour and size both carry severity",
   "Hover a finding to see its arithmetic",
   "Boxes stored normalised, so they align at any zoom"].forEach((t, i) => {
    const y = 3.28 + i * 0.55;
    dot(s, M + 0.4, y + 0.08, CYAN, 0.1);
    s.addText(t, {
      x: M + 0.64, y, w: 4.7, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, color: MUTED,
    });
  });

  card(s, M + 6.1, 2.5, 5.7, 3.5);
  s.addText("Digital Twin v1", {
    x: M + 6.5, y: 2.78, w: 4.9, h: 0.35, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 16, bold: true, color: TEXT,
  });
  ["A 3D structure with glowing severity markers",
   "Click any marker for its source image and score",
   "Built in code — no scanning rig required",
   "Illustrative placement, and we say so on screen"].forEach((t, i) => {
    const y = 3.28 + i * 0.55;
    dot(s, M + 6.5, y + 0.08, VIOLET, 0.1);
    s.addText(t, {
      x: M + 6.74, y, w: 4.7, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12.5, color: MUTED,
    });
  });

  s.addText(
    "[ Replace this line with a screenshot of the dashboard and the 3D viewer ]",
    { x: M, y: 6.25, w: 11.8, h: 0.35, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11.5, italic: true, color: DIM, align: "center" },
  );
  s.addNotes("Orbit the viewer live if the demo is working. Then immediately state what it is not.");
}

// ============================================================ 8. HONESTY
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "What it does not do");
  title(s, "We measured the weaknesses too.");
  s.addText(
    "Every one of these is stated in the product itself and on the last page of every report.",
    { x: M, y: 1.95, w: 11.5, h: 0.35, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, color: CYAN },
  );

  const limits = [
    ["Cracks only", "One defect class. It has never seen corrosion or spalling and will not report them."],
    ["1 in 5 clean surfaces flagged", "Measured against 94 defect-free photographs. It errs toward flagging."],
    ["8-63% on unfamiliar imagery", "Versus 81% on imagery like its training data. Three unseen datasets, all published."],
    ["Severity is relative", "It ranks which crack to look at first. It does not measure width in millimetres."],
    ["The 3D view is illustrative", "Marker positions come from capture order, not surveyed coordinates."],
    ["Video counts are inflated", "Frames are analysed independently, so one crack can be counted many times."],
    ["Not an engineering assessment", "It is a screening pass. A qualified engineer still signs off."],
  ];
  // Three columns rather than two: the seventh limitation pushed a 2-wide grid
  // into a fourth row that ran off the bottom of the slide.
  limits.forEach(([h, body], i) => {
    const x = M + (i % 3) * 4.03;
    const y = 2.62 + Math.floor(i / 3) * 1.4;
    card(s, x, y, 3.75, 1.25);
    s.addText(h, {
      x: x + 0.26, y: y + 0.13, w: 3.25, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, bold: true, color: TEXT,
    });
    s.addText(body, {
      x: x + 0.26, y: y + 0.45, w: 3.3, h: 0.72, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 10.5, color: MUTED, lineSpacingMultiple: 1.05,
    });
  });

  s.addText(
    "Naming a weakness costs far less than being caught by it.",
    { x: M, y: 6.85, w: 11.8, h: 0.35, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 14, italic: true, color: CYAN, align: "center" },
  );
  s.addNotes(
    "Do not skip this slide to save time. It is the one that separates us. Deliver it confidently, not apologetically.",
  );
}

// ============================================================ 9. ARCHITECTURE
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "Under the hood");
  title(s, "Boring technology, deliberately.");

  const layers = [
    ["Frontend", "Next.js 16 · React 19 · Three.js · Tailwind", CYAN],
    ["API", "FastAPI · Python 3.12 · SQLAlchemy · Alembic", INDIGO],
    ["Model", "YOLOv11n fine-tuned · PyTorch 2.13 · CUDA 13", VIOLET],
    ["Data", "PostgreSQL 16 · MinIO (S3-compatible)", SEV_LOW],
    ["Ship", "Docker Compose · GitHub Actions CI · JWT + RBAC", SEV_MED],
  ];
  layers.forEach(([name, stack, c], i) => {
    const y = 2.45 + i * 0.78;
    card(s, M, y, 7.1, 0.64);
    dot(s, M + 0.3, y + 0.25, c, 0.14);
    s.addText(name, {
      x: M + 0.6, y: y + 0.15, w: 1.6, h: 0.34, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13.5, bold: true, color: TEXT,
    });
    s.addText(stack, {
      x: M + 2.2, y: y + 0.16, w: 4.7, h: 0.34, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11.5, color: MUTED,
    });
  });

  card(s, M + 7.55, 2.45, 4.25, 3.97);
  s.addText("Decisions on record", {
    x: M + 7.9, y: 2.68, w: 3.6, h: 0.32, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 14.5, bold: true, color: TEXT,
  });
  s.addText(
    "20 architectural decisions are written down with their reasoning — including the ones we got wrong, and one we had to publicly reverse after re-checking it.\n\n" +
    "A dataset that looked ideal and turned out unusable. A merge that made the model worse. A metric that hid a failure for an hour.\n\n" +
    "All of it is in the repository.",
    { x: M + 7.9, y: 3.1, w: 3.6, h: 3.1, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: MUTED, lineSpacingMultiple: 1.12 },
  );
  s.addNotes("Cloud note: the S3 layer means MinIO swaps for Alibaba OSS or AWS S3 with a config change only.");
}

// ============================================================ 10. TEAM
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "The team");
  title(s, "Three people, one build.");

  const team = [
    ["Ayaan Aatif", "Team Lead", "Architecture, ML pipeline, demo delivery", CYAN],
    ["Muhammad Muneed", "Team Member", "[ Add focus area ]", INDIGO],
    ["Inshrah Mehmood", "Team Member", "[ Add focus area ]", VIOLET],
  ];
  team.forEach(([name, role, focus, c], i) => {
    const x = M + i * 4.0;
    card(s, x, 2.5, 3.65, 3.55);
    // Photo placeholder — replace the ellipse with an addImage of a headshot.
    s.addShape(pres.ShapeType.ellipse, {
      x: x + 1.18, y: 2.82, w: 1.3, h: 1.3,
      fill: { color: c, transparency: 82 },
      line: { color: c, width: 1.5 },
    });
    s.addText("PHOTO", {
      x: x + 1.18, y: 3.34, w: 1.3, h: 0.28, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 9.5, color: c, align: "center", charSpacing: 1.4,
    });
    s.addText(name, {
      x: x + 0.25, y: 4.32, w: 3.15, h: 0.36, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 16, bold: true, color: TEXT, align: "center",
    });
    s.addText(role, {
      x: x + 0.25, y: 4.7, w: 3.15, h: 0.3, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 12, color: c, align: "center",
    });
    s.addText(focus, {
      x: x + 0.25, y: 5.06, w: 3.15, h: 0.7, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 11.5, color: MUTED, align: "center",
    });
  });

  s.addText("[ Add contact email · GitHub · LinkedIn ]", {
    x: M, y: 6.35, w: 11.8, h: 0.32, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 11.5, italic: true, color: DIM, align: "center",
  });
  s.addNotes("Replace the circles with headshots and fill in each member's focus area before presenting.");
}

// ============================================================ 11. ROADMAP
{
  const s = pres.addSlide();
  base(s);
  eyebrow(s, "What comes next");
  title(s, "The honest roadmap.");

  const now = ["Crack detection, measured on unseen data", "Severity scoring and PDF reports",
               "Dashboard, 3D viewer, auth, Docker"];
  const next = ["Varied training data to close the 63/81 gap", "More defect classes — corrosion, spalling",
                "Cross-frame tracking so video counts are real"];
  const later = ["Photogrammetric twin from the imagery itself",
                 "Predictive maintenance once trend data exists", "Live drone and robot integration"];

  [["SHIPPED", now, SEV_LOW], ["NEXT", next, CYAN], ["LATER", later, DIM]]
    .forEach(([label, items, c], i) => {
      const x = M + i * 4.0;
      card(s, x, 2.5, 3.65, 3.2);
      s.addText(label, {
        x: x + 0.3, y: 2.74, w: 3, h: 0.3, isTextBox: true, margin: 0,
        fontFace: B, fontSize: 11.5, bold: true, color: c, charSpacing: 2,
      });
      items.forEach((t, j) => {
        const y = 3.2 + j * 0.78;
        dot(s, x + 0.3, y + 0.08, c, 0.1);
        s.addText(t, {
          x: x + 0.54, y, w: 2.9, h: 0.68, isTextBox: true, margin: 0,
          fontFace: B, fontSize: 12, color: MUTED,
        });
      });
    });

  s.addText(
    "Predictive maintenance needs longitudinal data that does not exist yet. We are not going to pretend otherwise.",
    { x: M, y: 6.0, w: 11.8, h: 0.4, isTextBox: true, margin: 0,
      fontFace: B, fontSize: 13, italic: true, color: MUTED, align: "center" },
  );
  s.addNotes("The 'later' column is deliberately labelled later, not coming soon.");
}

// ============================================================ 12. CLOSE
{
  const s = pres.addSlide();
  base(s, { glow: false });
  s.addShape(pres.ShapeType.ellipse, {
    x: W / 2 - 5, y: -2.2, w: 10, h: 10,
    fill: { color: INDIGO, transparency: 88 }, line: { type: "none" },
  });

  s.addText("This does not replace an engineer.", {
    x: M, y: 2.35, w: 11.8, h: 0.8, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 40, bold: true, color: TEXT, align: "center",
  });
  s.addText(
    "It does the first pass, so the engineer spends their time on judgement\ninstead of data collection — and it tells you exactly how much to trust it.",
    { x: M, y: 3.35, w: 11.8, h: 1.0, isTextBox: true, margin: 0,
      fontFace: H, fontSize: 20, color: CYAN, align: "center", lineSpacingMultiple: 1.25 },
  );

  s.addText("TwinVerse Inspect AI", {
    x: M, y: 5.15, w: 11.8, h: 0.45, isTextBox: true, margin: 0,
    fontFace: H, fontSize: 22, bold: true, color: TEXT, align: "center",
  });
  s.addText("Ayaan Aatif  ·  Muhammad Muneed  ·  Inshrah Mehmood", {
    x: M, y: 5.65, w: 11.8, h: 0.35, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 14, color: MUTED, align: "center",
  });
  s.addText("[ Add repository link · contact email ]", {
    x: M, y: 6.1, w: 11.8, h: 0.32, isTextBox: true, margin: 0,
    fontFace: B, fontSize: 11.5, italic: true, color: DIM, align: "center",
  });
  s.addNotes("Land on the sentence, pause, then invite questions. Do not add a summary slide after this.");
}

pres.writeFile({ fileName: "TwinVerse_Inspect_AI_Pitch.pptx" })
  .then((f) => console.log("wrote", f));
