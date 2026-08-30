"use client";

import { useEffect, useRef, useState } from "react";

/** True once the element has entered the viewport. Fires once, then unobserves. */
export function useInView<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  // Must start false on both server and client. Deriving it from
  // `typeof IntersectionObserver` looks like a sensible fail-open, but that
  // expression is true during SSR and false in the browser, so the two renders
  // disagree and React reports a hydration mismatch. The effect below covers
  // the missing-observer case instead.
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // No observer available: reveal immediately rather than never.
    if (typeof IntersectionObserver === "undefined") {
      const id = window.setTimeout(() => setInView(true), 0);
      return () => window.clearTimeout(id);
    }

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    io.observe(el);

    // Safety net. The observer does not fire while the document is hidden
    // (background tab, headless capture, prerender), and these hooks gate
    // *content* — a counter stuck at its start value shows 0 where the real
    // figure is 8, which is wrong data rather than a missing animation.
    // Reveal regardless after a short grace period.
    const fallback = window.setTimeout(() => {
      setInView(true);
      io.disconnect();
    }, 900);

    return () => {
      window.clearTimeout(fallback);
      io.disconnect();
    };
  }, []);

  return { ref, inView };
}

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
}

interface CounterProps {
  value: number;
  decimals?: number;
  duration?: number;
  className?: string;
  suffix?: string;
}

/**
 * Number that counts up when scrolled into view.
 *
 * Eased with an ease-out cubic so it decelerates into the final value rather
 * than stopping dead. The final value is always rendered exactly, so the
 * displayed figure is never an artefact of the animation.
 */
export function AnimatedCounter({
  value,
  decimals = 0,
  duration = 1100,
  className,
  suffix = "",
}: CounterProps) {
  const { ref, inView } = useInView<HTMLSpanElement>();
  const [shown, setShown] = useState(0);

  useEffect(() => {
    if (!inView) return;

    if (prefersReducedMotion()) {
      const id = window.setTimeout(() => setShown(value), 0);
      return () => window.clearTimeout(id);
    }

    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(value * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
      else setShown(value);
    };
    raf = requestAnimationFrame(tick);

    // requestAnimationFrame is paused entirely while the document is hidden,
    // so the loop above may never run a single frame and the counter would sit
    // at 0 — displaying a wrong number, not merely an unanimated one. A timer
    // still fires when hidden, so it guarantees the true value lands.
    const settle = window.setTimeout(() => setShown(value), duration + 120);

    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(settle);
    };
  }, [inView, value, duration]);

  return (
    <span ref={ref} className={className}>
      {shown.toFixed(decimals)}
      {suffix}
    </span>
  );
}

interface BarProps {
  value: number;
  max?: number;
  color?: string;
  label?: string;
  sublabel?: string;
  delay?: number;
}

/** Progress bar that fills from zero when it enters view. */
export function ProgressBar({
  value,
  max = 100,
  color = "var(--accent)",
  label,
  sublabel,
  delay = 0,
}: BarProps) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;

  return (
    <div ref={ref}>
      {(label || sublabel) && (
        <div className="mb-1.5 flex items-baseline justify-between gap-3">
          {label && (
            <span className="text-xs font-medium text-[var(--text-1)]">
              {label}
            </span>
          )}
          {sublabel && (
            <span className="text-xs tabular-nums text-[var(--text-2)]">
              {sublabel}
            </span>
          )}
        </div>
      )}
      <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--bg-2)]">
        <div
          className="relative h-full overflow-hidden rounded-full sheen"
          style={{
            width: inView ? `${pct}%` : "0%",
            background: `linear-gradient(90deg, ${color}aa, ${color})`,
            boxShadow: `0 0 14px -2px ${color}`,
            transition: `width 1.1s cubic-bezier(0.2,0.7,0.3,1) ${delay}ms`,
          }}
        />
      </div>
    </div>
  );
}
