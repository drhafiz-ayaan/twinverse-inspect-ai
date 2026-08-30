import Link from "next/link";
import { api, type Asset, type Inspection } from "@/lib/api";
import { SeverityFormula } from "@/components/SeverityFormula";

export const dynamic = "force-dynamic";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
  processing: "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300",
  completed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  failed: "bg-rose-100 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
};

function ApiDown({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 dark:border-amber-500/30 dark:bg-amber-500/10">
      <h2 className="text-sm font-semibold text-amber-900 dark:text-amber-200">
        Cannot reach the API
      </h2>
      <p className="mt-1 text-sm text-amber-800 dark:text-amber-300">{message}</p>
      <pre className="mt-3 overflow-x-auto rounded bg-amber-100/60 px-3 py-2 text-xs text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
{`cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000`}
      </pre>
    </div>
  );
}

export default async function Home() {
  let assets: Asset[] = [];
  let inspections: Inspection[] = [];
  try {
    [assets, inspections] = await Promise.all([api.assets(), api.inspections()]);
  } catch (error) {
    return <ApiDown message={(error as Error).message} />;
  }

  const assetById = new Map(assets.map((a) => [a.id, a]));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Inspections</h1>
        <p className="mt-1 text-sm text-slate-500">
          {inspections.length} inspection{inspections.length === 1 ? "" : "s"} across{" "}
          {assets.length} asset{assets.length === 1 ? "" : "s"}
        </p>
      </div>

      {inspections.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 p-10 text-center dark:border-slate-700">
          <p className="text-sm font-medium">No inspections yet</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
            Create an asset, open an inspection against it, then upload drone or
            phone imagery. The API docs have runnable examples for each step.
          </p>
        </div>
      ) : (
        <ul className="grid gap-3">
          {inspections.map((inspection) => {
            const asset = assetById.get(inspection.asset_id);
            return (
              <li key={inspection.id}>
                <Link
                  href={`/inspections/${inspection.id}`}
                  className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white px-5 py-4 transition hover:border-slate-300 hover:shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {inspection.title}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-slate-500">
                      {asset?.name ?? "unknown asset"}
                      {asset?.location ? ` · ${asset.location}` : ""}
                      {" · "}
                      {new Date(inspection.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <span className="text-xs tabular-nums text-slate-500">
                      {inspection.media_count ?? 0} file
                      {inspection.media_count === 1 ? "" : "s"}
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
                        STATUS_STYLES[inspection.status] ?? STATUS_STYLES.pending
                      }`}
                    >
                      {inspection.status}
                    </span>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <SeverityFormula />
    </div>
  );
}
