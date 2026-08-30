"use client";

import { useState } from "react";
import {
  BAND_STROKE,
  type Detection,
  type MediaFile,
  type SeverityBand,
} from "@/lib/api";

interface Props {
  media: MediaFile;
  detections: Detection[];
}

/**
 * An image with its detections drawn over it.
 *
 * Boxes are stored normalized 0..1 (README D-009), so the overlay is an SVG
 * with `viewBox="0 0 1 1"` and `preserveAspectRatio="none"` stretched across
 * the image. No pixel arithmetic, and correct alignment at any rendered size
 * including responsive scaling.
 */
export function DetectionImage({ media, detections }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const active = detections.find((d) => d.id === selected) ?? null;
  const worst = detections.reduce(
    (max, d) => Math.max(max, d.severity_score ?? 0),
    0,
  );
  const worstBand =
    detections.find((d) => (d.severity_score ?? 0) === worst)?.severity_band ??
    null;

  return (
    <div className="glass glass-hover overflow-hidden">
      <div className="relative bg-black/40">
        {failed ? (
          <div className="flex aspect-video items-center justify-center px-4 text-center text-sm text-[var(--text-2)]">
            Could not load image. The download link may have expired — reload
            to get a fresh one.
          </div>
        ) : (
          <>
            {!loaded && media.media_type === "image" && (
              <div className="skeleton absolute inset-0" />
            )}

            {media.media_type === "video" ? (
              <video
                src={media.download_url}
                controls
                className="block w-full"
                onError={() => setFailed(true)}
                onLoadedData={() => setLoaded(true)}
              />
            ) : (
              // Plain <img>: the source is a presigned MinIO URL on another
              // origin, which next/image would need explicit host config for.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={media.download_url}
                alt={media.original_filename}
                className={`block w-full transition-opacity duration-500 ${
                  loaded ? "opacity-100" : "opacity-0"
                }`}
                onError={() => setFailed(true)}
                onLoad={() => setLoaded(true)}
              />
            )}

            {/* Analysis sweep, shown only while an upload is still unprocessed. */}
            {!media.processed && loaded && (
              <div className="scan pointer-events-none absolute inset-0 overflow-hidden" />
            )}

            {media.media_type === "image" && detections.length > 0 && loaded && (
              <svg
                viewBox="0 0 1 1"
                preserveAspectRatio="none"
                className="pointer-events-none absolute inset-0 h-full w-full"
              >
                {detections.map((d, i) => {
                  const band = (d.severity_band ?? "low") as SeverityBand;
                  const isActive = d.id === selected;
                  return (
                    <g key={d.id}>
                      <rect
                        x={d.bbox_x}
                        y={d.bbox_y}
                        width={d.bbox_width}
                        height={d.bbox_height}
                        fill={isActive ? BAND_STROKE[band] : "none"}
                        fillOpacity={isActive ? 0.18 : 0}
                        stroke={BAND_STROKE[band]}
                        strokeWidth={isActive ? 2.5 : 1.4}
                        vectorEffect="non-scaling-stroke"
                        style={{
                          filter: isActive
                            ? `drop-shadow(0 0 6px ${BAND_STROKE[band]})`
                            : undefined,
                          transition: "all 0.25s ease",
                          animation: `rise 0.5s ease ${i * 45}ms both`,
                        }}
                      />
                    </g>
                  );
                })}
              </svg>
            )}

            {detections.length > 0 && worstBand && (
              <span
                className="absolute right-2.5 top-2.5 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide backdrop-blur"
                style={{
                  color: BAND_STROKE[worstBand as SeverityBand],
                  background: `${BAND_STROKE[worstBand as SeverityBand]}22`,
                  boxShadow: `0 0 0 1px ${BAND_STROKE[worstBand as SeverityBand]}55`,
                }}
              >
                {worstBand}
              </span>
            )}
          </>
        )}
      </div>

      <div className="border-t border-white/5 px-4 py-3">
        <div className="flex items-baseline justify-between gap-3">
          <p className="truncate text-xs font-medium">{media.original_filename}</p>
          <p className="shrink-0 text-[11px] tabular-nums text-[var(--text-2)]">
            {detections.length} detection{detections.length === 1 ? "" : "s"}
          </p>
        </div>
        {media.width && media.height && (
          <p className="mt-0.5 text-[11px] text-[var(--text-2)]">
            {media.width}×{media.height}
            {media.duration_seconds ? ` · ${media.duration_seconds.toFixed(1)}s` : ""}
            {!media.processed && " · awaiting analysis"}
          </p>
        )}

        {detections.length > 0 && (
          <ul className="mt-3 space-y-0.5">
            {[...detections]
              .sort((a, b) => (b.severity_score ?? 0) - (a.severity_score ?? 0))
              .slice(0, 5)
              .map((d) => {
                const band = (d.severity_band ?? "low") as SeverityBand;
                return (
                  <li key={d.id}>
                    <button
                      type="button"
                      onMouseEnter={() => setSelected(d.id)}
                      onMouseLeave={() => setSelected(null)}
                      onFocus={() => setSelected(d.id)}
                      onBlur={() => setSelected(null)}
                      className={`flex w-full items-center gap-2 rounded-lg px-2 py-1 text-left text-[11px] transition ${
                        d.id === selected ? "bg-white/[0.07]" : "hover:bg-white/[0.04]"
                      }`}
                    >
                      <span
                        className="h-1.5 w-1.5 shrink-0 rounded-full"
                        style={{ background: BAND_STROKE[band] }}
                      />
                      <span className="capitalize text-[var(--text-1)]">
                        {d.defect_class.replace("_", " ")}
                      </span>
                      {d.frame_index !== null && (
                        <span className="text-[var(--text-2)]">
                          f{d.frame_index}
                        </span>
                      )}
                      <span className="ml-auto shrink-0 tabular-nums text-[var(--text-2)]">
                        {d.confidence.toFixed(2)}
                      </span>
                      <span
                        className="shrink-0 font-mono tabular-nums"
                        style={{ color: BAND_STROKE[band] }}
                      >
                        {d.severity_score?.toFixed(5) ?? "—"}
                      </span>
                    </button>
                  </li>
                );
              })}
            {detections.length > 5 && (
              <li className="px-2 pt-1 text-[11px] text-[var(--text-2)]">
                +{detections.length - 5} more
              </li>
            )}
          </ul>
        )}

        {active && (
          <p className="mt-2 rounded-lg bg-black/40 px-2.5 py-1.5 font-mono text-[10.5px] text-cyan-200/90 ring-1 ring-cyan-400/15">
            {active.normalized_area?.toFixed(4)} × {active.confidence.toFixed(3)} ×{" "}
            {active.class_weight?.toFixed(1)} = {active.severity_score?.toFixed(5)}
          </p>
        )}
      </div>
    </div>
  );
}
