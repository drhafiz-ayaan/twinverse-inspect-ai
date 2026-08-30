"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function SignOutButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  return (
    <button
      type="button"
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        // DELETE clears the httpOnly cookie server-side; page scripts cannot
        // remove it themselves, which is the point of it being httpOnly.
        await fetch("/api/session", { method: "DELETE" });
        router.push("/login");
        router.refresh();
      }}
      className="rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-2)] transition hover:bg-white/5 hover:text-[var(--text-0)] disabled:opacity-50"
    >
      {busy ? "…" : "Sign out"}
    </button>
  );
}
