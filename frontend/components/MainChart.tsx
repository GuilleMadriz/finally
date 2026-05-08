"use client";

import { useMemo } from "react";
import { usePriceStore } from "@/lib/priceStore";
import { useSelectionStore } from "@/lib/selectionStore";
import { fmtPrice } from "@/lib/format";

const WIDTH = 800;
const HEIGHT = 320;
const PAD = { top: 16, right: 56, bottom: 24, left: 8 };

interface ChartGeometry {
  path: string;
  area: string;
  up: boolean;
  min: number;
  max: number;
  ticks: number[];
}

const buildGeometry = (
  prices: number[],
): ChartGeometry | null => {
  if (prices.length < 2) return null;
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const innerW = WIDTH - PAD.left - PAD.right;
  const innerH = HEIGHT - PAD.top - PAD.bottom;
  const stepX = innerW / (prices.length - 1);

  const points = prices.map((p, i) => {
    const x = PAD.left + i * stepX;
    const y = PAD.top + (1 - (p - min) / range) * innerH;
    return [x, y] as const;
  });

  const path = points
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");

  const lastX = points[points.length - 1][0];
  const firstX = points[0][0];
  const baseY = PAD.top + innerH;
  const area = `${path} L${lastX.toFixed(2)},${baseY} L${firstX.toFixed(2)},${baseY} Z`;

  const up = prices[prices.length - 1] >= prices[0];
  const ticks = [min, (min + max) / 2, max];

  return { path, area, up, min, max, ticks };
};

export function MainChart() {
  const selected = useSelectionStore((s) => s.selected);
  const tick = usePriceStore((s) => (selected ? s.byTicker[selected] : undefined));

  const geometry = useMemo<ChartGeometry | null>(() => {
    const points = tick?.sparkline ?? [];
    return buildGeometry(points.map((p) => p.price));
  }, [tick?.sparkline]);

  const stroke = geometry?.up ? "var(--color-up)" : "var(--color-down)";

  return (
    <section
      data-testid="main-chart"
      className="panel flex h-full flex-col overflow-hidden"
    >
      <header className="flex items-baseline justify-between border-b border-border-muted px-4 py-2.5">
        <div className="flex items-baseline gap-3">
          <h2 className="font-mono-tabular text-base font-semibold tracking-wide text-fg-primary">
            {selected ?? "—"}
          </h2>
          <span className="text-xs uppercase tracking-[0.18em] text-fg-dim">
            live · since open
          </span>
        </div>
        <div className="flex items-baseline gap-4">
          <span className="font-mono-tabular text-2xl text-fg-primary">
            {fmtPrice(tick?.price ?? null)}
          </span>
          <span
            className={`font-mono-tabular text-sm ${
              (tick?.change_percent ?? 0) >= 0 ? "text-up" : "text-down"
            }`}
          >
            {tick
              ? `${tick.change_percent >= 0 ? "+" : ""}${tick.change_percent.toFixed(2)}%`
              : "—"}
          </span>
        </div>
      </header>

      <div className="relative flex-1">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          className="h-full w-full"
          role="img"
          aria-label={selected ? `${selected} price chart` : "price chart"}
        >
          <defs>
            <linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
              <stop offset="100%" stopColor={stroke} stopOpacity="0" />
            </linearGradient>
          </defs>

          {geometry?.ticks.map((t, i) => {
            const innerH = HEIGHT - PAD.top - PAD.bottom;
            const y = PAD.top + (1 - (t - geometry.min) / (geometry.max - geometry.min || 1)) * innerH;
            return (
              <g key={i}>
                <line
                  x1={PAD.left}
                  x2={WIDTH - PAD.right}
                  y1={y}
                  y2={y}
                  stroke="var(--color-border-muted)"
                  strokeDasharray="2 4"
                  strokeWidth={0.5}
                />
                <text
                  x={WIDTH - PAD.right + 6}
                  y={y + 3}
                  className="font-mono-tabular"
                  fontSize={10}
                  fill="var(--color-fg-dim)"
                >
                  {fmtPrice(t)}
                </text>
              </g>
            );
          })}

          {geometry && (
            <>
              <path d={geometry.area} fill="url(#chart-fill)" />
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
            {selected
              ? "Waiting for price data…"
              : "Select a ticker from the watchlist."}
          </div>
        )}
      </div>
    </section>
  );
}
