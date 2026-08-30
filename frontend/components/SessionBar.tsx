import Link from "next/link";
import { api } from "@/lib/server-api";
import { SignOutButton } from "@/components/SignOutButton";

const ROLE_STYLE: Record<string, string> = {
  admin: "text-rose-300 ring-rose-400/30 bg-rose-400/10",
  inspector: "text-cyan-300 ring-cyan-400/30 bg-cyan-400/10",
  viewer: "text-slate-300 ring-slate-400/25 bg-slate-400/10",
};

/**
 * Signed-in identity and role, or a sign-in link.
 *
 * Renders nothing but the link when /auth/me fails: the header must not be
 * able to break a page, and an expired session is handled by the page's own
 * redirect rather than here.
 */
export async function SessionBar() {
  let me: { email: string; role: string } | null = null;
  try {
    me = await api.me();
  } catch {
    me = null;
  }

  if (!me) {
    return (
      <Link
        href="/login"
        className="rounded-lg px-3 py-1.5 text-xs font-medium text-[var(--text-1)] ring-1 ring-[var(--line)] transition hover:text-white hover:ring-cyan-400/40"
      >
        Sign in
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-2.5">
      <a
        href="http://localhost:8000/docs"
        target="_blank"
        rel="noreferrer"
        className="hidden text-xs text-[var(--text-2)] transition hover:text-[var(--text-0)] sm:inline"
      >
        API docs ↗
      </a>
      <span
        className={`rounded-full px-2.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide ring-1 ${
          ROLE_STYLE[me.role] ?? ROLE_STYLE.viewer
        }`}
      >
        {me.role}
      </span>
      <span className="hidden text-xs text-[var(--text-1)] md:inline">
        {me.email}
      </span>
      <SignOutButton />
    </div>
  );
}
