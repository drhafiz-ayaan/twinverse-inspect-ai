import { BAND_ORDER, BAND_STYLES, type SeverityBand } from "@/lib/api";

interface Props {
  counts: { severity_band: SeverityBand; count: number }[];
}

/**
 * Stacked proportion bar for the severity distribution.
 *
 * Bands are always rendered critical-first so the eye lands on the worst
 * finding, and every present band gets a minimum width so a single critical
 * detection among hundreds does not vanish into a hairline.
 */
export function SeverityBar({ counts }: Props) {
  const byBand = new Map(counts.map((c) => [c.severity_band, c.count]));
  const total = counts.reduce((sum, c) => sum + c.count, 0);

  if (total === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 dark:border-slate-700 px-4 py-6 text-center text-sm text-slate-500">
        No detections yet
      </div>
    );
  }

  return (
    <div>
      <div className="flex h-9 w-full overflow-hidden rounded-lg">
        {BAND_ORDER.map((band) => {
          const n = byBand.get(band) ?? 0;
          if (n === 0) return null;
          return (
            <div
              key={band}
              className={`${BAND_STYLES[band].dot} flex items-center justify-center text-xs font-medium text-white`}
              style={{ width: `${Math.max(6, (n / total) * 100)}%` }}
              title={`${band}: ${n}`}
            >
              {n / total > 0.1 ? n : ""}
            </div>
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5">
        {BAND_ORDER.map((band) => {
          const n = byBand.get(band) ?? 0;
          return (
            <div key={band} className="flex items-center gap-1.5 text-xs">
              <span className={`h-2 w-2 rounded-full ${BAND_STYLES[band].dot}`} />
              <span className="capitalize text-slate-600 dark:text-slate-400">
                {band}
              </span>
              <span className="font-medium tabular-nums text-slate-900 dark:text-slate-100">
                {n}
              </span>
              <span className="text-slate-400 tabular-nums">
                {total > 0 ? `${((n / total) * 100).toFixed(0)}%` : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
