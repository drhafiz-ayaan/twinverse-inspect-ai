import { NextResponse } from "next/server";
import { API_INTERNAL_BASE } from "@/lib/server-config";
import { authHeader, UNAUTHENTICATED } from "@/lib/proxy";

export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const auth = await authHeader();
  if (!auth) return UNAUTHENTICATED;

  const contentType = request.headers.get("content-type");
  if (!contentType?.startsWith("multipart/form-data")) {
    return NextResponse.json(
      { error: "expected a multipart upload" },
      { status: 400 },
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${API_INTERNAL_BASE}/inspections/${id}/uploads`, {
      method: "POST",
      // Forward the body as a stream so a 500 MB video is never held in
      // memory here. `duplex: "half"` is required by undici whenever the body
      // is a stream; it is absent from the DOM RequestInit type, hence the cast.
      //
      // The original Content-Type is passed through untouched because it
      // carries the multipart boundary — regenerating it would make the body
      // unparseable.
      headers: { ...auth, "Content-Type": contentType },
      body: request.body,
      duplex: "half",
      cache: "no-store",
    } as RequestInit & { duplex: "half" });
  } catch {
    return NextResponse.json(
      { error: "cannot reach the API — is the backend running?" },
      { status: 502 },
    );
  }

  const body = await upstream.json().catch(() => null);
  if (!upstream.ok) {
    const detail = (body as { detail?: unknown } | null)?.detail;
    return NextResponse.json(
      { error: typeof detail === "string" ? detail : "upload failed" },
      { status: upstream.status },
    );
  }
  return NextResponse.json(body, { status: upstream.status });
}
