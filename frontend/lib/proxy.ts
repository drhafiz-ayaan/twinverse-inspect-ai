import "server-only";

import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { API_BASE } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/server-api";

/**
 * Shared plumbing for the route handlers the browser calls.
 *
 * The access token is in an httpOnly cookie, so page scripts cannot read it and
 * therefore cannot call the API directly. Every browser-initiated write goes
 * through a handler here, which attaches the token server-side. Same reason the
 * PDF download is proxied rather than linked.
 */

/** Attach the caller's own token; returns null when they have no session. */
export async function authHeader(): Promise<Record<string, string> | null> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  return token ? { Authorization: `Bearer ${token}` } : null;
}

export const UNAUTHENTICATED = NextResponse.json(
  { error: "not signed in" },
  { status: 401 },
);

/**
 * Forward a request to the API and mirror its response.
 *
 * The API's own error wording is passed through unchanged — it is written for
 * users, and rephrasing it here would mean two places to keep consistent.
 */
export async function forward(
  path: string,
  init: RequestInit,
): Promise<NextResponse> {
  const auth = await authHeader();
  if (!auth) return UNAUTHENTICATED;

  let upstream: Response;
  try {
    upstream = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...auth, ...(init.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "cannot reach the API — is the backend running?" },
      { status: 502 },
    );
  }

  // 204 has no body, and calling .json() on one throws.
  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const body = await upstream.json().catch(() => null);
  if (!upstream.ok) {
    return NextResponse.json(
      { error: describe(body) ?? `request failed (${upstream.status})` },
      { status: upstream.status },
    );
  }
  return NextResponse.json(body, { status: upstream.status });
}

/**
 * Turn FastAPI's error body into one line.
 *
 * A 422 arrives as `detail: [{loc, msg, ...}]` rather than a string, which
 * renders as "[object Object]" if passed straight to the UI.
 */
function describe(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const loc = Array.isArray(d?.loc) ? d.loc.slice(1).join(".") : "";
        return loc ? `${loc}: ${d.msg}` : d.msg;
      })
      .filter(Boolean)
      .join("; ");
  }
  return null;
}
