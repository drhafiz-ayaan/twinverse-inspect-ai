import "server-only";

import { cookies } from "next/headers";
import {
  API_BASE,
  type Asset,
  type Detection,
  type DetectionSummary,
  type DetectorInfo,
  type Inspection,
  type MediaFile,
  type SeverityModel,
} from "@/lib/api";

/**
 * Server-side API client.
 *
 * The access token lives in an httpOnly cookie, so it is never readable by
 * page scripts — an XSS bug cannot exfiltrate it. That also means only Server
 * Components can attach it, which is why every data fetch happens on the
 * server and the browser never talks to the API directly.
 */

export const SESSION_COOKIE = "twinverse_session";

/** Thrown when the API rejects our credentials; pages turn this into a redirect. */
export class UnauthorizedError extends Error {
  constructor() {
    super("not authenticated");
    this.name = "UnauthorizedError";
  }
}

async function get<T>(path: string): Promise<T> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (res.status === 401) throw new UnauthorizedError();
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} — GET ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  assets: () => get<Asset[]>("/assets"),
  asset: (id: string) => get<Asset>(`/assets/${id}`),
  inspections: () => get<Inspection[]>("/inspections"),
  inspection: (id: string) => get<Inspection>(`/inspections/${id}`),
  media: (inspectionId: string) =>
    get<MediaFile[]>(`/inspections/${inspectionId}/media`),
  detections: (inspectionId: string) =>
    get<Detection[]>(`/inspections/${inspectionId}/detections`),
  summary: (inspectionId: string) =>
    get<DetectionSummary>(`/inspections/${inspectionId}/detections/summary`),
  severityModel: () => get<SeverityModel>("/severity/model"),
  detector: () => get<DetectorInfo>("/detector"),
  me: () => get<{ email: string; role: string }>("/auth/me"),
};

export async function isAuthenticated(): Promise<boolean> {
  return Boolean((await cookies()).get(SESSION_COOKIE)?.value);
}
