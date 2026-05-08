"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { fmtPrice } from "@/lib/format";
import type { HistoryPoint } from "@/lib/types";

const WIDTH = 800;
const HEIGHT = 240;
const PAD = { top: 12, right: 56, bottom: 22, left: 8 };
const REFRESH_MS = 30_000;

function buildPath(points: HistoryPoint[]) {
  if (points.length < 2) return null;
  const values = points.map((p) => p.total_value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const innerW = WIDTH - PAD.left - PAD.right;
  const innerH = HEIGHT - PAD.top - PAD.bottom;
  const stepX = innerW / (points.length - 1);

  const coords = values.map((v, i) => {
    const x = PAD.left + i * stepX;
    const y = PAD.top + (1 - (v - min) / range) * innerH;
    return [x, y] as const;
  });
  const path = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");
  const lastX = coords[coords.length - 1][0];
  const firstX = coords[0][0];
  const baseY = PAD.top + innerH;
  const area = `${path} L${lastX.toFixed(2)},${baseY} L${firstX.toFixed(2)},${baseY} Z`;
  const up = values[values.length - 1] >= values[0];
  return { path, area, up, min, max };
}

export function PnlChart() {
  const [points, setPoints] = useState<HistoryPoint[]>([]);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const data = await api.getPortfolioHistory();
        if (!cancelled) setPoints(data.points);
      } catch {
        // network blip; next tick will retry.
      }
    };
    tick();
    const id = setInterval(tick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const geometry = useMemo(() => buildPath(points), [points]);
  const stroke = geometry?.up ? "var(--color-up)" : "var(--color-down)";
  const last = points[points.length - 1]?.total_value;
  const first = points[0]?.total_value;
  const change =
    first != null && last != null && first !== 0
      ? ((last - first) / first) * 100
      : null;

  return (
    <section
      className="panel flex h-full flex-col overflow-hidden"
      data-testid="pnl-chart"
    >
      <header className="flex items-baseline justify-between border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-fg-muted">
          Total Value
        </h2>
        <div className="flex items-baseline gap-3">
          <span className="font-mono-tabular text-sm text-fg-primary">
            {fmtPrice(last ?? null)}
          </span>
          {change != null && (
            <span
              className={`font-mono-tabular text-xs ${
                change >= 0 ? "text-up" : "text-down"
              }`}
            >
              {change >= 0 ? "+" : ""}
              {change.toFixed(2)}%
            </span>
          )}
        </div>
      </header>

      <div className="relative flex-1">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="h-full w-full"
          role="img"
          aria-label="portfolio value chart"
        >
          <defs>
            <linearGradient id="pnl-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
              <stop offset="100%" stopColor={stroke} stopOpacity="0" />
            </linearGradient>
          </defs>
          {geometry && (
            <>
              <path d={geometry.area} fill="url(#pnl-fill)" />
              <path
                d={geometry.path}
                fill="none"
                stroke={stroke}
                strokeWidth={1.5}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </>
          )}
        </svg>
        {!geometry && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-xs text-fg-dim">
            {points.length === 1 ? "Waiting for the next snapshot…" : "No history yet."}
          </div>
        )}
      </div>
    </section>
  );
}
