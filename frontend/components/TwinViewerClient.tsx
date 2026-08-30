"use client";

import nextDynamic from "next/dynamic";
import type { Detection, MediaFile } from "@/lib/api";

/**
 * Client-side boundary for the 3D viewer.
 *
 * Three.js needs `window` and a WebGL context, so the viewer must not render
 * during SSR. `next/dynamic` with `ssr: false` is only permitted inside a
 * Client Component, hence this wrapper — the inspection page is an async
 * Server Component and cannot call it directly.
 */
const TwinViewer = nextDynamic(
  () => import("./TwinViewer").then((m) => m.TwinViewer),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[460px] items-center justify-center rounded-xl border border-slate-200 bg-white text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900">
        Loading 3D viewer…
      </div>
    ),
  },
);

export function TwinViewerClient(props: {
  media: MediaFile[];
  detections: Detection[];
}) {
  return <TwinViewer {...props} />;
}
