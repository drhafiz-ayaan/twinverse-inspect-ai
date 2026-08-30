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
 * the image. That means no pixel arithmetic and correct alignment at any
 * rendered size — including when the browser scales the image responsively.
 */
export function DetectionImage({ media, detections }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  const active = detections.find((d) => d.id === selected) ?? null;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="relative bg-slate-100 dark:bg-slate-950">
        {failed ? (
          <div className="flex aspect-video items-center justify-center px-4 text-center text-sm text-slate-500">
            Could not load image. The download link may have expired —
            reload the page to get a fresh one.
          </div>
        ) : (
          <>
            {media.media_type === "video" ? (
              <video
                src={media.download_url}
                controls
                className="block w-full"
                onError={() => setFailed(true)}
              />
            ) : (
              // Plain <img>: the source is a presigned MinIO URL on another
              // origin, which next/image would need explicit host config for.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={media.download_url}
                alt={media.original_filename}
                className="block w-full"
                onError={() => setFailed(true)}
              />
            )}

            {media.media_type === "image" && detections.length > 0 && (
              <svg
                viewBox="0 0 1 1"
                preserveAspectRatio="none"
                className="pointer-events-none absolute inset-0 h-full w-full"
              >
                {detections.map((d) => {
                  const band = (d.severity_band ?? "low") as SeverityBand;
                  const isActive = d.id === selected;
                  return (
                    <rect
                      key={d.id}
                      x={d.bbox_x}
                      y={d.bbox_y}
                      width={d.bbox_width}
                      height={d.bbox_height}
                      fill={isActive ? BAND_STROKE[band] : "none"}
                      fillOpacity={isActive ? 0.15 : 0}
                      stroke={BAND_STROKE[band]}
                      strokeWidth={isActive ? 0.006 : 0.003}
                      vectorEffect="non-scaling-stroke"
                    />
                  );
                })}
              </svg>
            )}
          </>
        )}
      </div>

      <div className="border-t border-slate-200 px-4 py-3 dark:border-slate-800">
        <div className="flex items-baseline justify-between gap-3">
          <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
            {media.original_filename}
          </p>
          <p className="shrink-0 text-xs text-slate-500">
            {detections.length} detection{detections.length === 1 ? "" : "s"}
          </p>
        </div>
        {media.width && media.height && (
          <p className="mt-0.5 text-xs text-slate-500">
            {media.width}×{media.height}
            {media.duration_seconds
              ? ` · ${media.duration_seconds.toFixed(1)}s`
              : ""}
            {!media.processed && " · not yet analysed"}
          </p>
        )}

        {detections.length > 0 && (
          <ul className="mt-3 space-y-1">
            {[...detections]
              .sort((a, b) => (b.severity_score ?? 0) - (a.severity_score ?? 0))
              .slice(0, 6)
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
                      className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left text-xs transition ${
                        d.id === selected
                          ? "bg-slate-100 dark:bg-slate-800"
                          : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                      }`}
                    >
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ background: BAND_STROKE[band] }}
                      />
                      <span className="capitalize text-slate-700 dark:text-slate-300">
                        {d.defect_class.replace("_", " ")}
                      </span>
                      {d.frame_index !== null && (
                        <span className="text-slate-400">
                          frame {d.frame_index}
                        </span>
                      )}
                      <span className="ml-auto shrink-0 tabular-nums text-slate-500">
                        conf {d.confidence.toFixed(2)}
                      </span>
                      <span className="shrink-0 tabular-nums font-medium text-slate-900 dark:text-slate-100">
                        {d.severity_score?.toFixed(5) ?? "—"}
                      </span>
                    </button>
                  </li>
                );
              })}
            {detections.length > 6 && (
              <li className="px-2 pt-1 text-xs text-slate-400">
                +{detections.length - 6} more
              </li>
            )}
          </ul>
        )}

        {active && (
          <p className="mt-2 rounded bg-slate-50 px-2 py-1.5 font-mono text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-400">
            {active.normalized_area?.toFixed(4)} × {active.confidence.toFixed(3)}{" "}
            × {active.class_weight?.toFixed(1)} ={" "}
            {active.severity_score?.toFixed(5)}
          </p>
        )}
      </div>
    </div>
  );
}
