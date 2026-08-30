import type { Detection, MediaFile } from "@/lib/api";

/**
 * Projecting 2D detections onto a 3D structure.
 *
 * IMPORTANT — this is a presentation convention, not a measurement.
 *
 * Detections are bounding boxes in image space. Nothing in the pipeline
 * recovers where a photograph was taken from or which part of the structure it
 * shows, so there is no true 3D position to place a marker at. Deriving one
 * would need camera pose, photogrammetry or a surveyed reference — all out of
 * MVP scope (README D-003).
 *
 * Rather than invent positions, the viewer applies one stated rule:
 *
 *   - Media files are assumed captured **sequentially along the span**, so the
 *     Nth file maps to the Nth station along the deck's long axis.
 *   - Within a frame, the box's horizontal centre maps to lateral offset and
 *     its vertical centre to height, with the image's top-down Y inverted.
 *
 * If the imagery was not captured in span order, the along-span axis means
 * nothing. That caveat is displayed beside the viewer rather than buried here,
 * because a 3D view invites the reader to believe it was surveyed.
 */

export interface PlacedMarker {
  detection: Detection;
  media: MediaFile;
  /** Scene-space position in the viewer's arbitrary units. */
  position: [number, number, number];
}

export const DECK_LENGTH = 24;
export const DECK_WIDTH = 6;
export const DECK_HEIGHT = 4;

export function placeMarkers(
  media: MediaFile[],
  detections: Detection[],
): PlacedMarker[] {
  const ordered = [...media].sort(
    (a, b) => Date.parse(a.created_at) - Date.parse(b.created_at),
  );
  const stationOf = new Map(ordered.map((m, i) => [m.id, i]));
  const byId = new Map(media.map((m) => [m.id, m]));
  const stations = Math.max(1, ordered.length);

  return detections.flatMap((d) => {
    const source = byId.get(d.media_file_id);
    const station = stationOf.get(d.media_file_id);
    if (!source || station === undefined) return [];

    // Stations spread evenly along the deck, centred on the origin.
    const t = stations === 1 ? 0.5 : station / (stations - 1);
    const x = (t - 0.5) * DECK_LENGTH * 0.9;

    const cx = d.bbox_x + d.bbox_width / 2;
    const cy = d.bbox_y + d.bbox_height / 2;

    // Image X maps across the deck's width; image Y is inverted, since image
    // space counts downward and the scene counts upward.
    const z = (cx - 0.5) * DECK_WIDTH * 0.85;
    const y = DECK_HEIGHT + (0.5 - cy) * 1.6;

    return [
      {
        detection: d,
        media: source,
        position: [x, y, z] as [number, number, number],
      },
    ];
  });
}
