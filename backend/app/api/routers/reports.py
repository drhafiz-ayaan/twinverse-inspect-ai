"""PDF report export."""

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_inspection_or_404
from app.db.models import Asset, Detection, Inspection, MediaFile
from app.db.session import get_db
from app.services import reporting

router = APIRouter(tags=["reports"])


def _filename(asset_name: str, title: str) -> str:
    """A safe, descriptive download name.

    Anything outside a conservative allowlist is stripped rather than escaped —
    asset names come from user input and end up in a Content-Disposition
    header, where a stray quote or newline is a header-injection vector.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", f"{asset_name}-{title}").strip("-").lower()
    return f"{(slug or 'inspection')[:80]}-{stamp}.pdf"


@router.get(
    "/inspections/{inspection_id}/report.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def inspection_report(
    inspection: Inspection = Depends(get_inspection_or_404),
    db: Session = Depends(get_db),
) -> Response:
    """Render an inspection as a downloadable PDF."""
    asset = db.get(Asset, inspection.asset_id)
    media = list(
        db.scalars(
            select(MediaFile)
            .where(MediaFile.inspection_id == inspection.id)
            .order_by(MediaFile.created_at)
        )
    )
    detections = list(
        db.scalars(
            select(Detection)
            .join(MediaFile, MediaFile.id == Detection.media_file_id)
            .where(MediaFile.inspection_id == inspection.id)
        )
    )

    pdf = reporting.build_report(inspection, asset, media, detections)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="{_filename(asset.name, inspection.title)}"'
        },
    )
