"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error ?? "login failed");
        return;
      }
      router.push("/");
      router.refresh();
    } catch {
      setError("could not reach the dashboard server");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm py-16">
      <div className="glass rise p-7">
      <p className="text-[11px] uppercase tracking-[0.22em] text-cyan-300/80">
        Secure access
      </p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">
        Sign in to <span className="text-gradient">Inspect AI</span>
      </h1>

      <form onSubmit={submit} className="mt-7 space-y-4">
        <div>
          <label
            htmlFor="email"
            className="block text-[10.5px] uppercase tracking-[0.14em] text-[var(--text-2)]"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-[var(--line)] bg-black/30 px-3.5 py-2.5 text-sm outline-none transition focus:border-cyan-400/60 focus:ring-2 focus:ring-cyan-400/20"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-[10.5px] uppercase tracking-[0.14em] text-[var(--text-2)]"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-[var(--line)] bg-black/30 px-3.5 py-2.5 text-sm outline-none transition focus:border-cyan-400/60 focus:ring-2 focus:ring-cyan-400/20"
          />
        </div>

        {error && (
          <p className="rounded-xl border-l-2 border-rose-400 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-500 px-4 py-3 text-sm font-semibold text-white shadow-[0_10px_30px_-10px_rgba(34,211,238,0.8)] transition hover:brightness-110 disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-[11px] leading-relaxed text-[var(--text-2)]">
        Accounts are created by an administrator. The session token is stored in
        an <span className="text-[var(--text-1)]">httpOnly</span> cookie, so page
        scripts cannot read it.
      </p>
      </div>
    </div>
  );
}
