import Link from "next/link";
import { redirect } from "next/navigation";
import { type Asset, type Inspection } from "@/lib/api";
import { api, UnauthorizedError } from "@/lib/server-api";
import { SeverityFormula } from "@/components/SeverityFormula";
import { AnimatedCounter } from "@/components/ui/Motion";

export const dynamic = "force-dynamic";

const STATUS_STYLE: Record<string, string> = {
  pending: "text-slate-300 ring-slate-400/25 bg-slate-400/10",
  processing: "text-cyan-300 ring-cyan-400/30 bg-cyan-400/10",
  completed: "text-emerald-300 ring-emerald-400/30 bg-emerald-400/10",
  failed: "text-rose-300 ring-rose-400/30 bg-rose-400/10",
};

function ApiDown({ message }: { message: string }) {
  return (
    <div className="glass rise p-6">
      <h2 className="text-sm font-semibold text-amber-300">
        Cannot reach the API
      </h2>
      <p className="mt-1.5 text-sm text-[var(--text-1)]">{message}</p>
      <pre className="mt-3 overflow-x-auto rounded-lg bg-black/40 px-3 py-2.5 text-xs text-amber-200 ring-1 ring-amber-400/20">
{`cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000`}
      </pre>
    </div>
  );
}

function Metric({
  label,
  value,
  accent,
  delay,
}: {
  label: string;
  value: number;
  accent: string;
  delay: string;
}) {
  return (
    <div className={`glass glass-hover rise ${delay} px-5 py-4`}>
      <p className="text-[10.5px] uppercase tracking-[0.14em] text-[var(--text-2)]">
        {label}
      </p>
      <p
        className="mt-1 text-3xl font-semibold tabular-nums"
        style={{ color: accent }}
      >
        <AnimatedCounter value={value} />
      </p>
    </div>
  );
}

export default async function Home() {
  let assets: Asset[] = [];
  let inspections: Inspection[] = [];
  try {
    [assets, inspections] = await Promise.all([api.assets(), api.inspections()]);
  } catch (error) {
    // An expired or missing session is a routing concern, not an error page.
    if (error instanceof UnauthorizedError) redirect("/login");
    return <ApiDown message={(error as Error).message} />;
  }

  const assetById = new Map(assets.map((a) => [a.id, a]));
  const mediaTotal = inspections.reduce(
    (sum, i) => sum + (i.media_count ?? 0),
    0,
  );
  const completed = inspections.filter((i) => i.status === "completed").length;

  return (
    <div className="space-y-10">
      {/* hero */}
      <section className="rise">
        <p className="text-[11px] uppercase tracking-[0.22em] text-cyan-300/80">
          Autonomous structural screening
        </p>
        <h1 className="mt-2 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Inspect the <span className="text-gradient">unreachable</span>.
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[var(--text-1)]">
          Drone, CCTV and handheld imagery in — located defects, ranked severity
          and a shareable report out. Engineers spend their time on judgement
          instead of data collection.
        </p>
      </section>

      {/* fleet metrics */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Assets" value={assets.length} accent="var(--accent)" delay="d1" />
        <Metric label="Inspections" value={inspections.length} accent="#a78bfa" delay="d2" />
        <Metric label="Media files" value={mediaTotal} accent="#34d399" delay="d3" />
        <Metric label="Analysed" value={completed} accent="#f59e0b" delay="d4" />
      </section>

      {/* inspections */}
      <section className="rise d3">
        <div className="mb-4 flex items-end justify-between gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--text-1)]">
            Inspections
          </h2>
          <span className="text-xs text-[var(--text-2)]">
            {inspections.length} across {assets.length} asset
            {assets.length === 1 ? "" : "s"}
          </span>
        </div>

        {inspections.length === 0 ? (
          <div className="glass p-12 text-center">
            <p className="text-sm font-medium">No inspections yet</p>
            <p className="mx-auto mt-2 max-w-md text-sm text-[var(--text-2)]">
              Create an asset, open an inspection against it, then upload drone
              or phone imagery. The API docs have runnable examples for each
              step.
            </p>
          </div>
        ) : (
          <ul className="grid gap-3">
            {inspections.map((inspection, index) => {
              const asset = assetById.get(inspection.asset_id);
              return (
                <li
                  key={inspection.id}
                  className="rise"
                  style={{ animationDelay: `${0.24 + index * 0.05}s` }}
                >
                  <Link
                    href={`/inspections/${inspection.id}`}
                    className="glass glass-hover group flex items-center justify-between gap-4 px-5 py-4"
                  >
                    <div className="flex min-w-0 items-center gap-4">
                      <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-400/10 ring-1 ring-cyan-400/25">
                        <svg
                          viewBox="0 0 24 24"
                          className="h-4.5 w-4.5 text-cyan-300"
                          style={{ width: 18, height: 18 }}
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden="true"
                        >
                          <path d="M3 17h18M5 17V9l7-5 7 5v8" />
                        </svg>
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium transition group-hover:text-cyan-200">
                          {inspection.title}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-[var(--text-2)]">
                          {asset?.name ?? "unknown asset"}
                          {asset?.location ? ` · ${asset.location}` : ""} ·{" "}
                          {new Date(inspection.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-3">
                      <span className="hidden text-xs tabular-nums text-[var(--text-2)] sm:inline">
                        {inspection.media_count ?? 0} file
                        {inspection.media_count === 1 ? "" : "s"}
                      </span>
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide ring-1 ${
                          STATUS_STYLE[inspection.status] ?? STATUS_STYLE.pending
                        }`}
                      >
                        {inspection.status}
                      </span>
                      <span className="text-[var(--text-2)] transition group-hover:translate-x-0.5 group-hover:text-cyan-300">
                        →
                      </span>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <div className="rise d5">
        <SeverityFormula />
      </div>
    </div>
  );
}
