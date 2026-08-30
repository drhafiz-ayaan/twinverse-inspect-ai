import Link from "next/link";
import { notFound } from "next/navigation";
import {
  api,
  BAND_ORDER,
  BAND_STYLES,
  type Detection,
  type SeverityBand,
} from "@/lib/api";
import { SeverityBar } from "@/components/SeverityBar";
import { DetectionImage } from "@/components/DetectionImage";
import { SeverityFormula } from "@/components/SeverityFormula";

export const dynamic = "force-dynamic";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

export default async function InspectionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let inspection, media, detections, summary;
  try {
    [inspection, media, detections, summary] = await Promise.all([
      api.inspection(id),
      api.media(id),
      api.detections(id),
      api.summary(id),
    ]);
  } catch (error) {
    if ((error as Error).message.startsWith("404")) notFound();
    throw error;
  }

  const asset = await api.asset(inspection.asset_id).catch(() => null);

  const byMedia = new Map<string, Detection[]>();
  for (const d of detections) {
    byMedia.set(d.media_file_id, [...(byMedia.get(d.media_file_id) ?? []), d]);
  }

  const worst = [...detections]
    .filter((d) => d.severity_score !== null)
    .sort((a, b) => (b.severity_score ?? 0) - (a.severity_score ?? 0))
    .slice(0, 10);

  const unprocessed = media.filter((m) => !m.processed).length;

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/"
          className="text-xs text-slate-500 transition hover:text-slate-900 dark:hover:text-slate-200"
        >
          ← All inspections
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {inspection.title}
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              {asset?.name ?? "unknown asset"}
              {asset?.location ? ` · ${asset.location}` : ""} ·{" "}
              <span className="capitalize">{inspection.status}</span>
            </p>
          </div>
          <a
            href={api.reportUrl(id)}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            Download PDF report
          </a>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Media analysed"
          value={`${summary.media_processed}/${summary.media_total}`}
          hint={unprocessed > 0 ? `${unprocessed} pending` : undefined}
        />
        <Stat label="Detections" value={String(summary.detection_total)} />
        <Stat
          label="Highest severity"
          value={summary.max_severity_score?.toFixed(5) ?? "—"}
        />
        <Stat
          label="Mean severity"
          value={summary.mean_severity_score?.toFixed(5) ?? "—"}
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-sm font-semibold">Severity distribution</h2>
        <div className="mt-4">
          <SeverityBar counts={summary.by_severity} />
        </div>
      </section>

      {worst.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold">Highest-severity detections</h2>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-xs text-slate-500 dark:border-slate-800">
                  <th className="px-4 py-2.5 font-medium">Class</th>
                  <th className="px-4 py-2.5 font-medium">Source</th>
                  <th className="px-4 py-2.5 text-right font-medium">Conf.</th>
                  <th className="px-4 py-2.5 text-right font-medium">Area</th>
                  <th className="px-4 py-2.5 text-right font-medium">Score</th>
                  <th className="px-4 py-2.5 font-medium">Band</th>
                </tr>
              </thead>
              <tbody>
                {worst.map((d) => {
                  const src = media.find((m) => m.id === d.media_file_id);
                  const band = (d.severity_band ?? "low") as SeverityBand;
                  return (
                    <tr
                      key={d.id}
                      className="border-b border-slate-100 last:border-0 dark:border-slate-800/60"
                    >
                      <td className="px-4 py-2.5 capitalize">
                        {d.defect_class.replace("_", " ")}
                      </td>
                      <td className="max-w-[220px] truncate px-4 py-2.5 text-slate-500">
                        {src?.original_filename ?? "—"}
                        {d.frame_index !== null && ` @${d.frame_index}`}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums">
                        {d.confidence.toFixed(3)}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-slate-500">
                        {d.normalized_area?.toFixed(4)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-medium tabular-nums">
                        {d.severity_score?.toFixed(5)}
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${BAND_STYLES[band].bg} ${BAND_STYLES[band].text}`}
                        >
                          {band}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold">
          Media{" "}
          <span className="font-normal text-slate-500">
            — hover a detection to highlight its box
          </span>
        </h2>
        {media.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">
            No media uploaded to this inspection yet.
          </div>
        ) : (
          <div className="grid gap-5 md:grid-cols-2">
            {media.map((m) => (
              <DetectionImage
                key={m.id}
                media={m}
                detections={byMedia.get(m.id) ?? []}
              />
            ))}
          </div>
        )}
      </section>

      <SeverityFormula />
    </div>
  );
}
