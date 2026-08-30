"use client";

import { BAND_ORDER, BAND_STROKE, type SeverityBand } from "@/lib/api";
import { AnimatedCounter, useInView } from "@/components/ui/Motion";

interface Props {
  counts: { severity_band: SeverityBand; count: number }[];
}

/**
 * Stacked severity distribution.
 *
 * Ordered critical-first so the eye lands on the worst finding, and every
 * present band keeps a minimum width — a single critical detection among
 * hundreds must not collapse to an invisible hairline.
 */
export function SeverityBar({ counts }: Props) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const byBand = new Map(counts.map((c) => [c.severity_band, c.count]));
  const total = counts.reduce((sum, c) => sum + c.count, 0);

  if (total === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--line)] px-4 py-8 text-center text-sm text-[var(--text-2)]">
        No detections yet
      </div>
    );
  }

  return (
    <div ref={ref}>
      <div className="flex h-11 w-full overflow-hidden rounded-xl ring-1 ring-white/5">
        {BAND_ORDER.map((band, i) => {
          const n = byBand.get(band) ?? 0;
          if (n === 0) return null;
          const share = (n / total) * 100;
          return (
            <div
              key={band}
              className="relative flex items-center justify-center overflow-hidden text-xs font-semibold text-black/80"
              style={{
                width: inView ? `${Math.max(7, share)}%` : "0%",
                background: `linear-gradient(180deg, ${BAND_STROKE[band]}, ${BAND_STROKE[band]}cc)`,
                boxShadow: `inset 0 0 22px -6px #fff8`,
                transition: `width 1s cubic-bezier(0.2,0.7,0.3,1) ${i * 110}ms`,
              }}
              title={`${band}: ${n}`}
            >
              {share > 9 && <span className="relative z-10">{n}</span>}
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {BAND_ORDER.map((band, i) => {
          const n = byBand.get(band) ?? 0;
          const pct = total > 0 ? (n / total) * 100 : 0;
          return (
            <div
              key={band}
              className="rounded-lg bg-white/[0.03] px-3 py-2 ring-1 ring-white/5"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex items-center gap-1.5">
                <span
                  className="relative h-2 w-2 rounded-full"
                  style={{ background: BAND_STROKE[band], color: BAND_STROKE[band] }}
                />
                <span className="text-[10.5px] uppercase tracking-wider text-[var(--text-2)]">
                  {band}
                </span>
              </div>
              <p className="mt-0.5 flex items-baseline gap-1.5">
                <span
                  className="text-lg font-semibold tabular-nums"
                  style={{ color: BAND_STROKE[band] }}
                >
                  <AnimatedCounter value={n} />
                </span>
                <span className="text-[11px] tabular-nums text-[var(--text-2)]">
                  <AnimatedCounter value={pct} decimals={0} suffix="%" />
                </span>
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
