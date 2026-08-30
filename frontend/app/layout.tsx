import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "TwinVerse Inspect AI",
  description:
    "AI-powered infrastructure inspection — defect detection and severity assessment",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
        <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="group flex items-baseline gap-2.5">
              <span className="text-base font-semibold tracking-tight">
                TwinVerse <span className="text-sky-600 dark:text-sky-400">Inspect AI</span>
              </span>
              <span className="hidden text-xs text-slate-500 sm:inline">
                Infrastructure Intelligence
              </span>
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-slate-500 transition hover:text-slate-900 dark:hover:text-slate-200"
            >
              API docs ↗
            </a>
          </div>
        </header>

        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>

        <footer className="mx-auto max-w-6xl px-6 pb-10 pt-4">
          <p className="text-xs leading-relaxed text-slate-400">
            First-pass screening only. Detections are automated and unreviewed;
            severity is a relative ranking, not an engineering measurement.
            Findings require confirmation by a qualified engineer.
          </p>
        </footer>
      </body>
    </html>
  );
}
