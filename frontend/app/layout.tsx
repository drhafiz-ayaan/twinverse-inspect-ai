import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { SessionBar } from "@/components/SessionBar";

export const metadata: Metadata = {
  title: "TwinVerse Inspect AI",
  description:
    "AI-powered infrastructure inspection — defect detection, severity assessment and digital twin visualisation",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">
        {/* Ambient layers sit behind everything and never take pointer events. */}
        <div className="aurora" aria-hidden="true" />
        <div className="grid-veil" aria-hidden="true" />

        <header className="sticky top-0 z-40 border-b border-[var(--line-soft)] bg-[rgba(7,11,20,0.72)] backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3.5">
            <Link href="/" className="group flex items-center gap-3">
              <span className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400/20 to-indigo-500/20 ring-1 ring-cyan-400/30">
                <span className="absolute inset-0 rounded-xl bg-cyan-400/10 blur-md transition-opacity group-hover:opacity-100 opacity-0" />
                <svg
                  viewBox="0 0 24 24"
                  className="relative h-5 w-5 text-cyan-300"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3 17h18M5 17V9l7-5 7 5v8M9 17v-4h6v4" />
                </svg>
              </span>
              <span className="leading-tight">
                <span className="block text-[15px] font-semibold tracking-tight">
                  TwinVerse <span className="text-gradient">Inspect AI</span>
                </span>
                <span className="block text-[10.5px] uppercase tracking-[0.16em] text-[var(--text-2)]">
                  Infrastructure Intelligence
                </span>
              </span>
            </Link>

            <SessionBar />
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>

        <footer className="mx-auto max-w-7xl px-6 pb-12 pt-6">
          <div className="hairline mb-4" />
          <p className="text-[11px] leading-relaxed text-[var(--text-2)]">
            <span className="font-medium text-[var(--text-1)]">
              First-pass screening only.
            </span>{" "}
            Detections are automated and unreviewed. Severity is a relative
            ranking, not an engineering measurement — it does not output crack
            width in millimetres. Findings require confirmation by a qualified
            engineer before any maintenance decision.
          </p>
        </footer>
      </body>
    </html>
  );
}
