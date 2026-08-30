import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { BAND_STROKE, type Detection, type SeverityBand } from "@/lib/api";
import { api, UnauthorizedError } from "@/lib/server-api";
import { SeverityBar } from "@/components/SeverityBar";
import { DetectionImage } from "@/components/DetectionImage";
import { SeverityFormula } from "@/components/SeverityFormula";
import { AnimatedCounter } from "@/components/ui/Motion";
import { TwinViewerClient } from "@/components/TwinViewerClient";
import { API_BASE } from "@/lib/api";

export const dynamic = "force-dynamic";

function Stat({
  label,
  value,
  decimals = 0,
  suffix = "",
  hint,
  accent = "var(--accent)",
  delay = "d1",
}: {
  label: string;
  value: number | null;
  decimals?: number;
  suffix?: string;
  hint?: string;
  accent?: string;
  delay?: string;
}) {
  return (
    <div className={`glass glass-hover rise ${delay} px-5 py-4`}>
      <p className="text-[10.5px] uppercase tracking-[0.14em] text-[var(--text-2)]">
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold tabular-nums" style={{ color: accent }}>
        {value === null ? (
          "—"
        ) : (
          <AnimatedCounter value={value} decimals={decimals} suffix={suffix} />
        )}
      </p>
      {hint && <p className="mt-0.5 text-[11px] text-[var(--text-2)]">{hint}</p>}
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
    if (error instanceof UnauthorizedError) redirect("/login");
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
    <div className="space-y-9">
      <div>
        <Link
          href="/"
          className="text-xs text-[var(--text-2)] transition hover:text-cyan-300"
        >
          ← All inspections
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">
              {inspection.title}
            </h1>
            <p className="mt-1 text-sm text-[var(--text-1)]">
              {asset?.name ?? "unknown asset"}
              {asset?.location ? ` · ${asset.location}` : ""} ·{" "}
              <span className="capitalize">{inspection.status}</span>
            </p>
          </div>
          <a
            href={`${API_BASE}/inspections/${id}/report.pdf`}
            className="group relative overflow-hidden rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-500 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_24px_-8px_rgba(34,211,238,0.7)] transition hover:brightness-110"
          >
            Download PDF report
          </a>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Media analysed"
          value={summary.media_processed}
          suffix={`/${summary.media_total}`}
          hint={unprocessed > 0 ? `${unprocessed} pending` : "all processed"}
          delay="d1"
        />
        <Stat
          label="Detections"
          value={summary.detection_total}
          accent="#a78bfa"
          delay="d2"
        />
        <Stat
          label="Highest severity"
          value={summary.max_severity_score}
          decimals={5}
          accent="#f43f5e"
          delay="d3"
        />
        <Stat
          label="Mean severity"
          value={summary.mean_severity_score}
          decimals={5}
          accent="#f59e0b"
          delay="d4"
        />
      </div>

      <section className="glass rise d4 p-5">
        <h2 className="text-sm font-semibold">Severity distribution</h2>
        <div className="mt-4">
          <SeverityBar counts={summary.by_severity} />
        </div>
      </section>

      {worst.length > 0 && (
        <section className="rise d5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.14em] text-[var(--text-1)]">Highest-severity detections</h2>
          <div className="glass overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-white/5 text-left text-[10.5px] uppercase tracking-wider text-[var(--text-2)]">
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
                      className="border-b border-white/[0.04] transition hover:bg-white/[0.03] last:border-0"
                    >
                      <td className="px-4 py-2.5 capitalize">
                        {d.defect_class.replace("_", " ")}
                      </td>
                      <td className="max-w-[220px] truncate px-4 py-2.5 text-[var(--text-2)]">
                        {src?.original_filename ?? "—"}
                        {d.frame_index !== null && ` @${d.frame_index}`}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums">
                        {d.confidence.toFixed(3)}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-[var(--text-2)]">
                        {d.normalized_area?.toFixed(4)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-medium tabular-nums">
                        {d.severity_score?.toFixed(5)}
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className="rounded-full px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide"
                          style={{ color: BAND_STROKE[band], background: `${BAND_STROKE[band]}1a`, boxShadow: `inset 0 0 0 1px ${BAND_STROKE[band]}44` }}
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
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.14em] text-[var(--text-1)]">
          Digital Twin v1{" "}
          <span className="font-normal normal-case text-[var(--text-2)]">
            — marker viewer, not a reconstruction
          </span>
        </h2>
        <TwinViewerClient media={media} detections={detections} />
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-[0.14em] text-[var(--text-1)]">
          Media{" "}
          <span className="font-normal normal-case text-[var(--text-2)]">
            — hover a detection to highlight its box
          </span>
        </h2>
        {media.length === 0 ? (
          <div className="glass p-10 text-center text-sm text-[var(--text-2)]">
            No media uploaded to this inspection yet.
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
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
