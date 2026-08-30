import {
  BAND_STROKE,
  type DetectorInfo,
  type SeverityBand,
  type SeverityModel,
} from "@/lib/api";
import { api } from "@/lib/server-api";

/**
 * The scoring model, on screen.
 *
 * Fetched from the API rather than hardcoded so what the dashboard shows
 * cannot drift from what the server computes — which is the whole point of
 * README D-004's commitment to visible scoring. A formula displayed from a
 * stale copy would be worse than showing none.
 */
export async function SeverityFormula() {
  let model: SeverityModel;
  let detector: DetectorInfo | null = null;
  try {
    [model, detector] = await Promise.all([api.severityModel(), api.detector()]);
  } catch {
    return null;
  }

  return (
    <section className="glass overflow-hidden">
      <div className="border-b border-white/5 px-5 py-3.5">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_10px_2px_rgba(34,211,238,0.6)]" />
          How severity is calculated
        </h2>
      </div>

      <div className="p-5">
        <code className="block overflow-x-auto rounded-xl bg-black/40 px-4 py-3 font-mono text-[13px] text-cyan-200 ring-1 ring-cyan-400/15">
          {model.formula}
        </code>

        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <p className="text-[10.5px] uppercase tracking-[0.14em] text-[var(--text-2)]">
              Class weights
            </p>
            <ul className="mt-2 space-y-1">
              {Object.entries(model.class_weights).map(([name, weight]) => {
                // Struck through when this checkpoint cannot emit the class —
                // the weight exists in the model but is unreachable in practice.
                const covered = detector ? detector.detects.includes(name) : true;
                return (
                  <li key={name} className="flex items-center justify-between text-xs">
                    <span
                      className={
                        covered
                          ? "capitalize text-[var(--text-1)]"
                          : "capitalize text-[var(--text-2)] line-through decoration-[var(--text-2)]/50"
                      }
                      title={covered ? undefined : "not detected by the loaded model"}
                    >
                      {name.replace("_", " ")}
                    </span>
                    <span className="font-mono tabular-nums text-[var(--text-0)]">
                      {weight.toFixed(1)}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>

          <div>
            <p className="text-[10.5px] uppercase tracking-[0.14em] text-[var(--text-2)]">
              Bands
            </p>
            <ul className="mt-2 space-y-1">
              {Object.entries(model.bands).map(([band, [lo, hi]]) => (
                <li key={band} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 capitalize text-[var(--text-1)]">
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ background: BAND_STROKE[band as SeverityBand] }}
                    />
                    {band}
                  </span>
                  <span className="font-mono tabular-nums text-[var(--text-2)]">
                    {lo.toFixed(3)} – {hi.toFixed(3)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <p className="mt-5 rounded-lg border-l-2 border-amber-400/50 bg-amber-400/[0.06] px-3 py-2 text-xs leading-relaxed text-amber-200/90">
          {model.limitation}
        </p>

        {detector && (
          <p className="mt-3 text-[11px] leading-relaxed text-[var(--text-2)]">
            Model{" "}
            <span className="font-mono text-[var(--text-1)]">
              {detector.weights.split("/").pop()}
            </span>{" "}
            · threshold {detector.confidence_threshold.toFixed(2)}
            {detector.detects.length > 0 ? (
              <>
                {" "}
                · detects{" "}
                <strong className="text-[var(--text-1)]">
                  {detector.detects.length === 1 ? "only " : ""}
                  {detector.detects.join(", ")}
                </strong>
                {detector.detects.length < detector.defect_classes.length && (
                  <>
                    {" "}
                    — the other{" "}
                    {detector.defect_classes.length - detector.detects.length}{" "}
                    classes in the taxonomy are not covered by this model and
                    will not be reported even if present
                  </>
                )}
              </>
            ) : (
              // Not a cosmetic edge case: this is what the Docker image showed
              // when it shipped without inference dependencies.
              <>
                {" "}
                ·{" "}
                <strong className="text-amber-300">
                  no defect classes reachable
                </strong>{" "}
                — the loaded checkpoint emits no label this taxonomy recognises,
                so nothing will be detected
              </>
            )}
          </p>
        )}
      </div>
    </section>
  );
}
