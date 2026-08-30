/**
 * Typed client for the TwinVerse Inspect API.
 *
 * Types mirror backend/app/schemas. They are hand-written rather than
 * generated so the drift is visible in review; if the API grows much further,
 * generate them from /openapi.json instead.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type AssetType =
  | "bridge" | "building" | "road" | "dam" | "pipeline" | "tunnel" | "other";
export type InspectionStatus = "pending" | "processing" | "completed" | "failed";
export type DefectClass =
  | "crack" | "corrosion" | "surface_damage" | "missing_component";
export type SeverityBand = "low" | "medium" | "high" | "critical";

export interface Asset {
  id: string;
  name: string;
  asset_type: AssetType;
  location: string | null;
  latitude: number | null;
  longitude: number | null;
  description: string | null;
  created_at: string;
}

export interface Inspection {
  id: string;
  asset_id: string;
  title: string;
  status: InspectionStatus;
  notes: string | null;
  inspected_at: string | null;
  created_at: string;
  media_count?: number;
}

export interface MediaFile {
  id: string;
  inspection_id: string;
  storage_key: string;
  original_filename: string;
  content_type: string;
  media_type: "image" | "video";
  size_bytes: number;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  frame_count: number | null;
  fps: number | null;
  processed: boolean;
  created_at: string;
  download_url: string;
}

export interface Detection {
  id: string;
  media_file_id: string;
  defect_class: DefectClass;
  confidence: number;
  bbox_x: number;
  bbox_y: number;
  bbox_width: number;
  bbox_height: number;
  frame_index: number | null;
  normalized_area: number | null;
  class_weight: number | null;
  severity_score: number | null;
  severity_band: SeverityBand | null;
  created_at: string;
}

export interface DetectionSummary {
  inspection_id: string;
  media_total: number;
  media_processed: number;
  detection_total: number;
  by_class: { defect_class: DefectClass; count: number }[];
  by_severity: { severity_band: SeverityBand; count: number }[];
  max_severity_score: number | null;
  mean_severity_score: number | null;
}

export interface SeverityModel {
  formula: string;
  class_weights: Record<string, number>;
  bands: Record<SeverityBand, [number, number]>;
  limitation: string;
}

export interface DetectorInfo {
  weights: string;
  confidence_threshold: number;
  video_frame_stride: number;
  video_max_frames: number;
  /** Full taxonomy the database and severity model support. */
  defect_classes: string[];
  /** Raw labels the loaded checkpoint emits. */
  model_classes: string[];
  /** Taxonomy subset this checkpoint can actually produce. */
  detects: string[];
}

/** Fetch JSON, never cached — inspection state changes as analysis runs. */
async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
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
  reportUrl: (inspectionId: string) =>
    `${API_BASE}/inspections/${inspectionId}/report.pdf`,
};

export const BAND_STYLES: Record<SeverityBand, { bg: string; text: string; dot: string }> = {
  low:      { bg: "bg-emerald-500/10", text: "text-emerald-700 dark:text-emerald-300", dot: "bg-emerald-500" },
  medium:   { bg: "bg-amber-500/10",   text: "text-amber-700 dark:text-amber-300",     dot: "bg-amber-500" },
  high:     { bg: "bg-orange-500/10",  text: "text-orange-700 dark:text-orange-300",   dot: "bg-orange-500" },
  critical: { bg: "bg-rose-500/10",    text: "text-rose-700 dark:text-rose-300",       dot: "bg-rose-500" },
};

export const BAND_ORDER: SeverityBand[] = ["critical", "high", "medium", "low"];

/** Stroke colours for box overlays — must read against photographic backgrounds. */
export const BAND_STROKE: Record<SeverityBand, string> = {
  low: "#10b981",
  medium: "#f59e0b",
  high: "#f97316",
  critical: "#f43f5e",
};
