#!/usr/bin/env python3
"""Generate the shareable vision document.

Audience: someone with no context who needs to understand *what* was built and
why it matters — not how it was engineered. Deliberately contains no code, no
file paths and no framework names beyond a single stack line.

Dark cover and closing page, light interior: the interior is the part people
print or read on a phone, and dark body text on white survives both.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).parent / "TwinVerse_Inspect_AI_Vision.pdf"

# Palette mirrors the product interface.
BG = colors.HexColor("#070B14")
PANEL = colors.HexColor("#111A2E")
CYAN = colors.HexColor("#22D3EE")
INDIGO = colors.HexColor("#6366F1")
VIOLET = colors.HexColor("#A78BFA")
INK = colors.HexColor("#111827")
BODY = colors.HexColor("#374151")
MUTED = colors.HexColor("#6B7280")
RULE = colors.HexColor("#E5E7EB")

SEV = {
    "critical": colors.HexColor("#F43F5E"),
    "high": colors.HexColor("#F97316"),
    "medium": colors.HexColor("#F59E0B"),
    "low": colors.HexColor("#10B981"),
}

PW, PH = A4
MARGIN = 20 * mm


# ------------------------------------------------------------------ styles
S = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=21, leading=26,
                         textColor=INK, spaceAfter=5),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13.5, leading=17,
                         textColor=INK, spaceBefore=13, spaceAfter=5),
    "eyebrow": ParagraphStyle("eyebrow", fontName="Helvetica-Bold", fontSize=8.5,
                              leading=11, textColor=CYAN, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=16,
                           textColor=BODY, spaceAfter=7, alignment=TA_LEFT),
    "lead": ParagraphStyle("lead", fontName="Helvetica", fontSize=12.5, leading=19,
                           textColor=INK, spaceAfter=9),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=9, leading=13,
                            textColor=MUTED, spaceAfter=5),
    "quote": ParagraphStyle("quote", fontName="Helvetica-Oblique", fontSize=12,
                            leading=18, textColor=INK, leftIndent=10,
                            spaceBefore=6, spaceAfter=10),
    "cardh": ParagraphStyle("cardh", fontName="Helvetica-Bold", fontSize=10.5,
                            leading=13, textColor=INK, spaceAfter=2),
    "cardb": ParagraphStyle("cardb", fontName="Helvetica", fontSize=9.5,
                            leading=13.5, textColor=BODY),
    "stat": ParagraphStyle("stat", fontName="Helvetica-Bold", fontSize=22,
                           leading=25, textColor=INK, alignment=TA_CENTER),
    "statl": ParagraphStyle("statl", fontName="Helvetica", fontSize=8.5,
                            leading=11, textColor=MUTED, alignment=TA_CENTER),
}


def cover_page(canvas: pdfcanvas.Canvas, doc):
    """Dark cover drawn directly — no flowables."""
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, PW, PH, stroke=0, fill=1)

    # Soft corner glows, echoing the dashboard.
    for cx, cy, r, col, alpha in [
        (-30, PH + 40, 170, INDIGO, 0.20),
        (PW + 20, 40, 190, CYAN, 0.14),
    ]:
        canvas.saveState()
        canvas.setFillColor(col)
        canvas.setFillAlpha(alpha)
        canvas.circle(cx, cy, r, stroke=0, fill=1)
        canvas.restoreState()

    canvas.setFillColor(CYAN)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, PH - 150, "A U T O N O M O U S   S T R U C T U R A L   S C R E E N I N G")

    canvas.setFillColor(colors.HexColor("#E8EEF8"))
    canvas.setFont("Helvetica-Bold", 34)
    canvas.drawString(MARGIN, PH - 200, "TwinVerse Inspect AI")

    canvas.setFillColor(CYAN)
    canvas.setFont("Helvetica", 19)
    canvas.drawString(MARGIN, PH - 232, "Inspect the unreachable.")

    canvas.setFillColor(colors.HexColor("#9FB0CC"))
    canvas.setFont("Helvetica", 11)
    for i, line in enumerate([
        "Engineers climb bridges, rappel down dams and walk pipelines",
        "with clipboards. This does that first pass from a photograph —",
        "and tells you exactly how much to trust the answer.",
    ]):
        canvas.drawString(MARGIN, PH - 275 - i * 17, line)

    # Severity swatch strip — the product's own visual signature.
    x = MARGIN
    for key in ("low", "medium", "high", "critical"):
        canvas.setFillColor(SEV[key])
        canvas.roundRect(x, 150, 78, 7, 3.5, stroke=0, fill=1)
        x += 86

    canvas.setFillColor(colors.HexColor("#E8EEF8"))
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(MARGIN, 120, "Ayaan Aatif  ·  Muhammad Muneed  ·  Inshrah Mehmood")
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont("Helvetica", 9)
    canvas.drawString(MARGIN, 104, "[ Event / Track ]   ·   [ Date ]   ·   Bano Qabil · Alkhidmat Foundation Pakistan")
    canvas.restoreState()


def interior_page(canvas: pdfcanvas.Canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, PW, PH, stroke=0, fill=1)

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(MARGIN, PH - 34, PW - MARGIN, PH - 34)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, PH - 30, "TwinVerse Inspect AI")
    canvas.drawRightString(PW - MARGIN, PH - 30, "What we built")

    canvas.line(MARGIN, 42, PW - MARGIN, 42)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, 31, "First-pass screening. Findings require confirmation by a qualified engineer.")
    canvas.drawRightString(PW - MARGIN, 31, str(doc.page - 1))
    canvas.restoreState()


def closing_page(canvas: pdfcanvas.Canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, PW, PH, stroke=0, fill=1)
    canvas.saveState()
    canvas.setFillColor(INDIGO)
    canvas.setFillAlpha(0.18)
    canvas.circle(PW / 2, PH + 30, 210, stroke=0, fill=1)
    canvas.restoreState()

    canvas.setFillColor(colors.HexColor("#E8EEF8"))
    canvas.setFont("Helvetica-Bold", 21)
    canvas.drawCentredString(PW / 2, PH / 2 + 60, "This does not replace an engineer.")
    canvas.setFillColor(CYAN)
    canvas.setFont("Helvetica", 12.5)
    canvas.drawCentredString(PW / 2, PH / 2 + 28,
                             "It does the first pass, so the engineer spends their time on judgement")
    canvas.drawCentredString(PW / 2, PH / 2 + 10,
                             "instead of data collection.")

    # Team, spaced across the lower third.
    team = [
        ("Ayaan Aatif", "Team Lead", CYAN),
        ("Muhammad Muneed", "Team Member", INDIGO),
        ("Inshrah Mehmood", "Team Member", VIOLET),
    ]
    col = (PW - 2 * MARGIN) / 3
    for i, (name, role, accent) in enumerate(team):
        cx = MARGIN + col * i + col / 2
        canvas.setFillColor(accent)
        canvas.circle(cx, 268, 3.5, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#E8EEF8"))
        canvas.setFont("Helvetica-Bold", 11.5)
        canvas.drawCentredString(cx, 240, name)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.setFont("Helvetica", 9.5)
        canvas.drawCentredString(cx, 224, role)

    canvas.setFillColor(colors.HexColor("#9FB0CC"))
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(PW / 2, 160, "TwinVerse Inspect AI")
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(PW / 2, 142, "[ Add contact email · repository link ]")
    canvas.restoreState()


def section(eyebrow_text, heading_text):
    """Eyebrow + heading as one unbreakable unit.

    Emitted separately, a page break can land between them and leave a stray
    coloured label alone at the bottom of a page.
    """
    return KeepTogether([
        Paragraph(eyebrow_text, S["eyebrow"]),
        Paragraph(heading_text, S["h1"]),
        Spacer(1, 5),
    ])


def card_row(items, widths=None):
    """Row of bordered cards: [(heading, body, accent), ...]."""
    cells = []
    for head, body, accent in items:
        inner = Table(
            [[Paragraph(head, S["cardh"])], [Paragraph(body, S["cardb"])]],
            colWidths=[(PW - 2 * MARGIN) / len(items) - 14],
        )
        inner.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        cells.append(inner)

    t = Table([cells], colWidths=[(PW - 2 * MARGIN) / len(items)] * len(items))
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, RULE),
    ]
    for i, (_, _, accent) in enumerate(items):
        style.append(("LINEBELOW", (i, 0), (i, 0), 2.2, accent))
    t.setStyle(TableStyle(style))
    # Own the gap below: without it a following eyebrow renders flush against
    # the accent rule and reads as part of the card.
    return KeepTogether([t, Spacer(1, 16)])


def stat_row(items):
    """[(value, label, colour)] rendered as large numerals."""
    cells = []
    for value, label, col in items:
        vs = ParagraphStyle("v", parent=S["stat"], textColor=col)
        inner = Table([[Paragraph(value, vs)], [Paragraph(label, S["statl"])]],
                      colWidths=[(PW - 2 * MARGIN) / len(items) - 12])
        inner.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        cells.append(inner)
    t = Table([cells], colWidths=[(PW - 2 * MARGIN) / len(items)] * len(items))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, RULE),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFBFC")),
    ]))
    return KeepTogether([t, Spacer(1, 14)])


def build():
    doc = BaseDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 22, bottomMargin=MARGIN + 12,
        title="TwinVerse Inspect AI — What we built",
        author="Ayaan Aatif, Muhammad Muneed, Inshrah Mehmood",
        subject="AI-powered infrastructure inspection",
    )
    frame = Frame(MARGIN, MARGIN + 12, PW - 2 * MARGIN,
                  PH - 2 * MARGIN - 34, id="body")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=cover_page),
        PageTemplate(id="interior", frames=[frame], onPage=interior_page),
        PageTemplate(id="closing", frames=[frame], onPage=closing_page),
    ])

    st = []
    # -- cover (drawn) ----------------------------------------------------
    st.append(NextPageTemplate("interior"))
    st.append(PageBreak())

    # -- page 1 -----------------------------------------------------------
    st.append(section("THE PROBLEM", "Someone has to go and look at it."))
    st.append(Paragraph(
        "Every bridge, dam, tunnel and building has to be inspected. Today that means a person "
        "physically getting close enough to see the concrete — climbing, rappelling, or walking "
        "the length of it with a clipboard.", S["lead"]))
    st.append(Paragraph(
        "It is dangerous work. It is slow enough that backlogs build and structures go years "
        "between inspections. And it is inconsistent: two inspectors looking at the same crack "
        "will often write down two different things.", S["body"]))
    st.append(Paragraph(
        "The result is that most maintenance is <b>reactive</b>. Problems are found after they "
        "matter rather than before.", S["body"]))

    st.append(Spacer(1, 10))
    st.append(card_row([
        ("Dangerous", "People work at height and over water to look at concrete with their own eyes.", SEV["critical"]),
        ("Slow", "A single span can take days. Backlogs mean long gaps between inspections.", SEV["high"]),
        ("Inconsistent", "Two inspectors, two clipboards, two different answers.", SEV["medium"]),
    ]))

    st.append(section("WHAT WE BUILT", "A first pass that never has to climb anything."))
    st.append(Paragraph(
        "TwinVerse Inspect AI takes ordinary imagery — from a drone, a fixed camera, or a phone — "
        "and does the first pass automatically. It finds cracks, ranks how serious each one is, "
        "shows them on the photograph and on a 3D view of the structure, and produces a report "
        "anyone can forward.", S["lead"]))
    st.append(Paragraph(
        "The engineer still makes every decision. What changes is that they start from a sorted "
        "list of findings instead of from a memory card full of photographs.", S["body"]))

    st.append(Spacer(1, 6))
    st.append(section("HOW IT WORKS", "Four steps, no black box."))
    st.append(card_row([
        ("1 · Capture", "Upload images or video. Drone, CCTV, robot or phone — it does not care which.", CYAN),
        ("2 · Detect", "A trained model finds each crack and draws a box around it.", INDIGO),
        ("3 · Score", "Each finding gets a severity score from a formula shown on screen.", VIOLET),
        ("4 · Report", "Annotated images, a 3D view, and a PDF for whoever needs it.", SEV["low"]),
    ]))
    st.append(Spacer(1, 14))

    st.append(section("WHY IT IS DIFFERENT", "You can check its work."))
    st.append(Paragraph(
        "Most systems of this kind give you a number and ask you to trust it. This one shows the "
        "arithmetic. Every severity score on screen is three values multiplied together, and all "
        "three are stored with the finding:", S["body"]))
    st.append(Spacer(1, 4))

    formula = Table([[Paragraph(
        '<font face="Courier-Bold" size="11" color="#111827">'
        'severity &nbsp;=&nbsp; area &nbsp;×&nbsp; confidence &nbsp;×&nbsp; class weight</font><br/>'
        '<font face="Courier" size="10" color="#6B7280">'
        '0.0288 &nbsp;×&nbsp; 0.558 &nbsp;×&nbsp; 1.0 &nbsp;=&nbsp; 0.01606</font>',
        S["cardb"])]], colWidths=[PW - 2 * MARGIN])
    formula.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    st.append(formula)
    st.append(Spacer(1, 8))
    st.append(Paragraph(
        "A reader can recompute any figure by hand from the record it came from. That is a "
        "deliberate design choice, not a feature — it is the difference between a tool an "
        "engineer can sign off on and one they cannot.", S["body"]))

    st.append(Spacer(1, 10))
    st.append(section("WHERE IT STANDS", "A running system, not a mockup."))
    st.append(stat_row([
        ("101", "automated tests", INK),
        ("6.1s", "to analyse 8 images", INK),
        ("7ms", "per image on a GPU", INK),
        ("81%", "of cracks found", INK),
    ]))

    st.append(PageBreak())

    # -- page 3 -----------------------------------------------------------
    st.append(section("BEING HONEST ABOUT IT", "We measured the weaknesses too."))
    st.append(Paragraph(
        "Anything that inspects infrastructure has to be trustworthy before it is impressive. "
        "Every limitation below is stated inside the product itself and printed on the last page "
        "of every report it generates.", S["lead"]))
    st.append(Spacer(1, 6))

    limits = [
        ("It finds cracks, and only cracks.",
         "The model has never been shown corrosion, spalling or missing components. It will not "
         "report them even if they are in the picture."),
        ("Roughly one clean surface in five gets flagged.",
         "Measured against 94 photographs of undamaged concrete. It is a screening tool and it "
         "errs toward flagging — a human reviews everything it raises."),
        ("Severity is a ranking, not a measurement.",
         "It tells you which crack to look at first. It does not tell you how wide the crack is "
         "in millimetres — that needs camera calibration or a physical scale in the frame."),
        ("The 3D view is illustrative.",
         "The structure shown is a generic model, and marker positions come from the order the "
         "photographs were taken, not from surveyed coordinates."),
        ("Video counts are inflated.",
         "Frames are analysed independently, so a single crack visible across ten frames is "
         "counted ten times."),
    ]
    for head, body in limits:
        block = Table([[Paragraph(head, S["cardh"])], [Paragraph(body, S["cardb"])]],
                      colWidths=[PW - 2 * MARGIN - 18])
        block.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        wrapper = Table([[block]], colWidths=[PW - 2 * MARGIN])
        wrapper.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FCFCFD")),
            ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ]))
        st.append(KeepTogether([wrapper, Spacer(1, 6)]))

    st.append(Spacer(1, 4))
    st.append(Paragraph(
        "&ldquo;Naming a weakness costs far less than being caught by it.&rdquo;", S["quote"]))

    st.append(Spacer(1, 8))
    st.append(section("WHAT COMES NEXT", "The honest roadmap."))
    st.append(card_row([
        ("Next", "More defect types. Tracking cracks across video frames so counts are real.", CYAN),
        ("Later", "A true photogrammetric twin built from the imagery itself.", INDIGO),
        ("Someday", "Predictive maintenance — which needs years of data that does not exist yet.", MUTED),
    ]))

    st.append(Spacer(1, 12))
    st.append(NextPageTemplate("closing"))
    st.append(PageBreak())
    # ReportLab discards a trailing PageBreak with no flowable after it, so the
    # closing template would never render. One invisible spacer forces the page.
    st.append(Spacer(1, 1))

    doc.build(st)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
