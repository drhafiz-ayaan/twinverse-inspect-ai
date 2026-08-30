import { NextResponse } from "next/server";
import { API_BASE } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/server-api";

/**
 * Session endpoint.
 *
 * The browser posts credentials here rather than to the API directly, so the
 * access token can be stored in an **httpOnly** cookie. A token held in
 * localStorage is readable by any script on the page, which turns a single XSS
 * bug into full account compromise; an httpOnly cookie is not.
 *
 * The trade-off is CSRF exposure, addressed with SameSite=lax — enough here
 * because every state-changing API call is a cross-origin request from the
 * server, not a form post from the browser.
 */

export async function POST(request: Request) {
  let email: string;
  let password: string;
  try {
    ({ email, password } = await request.json());
  } catch {
    return NextResponse.json({ error: "malformed request" }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "cannot reach the API — is the backend running?" },
      { status: 502 },
    );
  }

  if (!upstream.ok) {
    // Pass the API's own wording through unchanged: it deliberately does not
    // distinguish a wrong password from an unknown address.
    const body = await upstream.json().catch(() => ({}));
    return NextResponse.json(
      { error: body.detail ?? "login failed" },
      { status: upstream.status },
    );
  }

  const { access_token, expires_in, role } = await upstream.json();
  const response = NextResponse.json({ ok: true, role });
  response.cookies.set(SESSION_COOKIE, access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: expires_in,
  });
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, "", { path: "/", maxAge: 0 });
  return response;
}
