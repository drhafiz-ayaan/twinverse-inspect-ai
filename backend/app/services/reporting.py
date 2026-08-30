"""PDF inspection reports.

Renders an inspection to a self-contained PDF: summary counts, severity
distribution, the scoring formula, the highest-severity detections, and a
limitations section.

The limitations section is not boilerplate. A report that lists defects
without stating the detector's false-positive rate invites the reader to treat
it as an authoritative survey, which it is not (README D-016). Naming the
limits in the artefact itself is the same discipline D-004 applies to the
severity score.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.db.models import Asset, Detection, Inspection, MediaFile, SeverityBand
from app.services import inference, severity

BAND_COLOURS: dict[SeverityBand, colors.Color] = {
    SeverityBand.LOW: colors.HexColor("#4a7c59"),
    SeverityBand.MEDIUM: colors.HexColor("#c9a227"),
    SeverityBand.HIGH: colors.HexColor("#d1691e"),
    SeverityBand.CRITICAL: colors.HexColor("#b3261e"),
}

BAND_ORDER = [
    SeverityBand.CRITICAL,
    SeverityBand.HIGH,
    SeverityBand.MEDIUM,
    SeverityBand.LOW,
]


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "T", parent=base["Title"], fontSize=20, spaceAfter=2 * mm,
            textColor=colors.HexColor("#1a2b40"),
        ),
        "sub": ParagraphStyle(
            "S", parent=base["Normal"], fontSize=10,
            textColor=colors.HexColor("#5a6b7d"), spaceAfter=6 * mm,
        ),
        "h2": ParagraphStyle(
            "H", parent=base["Heading2"], fontSize=13, spaceBefore=6 * mm,
            spaceAfter=2 * mm, textColor=colors.HexColor("#1a2b40"),
        ),
        "body": ParagraphStyle(
            "B", parent=base["Normal"], fontSize=9.5, leading=14,
            alignment=TA_LEFT,
        ),
        "mono": ParagraphStyle(
            "M", parent=base["Code"], fontSize=9, leading=13,
            backColor=colors.HexColor("#f2f4f7"), borderPadding=4,
        ),
        "caveat": ParagraphStyle(
            "C", parent=base["Normal"], fontSize=8.5, leading=12,
            textColor=colors.HexColor("#5a6b7d"),
        ),
    }


def _severity_bar(counts: dict[SeverityBand, int], width: float = 150 * mm):
    """A stacked proportion bar. Drawn with a table so it needs no chart lib."""
    total = sum(counts.values())
    if total == 0:
        return None

    cells, widths, style = [], [], [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    col = 0
    for band in BAND_ORDER:
        n = counts.get(band, 0)
        if not n:
            continue
        share = n / total
        cells.append(f"{band.value} {n}" if share > 0.12 else str(n))
        widths.append(max(14 * mm, width * share))
        style.append(("BACKGROUND", (col, 0), (col, 0), BAND_COLOURS[band]))
        col += 1

    return Table([cells], colWidths=widths, style=TableStyle(style))


def build_report(
    inspection: Inspection,
    asset: Asset,
    media: list[MediaFile],
    detections: list[Detection],
) -> bytes:
    """Render the inspection to PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Inspection report — {inspection.title}",
        author="TwinVerse Inspect AI",
    )
    s = _styles()
    story: list = []

    # --- header ---
    story.append(Paragraph("Infrastructure Inspection Report", s["title"]))
    story.append(Paragraph(
        f"{asset.name} &nbsp;·&nbsp; {asset.asset_type.value}"
        + (f" &nbsp;·&nbsp; {asset.location}" if asset.location else ""),
        s["sub"],
    ))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#d7dde5")))

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = [
        ["Inspection", inspection.title],
        ["Status", inspection.status.value],
        ["Media analysed", f"{sum(1 for m in media if m.processed)} of {len(media)}"],
        ["Detections", str(len(detections))],
        ["Model", inference.active_detector().weights.split("/")[-1]],
        ["Confidence threshold", f"{settings.confidence_threshold:.2f}"],
        ["Generated", generated],
    ]
    story.append(Spacer(1, 4 * mm))
    story.append(Table(
        meta, colWidths=[45 * mm, 115 * mm],
        style=TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#5a6b7d")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]),
    ))

    # --- severity distribution ---
    counts: dict[SeverityBand, int] = {}
    for d in detections:
        if d.severity_band is not None:
            counts[d.severity_band] = counts.get(d.severity_band, 0) + 1

    story.append(Paragraph("Severity distribution", s["h2"]))
    bar = _severity_bar(counts)
    if bar is not None:
        story.append(bar)
        story.append(Spacer(1, 3 * mm))
        scores = [d.severity_score for d in detections if d.severity_score is not None]
        if scores:
            story.append(Paragraph(
                f"Highest score {max(scores):.5f} &nbsp;·&nbsp; "
                f"mean {sum(scores) / len(scores):.5f}",
                s["caveat"],
            ))
    else:
        story.append(Paragraph("No defects detected.", s["body"]))

    # --- the formula, on the page ---
    model = severity.describe()
    story.append(Paragraph("How severity is calculated", s["h2"]))
    story.append(Paragraph(model["formula"], s["mono"]))
    story.append(Spacer(1, 2 * mm))
    weights = " &nbsp;|&nbsp; ".join(
        f"{k} {v}" for k, v in model["class_weights"].items()
    )
    bands = " &nbsp;|&nbsp; ".join(
        f"{k} {v[0]:.3f}–{v[1]:.3f}" for k, v in model["bands"].items()
    )
    story.append(Paragraph(f"<b>Class weights:</b> {weights}", s["body"]))
    story.append(Paragraph(f"<b>Bands:</b> {bands}", s["body"]))

    # --- top detections ---
    scored = sorted(
        (d for d in detections if d.severity_score is not None),
        key=lambda d: d.severity_score, reverse=True,
    )[:15]
    if scored:
        story.append(Paragraph("Highest-severity detections", s["h2"]))
        by_id = {m.id: m for m in media}
        rows = [["#", "Source", "Class", "Conf.", "Area", "Score", "Band"]]
        for n, d in enumerate(scored, 1):
            src = by_id.get(d.media_file_id)
            name = (src.original_filename if src else "—")
            if len(name) > 26:
                name = name[:23] + "..."
            if d.frame_index is not None:
                name += f" @{d.frame_index}"
            rows.append([
                str(n), name, d.defect_class.value,
                f"{d.confidence:.3f}", f"{d.normalized_area:.4f}",
                f"{d.severity_score:.5f}", d.severity_band.value,
            ])

        table = Table(rows, colWidths=[8*mm, 52*mm, 24*mm, 18*mm, 20*mm, 22*mm, 20*mm])
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2b40")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (3, 1), (-2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7dde5")),
        ]
        for i, d in enumerate(scored, 1):
            style.append(
                ("TEXTCOLOR", (6, i), (6, i), BAND_COLOURS[d.severity_band])
            )
            if i % 2 == 0:
                style.append(
                    ("BACKGROUND", (0, i), (5, i), colors.HexColor("#f7f9fb"))
                )
        table.setStyle(TableStyle(style))
        story.append(table)
        if len(detections) > len(scored):
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(
                f"Showing the {len(scored)} highest of {len(detections)} detections.",
                s["caveat"],
            ))

    # --- limitations ---
    story.append(PageBreak())
    story.append(Paragraph("Limitations of this report", s["h2"]))
    for text in [
        "<b>Severity is relative, not absolute.</b> " + str(model["limitation"]),
        "<b>This is a first-pass screening tool, not a structural assessment.</b> "
        "Detections are automated and unreviewed. Findings should be confirmed by "
        "a qualified engineer before any maintenance decision.",
        "<b>False positives occur on undamaged surfaces.</b> Measured against 94 "
        "defect-free reference photographs, the detector flagged roughly one in "
        "five at the configured threshold. A listed detection is not proof of a "
        "defect.",
        "<b>Only cracks are detected.</b> The model is trained on a single defect "
        "class. Corrosion, spalling, missing components and any other defect type "
        "will not appear in this report even if present in the imagery.",
        "<b>Video counts are inflated.</b> Frames are sampled independently and "
        "detections are not matched across them, so one physical defect visible in "
        "several frames is counted several times.",
    ]:
        story.append(Paragraph(text, s["body"]))
        story.append(Spacer(1, 2.5 * mm))

    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#d7dde5")))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"TwinVerse Inspect AI · inspection {inspection.id} · generated {generated}",
        s["caveat"],
    ))

    doc.build(story)
    return buffer.getvalue()
