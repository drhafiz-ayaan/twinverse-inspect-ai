import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_BASE } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/server-api";

/**
 * PDF report download.
 *
 * The report button cannot link straight at the API. The access token lives in
 * an httpOnly cookie and the API authenticates with an `Authorization` header,
 * which a plain browser navigation has no way to attach — the API answered
 * every such request with 401 and the download silently failed.
 *
 * So the request is proxied: this handler reads the cookie server-side, calls
 * the API the same way every other fetch does, and streams the bytes back. It
 * also keeps the browser from ever talking to the API directly, which is the
 * rule the rest of the app already follows.
 */

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const token = (await cookies()).get(SESSION_COOKIE)?.value;

  if (!token) {
    // Send them to sign in rather than downloading an error page.
    return NextResponse.redirect(new URL("/login", _request.url));
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${API_BASE}/inspections/${id}/report.pdf`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "cannot reach the API — is the backend running?" },
      { status: 502 },
    );
  }

  if (upstream.status === 401) {
    return NextResponse.redirect(new URL("/login", _request.url));
  }
  if (!upstream.ok) {
    return NextResponse.json(
      { error: `report generation failed (${upstream.status})` },
      { status: upstream.status },
    );
  }

  // Stream rather than buffer: reports grow with the number of detections and
  // there is no reason to hold one in memory.
  return new NextResponse(upstream.body, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="inspection-${id}.pdf"`,
      "Cache-Control": "no-store",
    },
  });
}
