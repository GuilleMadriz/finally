"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePortfolioStore } from "@/lib/portfolioStore";
import { usePriceStore } from "@/lib/priceStore";
import { useSelectionStore } from "@/lib/selectionStore";
import { squarify, type TreemapTile } from "@/lib/treemap";
import { fmtPrice } from "@/lib/format";
import type { Position } from "@/lib/types";

interface Tile {
  ticker: string;
  weight: number; // 0-1
  pnlPct: number; // already ×100
  marketValue: number;
}

const colorFor = (pnlPct: number) => {
  // Map pnl% (-10..+10) to a green/red intensity stop.
  const clamped = Math.max(-10, Math.min(10, pnlPct));
  const intensity = Math.abs(clamped) / 10;
  const alpha = 0.18 + intensity * 0.55;
  const base = pnlPct >= 0 ? "var(--color-up)" : "var(--color-down)";
  return `color-mix(in oklab, ${base} ${(alpha * 100).toFixed(0)}%, var(--color-bg-panel-2))`;
};

const buildTiles = (
  positions: Position[],
  pricesByTicker: Record<string, number | undefined>,
  cash: number,
): { items: Tile[]; total: number } => {
  const enriched = positions.map((p) => {
    const live = pricesByTicker[p.ticker] ?? p.current_price;
    const value = p.quantity * live;
    const pnlPct =
      p.avg_cost > 0 ? ((live - p.avg_cost) / p.avg_cost) * 100 : 0;
    return { ticker: p.ticker, value, pnlPct };
  });
  const total = enriched.reduce((s, e) => s + e.value, 0) + Math.max(0, cash);
  if (total <= 0) return { items: [], total: 0 };

  const items: Tile[] = enriched
    .filter((e) => e.value > 0)
    .map((e) => ({
      ticker: e.ticker,
      weight: e.value / total,
      pnlPct: e.pnlPct,
      marketValue: e.value,
    }));

  if (cash > 0) {
    items.push({
      ticker: "CASH",
      weight: cash / total,
      pnlPct: 0,
      marketValue: cash,
    });
  }
  return { items, total };
};

export function PortfolioHeatmap() {
  const portfolio = usePortfolioStore((s) => s.portfolio);
  const refresh = usePortfolioStore((s) => s.refresh);
  const select = useSelectionStore((s) => s.select);
  const byTicker = usePriceStore((s) => s.byTicker);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ width: 600, height: 320 });

  useEffect(() => {
    if (!portfolio) refresh();
  }, [portfolio, refresh]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) setSize({ width, height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const tiles = useMemo<TreemapTile<Tile>[]>(() => {
    if (!portfolio) return [];
    const pricesByTicker = Object.fromEntries(
      Object.values(byTicker).map((t) => [t.ticker, t.price] as const),
    );
    const { items } = buildTiles(
      portfolio.positions,
      pricesByTicker,
      portfolio.cash_balance,
    );
    if (items.length === 0) return [];
    return squarify(
      items.map((it) => ({ item: it, value: it.weight })),
      size.width,
      size.height,
    );
  }, [portfolio, byTicker, size]);

  const isEmpty = !portfolio || tiles.length === 0;

  return (
    <section
      className="panel flex h-full flex-col overflow-hidden"
      data-testid="heatmap"
    >
      <header className="flex items-center justify-between border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-fg-muted">
          Allocation Heatmap
        </h2>
        <span className="font-mono-tabular text-[11px] text-fg-dim">
          weighted by market value
        </span>
      </header>
      <div ref={containerRef} className="relative flex-1 overflow-hidden">
        {isEmpty && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-fg-dim">
            No allocation data yet.
          </div>
        )}
        {tiles.map((t) => (
          <button
            key={t.item.ticker}
            type="button"
            onClick={() =>
              t.item.ticker !== "CASH" ? select(t.item.ticker) : undefined
            }
            className="absolute overflow-hidden border border-bg-base/80 text-left transition-transform hover:z-10 hover:scale-[1.01]"
            style={{
              left: t.x,
              top: t.y,
              width: t.width,
              height: t.height,
              background:
                t.item.ticker === "CASH"
                  ? "color-mix(in oklab, var(--color-accent-yellow) 20%, var(--color-bg-panel-2))"
                  : colorFor(t.item.pnlPct),
            }}
            data-testid="heatmap-tile"
            data-ticker={t.item.ticker}
          >
            {t.width > 60 && t.height > 30 && (
              <div className="flex h-full flex-col justify-between p-2">
                <span className="font-mono-tabular text-[11px] font-semibold text-fg-primary">
                  {t.item.ticker}
                </span>
                <span className="font-mono-tabular text-[10px] text-fg-primary/85">
                  {t.item.ticker === "CASH"
                    ? fmtPrice(t.item.marketValue)
                    : `${t.item.pnlPct >= 0 ? "+" : ""}${t.item.pnlPct.toFixed(2)}%`}
                </span>
              </div>
            )}
          </button>
        ))}
      </div>
    </section>
  );
}
