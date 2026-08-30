import { type SeverityModel, type DetectorInfo } from "@/lib/api";
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
    <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
        How severity is calculated
      </h2>

      <code className="mt-3 block rounded-lg bg-slate-50 px-3 py-2.5 font-mono text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-200">
        {model.formula}
      </code>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium text-slate-500">Class weights</p>
          <ul className="mt-1.5 space-y-0.5">
            {Object.entries(model.class_weights).map(([name, weight]) => (
              <li
                key={name}
                className="flex justify-between text-xs text-slate-700 dark:text-slate-300"
              >
                <span className="capitalize">{name.replace("_", " ")}</span>
                <span className="tabular-nums font-medium">{weight}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-medium text-slate-500">Bands</p>
          <ul className="mt-1.5 space-y-0.5">
            {Object.entries(model.bands).map(([band, [lo, hi]]) => (
              <li
                key={band}
                className="flex justify-between text-xs text-slate-700 dark:text-slate-300"
              >
                <span className="capitalize">{band}</span>
                <span className="tabular-nums">
                  {lo.toFixed(3)} – {hi.toFixed(3)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <p className="mt-4 border-t border-slate-100 pt-3 text-xs leading-relaxed text-slate-500 dark:border-slate-800">
        {model.limitation}
      </p>

      {detector && (
        <p className="mt-2 text-xs text-slate-400">
          Model{" "}
          <span className="font-mono">
            {detector.weights.split("/").pop()}
          </span>{" "}
          · confidence threshold {detector.confidence_threshold.toFixed(2)}
          {detector.detects.length > 0 && (
            <>
              {" "}
              · detects{" "}
              <strong>
                {detector.detects.length === 1 ? "only " : ""}
                {detector.detects.join(", ")}
              </strong>
              {detector.detects.length < detector.defect_classes.length && (
                <>
                  {" "}
                  — the other{" "}
                  {detector.defect_classes.length - detector.detects.length}{" "}
                  defect classes in the taxonomy are not covered by this model
                  and will not be reported even if present
                </>
              )}
            </>
          )}
        </p>
      )}
    </section>
  );
}
