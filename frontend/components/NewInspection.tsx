"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Asset, AssetType } from "@/lib/api";

/**
 * The whole intake flow in one panel: asset → inspection → upload → detect.
 *
 * Previously imagery could only enter through the API, so a demo meant six
 * curl commands with ids copied between them. Each step is still a separate
 * API call — this just sequences them and shows where it got to, because a
 * multi-second upload with no feedback reads as a broken button.
 */

const ASSET_TYPES: AssetType[] = [
  "bridge", "building", "road", "dam", "pipeline", "tunnel", "other",
];

/** Mirrors the API's own limit; rejecting here saves a wasted round trip. */
const MAX_FILES = 50;

type Phase =
  | { step: "idle" }
  | { step: "working"; label: string; percent: number }
  | { step: "error"; message: string };

const field =
  "mt-1.5 w-full rounded-xl border border-[var(--line)] bg-black/30 px-3.5 py-2.5 " +
  "text-sm outline-none transition focus:border-cyan-400/60 focus:ring-2 focus:ring-cyan-400/20";
const label =
  "block text-[10.5px] uppercase tracking-[0.14em] text-[var(--text-2)]";

export function NewInspection({ assets }: { assets: Asset[] }) {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);

  const [open, setOpen] = useState(false);
  const [phase, setPhase] = useState<Phase>({ step: "idle" });

  // "new" means create an asset as part of this submission.
  const [assetId, setAssetId] = useState<string>(assets[0]?.id ?? "new");
  const [assetName, setAssetName] = useState("");
  const [assetType, setAssetType] = useState<AssetType>("bridge");
  const [location, setLocation] = useState("");
  const [title, setTitle] = useState("");
  const [files, setFiles] = useState<File[]>([]);

  const busy = phase.step === "working";
  const creatingAsset = assetId === "new";

  function reset() {
    setPhase({ step: "idle" });
    setFiles([]);
    setTitle("");
    setAssetName("");
    setLocation("");
    if (fileInput.current) fileInput.current.value = "";
  }

  /** Parse a proxy-route error body without letting a non-JSON reply throw. */
  async function failure(res: Response, fallback: string): Promise<string> {
    const body = await res.json().catch(() => null);
    return body?.error ?? fallback;
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (files.length === 0) {
      setPhase({ step: "error", message: "choose at least one image or video" });
      return;
    }
    if (files.length > MAX_FILES) {
      setPhase({
        step: "error",
        message: `${files.length} files selected; the API accepts ${MAX_FILES} per upload`,
      });
      return;
    }

    try {
      // 1. Asset — reuse the selected one, or create it now.
      let targetAsset = assetId;
      if (creatingAsset) {
        setPhase({ step: "working", label: "Creating the asset", percent: 10 });
        const res = await fetch("/api/assets", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: assetName.trim(),
            asset_type: assetType,
            location: location.trim() || null,
          }),
        });
        if (!res.ok) {
          setPhase({ step: "error", message: await failure(res, "could not create the asset") });
          return;
        }
        targetAsset = (await res.json()).id;
      }

      // 2. Inspection.
      setPhase({ step: "working", label: "Opening the inspection", percent: 25 });
      const inspectionRes = await fetch("/api/inspections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ asset_id: targetAsset, title: title.trim() }),
      });
      if (!inspectionRes.ok) {
        setPhase({
          step: "error",
          message: await failure(inspectionRes, "could not open the inspection"),
        });
        return;
      }
      const inspectionId: string = (await inspectionRes.json()).id;

      // 3. Upload. One multipart request; the API reports each file's outcome
      //    separately, so a single unreadable frame does not sink the batch.
      setPhase({
        step: "working",
        label: `Uploading ${files.length} file${files.length === 1 ? "" : "s"}`,
        percent: 45,
      });
      const form = new FormData();
      for (const file of files) form.append("files", file);
      const uploadRes = await fetch(`/api/inspections/${inspectionId}/uploads`, {
        method: "POST",
        body: form,
      });
      if (!uploadRes.ok) {
        setPhase({ step: "error", message: await failure(uploadRes, "upload failed") });
        return;
      }
      const upload = await uploadRes.json();
      if (upload.accepted_count === 0) {
        const why = upload.results?.find((r: { error?: string }) => r.error)?.error;
        setPhase({
          step: "error",
          message: why ? `every file was rejected — ${why}` : "every file was rejected",
        });
        return;
      }

      // 4. Detection. Returns as soon as the work is queued.
      setPhase({ step: "working", label: "Running detection", percent: 65 });
      const detectRes = await fetch(`/api/inspections/${inspectionId}/detect`, {
        method: "POST",
      });
      if (!detectRes.ok) {
        setPhase({ step: "error", message: await failure(detectRes, "could not start detection") });
        return;
      }

      // 5. Poll until the status settles. Roughly a second per image on CPU,
      //    so the ceiling is generous; it reports rather than hanging silently.
      const deadline = Date.now() + 5 * 60_000;
      let status = "processing";
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 1500));
        const poll = await fetch(`/api/inspections/${inspectionId}/status`);
        if (!poll.ok) break;
        status = (await poll.json()).status;
        if (status === "completed" || status === "failed") break;
        setPhase((p) =>
          p.step === "working"
            ? { ...p, label: "Analysing imagery", percent: Math.min(94, p.percent + 3) }
            : p,
        );
      }

      if (status === "failed") {
        setPhase({ step: "error", message: "detection failed — check the API logs" });
        return;
      }

      setPhase({ step: "working", label: "Done", percent: 100 });
      router.push(`/inspections/${inspectionId}`);
      router.refresh();
    } catch {
      setPhase({ step: "error", message: "could not reach the dashboard server" });
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group relative overflow-hidden rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-500 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_24px_-8px_rgba(34,211,238,0.7)] transition hover:brightness-110"
      >
        + New inspection
      </button>
    );
  }

  return (
    <div className="glass rise w-full p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-cyan-300/80">
            New inspection
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">
            Upload imagery and analyse it
          </h2>
        </div>
        <button
          type="button"
          onClick={() => { setOpen(false); reset(); }}
          disabled={busy}
          className="text-xs text-[var(--text-2)] transition hover:text-[var(--text-1)] disabled:opacity-40"
        >
          Cancel
        </button>
      </div>

      <form onSubmit={submit} className="mt-6 space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="asset" className={label}>Asset</label>
            <select
              id="asset"
              value={assetId}
              onChange={(e) => setAssetId(e.target.value)}
              disabled={busy}
              className={field}
            >
              {assets.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
              <option value="new">+ Create a new asset</option>
            </select>
          </div>

          <div>
            <label htmlFor="title" className={label}>Inspection title</label>
            <input
              id="title"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="North span deck survey"
              disabled={busy}
              className={field}
            />
          </div>
        </div>

        {creatingAsset && (
          <div className="grid gap-4 rounded-xl border border-[var(--line)] bg-black/20 p-4 sm:grid-cols-3">
            <div>
              <label htmlFor="asset-name" className={label}>Asset name</label>
              <input
                id="asset-name"
                required
                value={assetName}
                onChange={(e) => setAssetName(e.target.value)}
                placeholder="Riverside Viaduct"
                disabled={busy}
                className={field}
              />
            </div>
            <div>
              <label htmlFor="asset-type" className={label}>Type</label>
              <select
                id="asset-type"
                value={assetType}
                onChange={(e) => setAssetType(e.target.value as AssetType)}
                disabled={busy}
                className={`${field} capitalize`}
              >
                {ASSET_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="asset-location" className={label}>Location</label>
              <input
                id="asset-location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Sector 7, North Span"
                disabled={busy}
                className={field}
              />
            </div>
          </div>
        )}

        <div>
          <label htmlFor="files" className={label}>Imagery</label>
          <input
            id="files"
            ref={fileInput}
            type="file"
            multiple
            accept="image/*,video/*"
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            disabled={busy}
            className="mt-1.5 w-full cursor-pointer rounded-xl border border-dashed border-[var(--line)] bg-black/20 px-3.5 py-3 text-sm text-[var(--text-1)] outline-none transition file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-cyan-400/15 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-cyan-200 hover:border-cyan-400/40"
          />
          <p className="mt-1.5 text-[11px] text-[var(--text-2)]">
            {files.length > 0
              ? `${files.length} file${files.length === 1 ? "" : "s"} selected`
              : `Images or video, up to ${MAX_FILES} files. The model detects cracks in concrete only.`}
          </p>
        </div>

        {phase.step === "error" && (
          <p className="rounded-xl border-l-2 border-rose-400 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
            {phase.message}
          </p>
        )}

        {busy && (
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-1)]">{phase.label}…</span>
              <span className="tabular-nums text-[var(--text-2)]">{phase.percent}%</span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-indigo-400 transition-[width] duration-500"
                style={{ width: `${phase.percent}%` }}
              />
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-500 px-4 py-3 text-sm font-semibold text-white shadow-[0_10px_30px_-10px_rgba(34,211,238,0.8)] transition hover:brightness-110 disabled:opacity-50"
        >
          {busy ? "Working…" : "Upload and analyse"}
        </button>
      </form>
    </div>
  );
}
