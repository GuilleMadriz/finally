"use client";

import { useEffect } from "react";
import { usePortfolioStore } from "@/lib/portfolioStore";
import { usePriceStore } from "@/lib/priceStore";
import { useSelectionStore } from "@/lib/selectionStore";
import { fmtPrice } from "@/lib/format";
import type { Position } from "@/lib/types";

interface RowProps {
  position: Position;
  onSelect: (ticker: string) => void;
}

function Row({ position, onSelect }: RowProps) {
  const tick = usePriceStore((s) => s.byTicker[position.ticker]);
  const livePrice = tick?.price ?? position.current_price;
  const marketValue = position.quantity * livePrice;
  const unrealized = (livePrice - position.avg_cost) * position.quantity;
  const unrealizedPct =
    position.avg_cost > 0
      ? ((livePrice - position.avg_cost) / position.avg_cost) * 100
      : 0;
  const profit = unrealized >= 0;
  const tone = profit ? "text-up" : "text-down";

  return (
    <tr
      onClick={() => onSelect(position.ticker)}
      className="cursor-pointer border-b border-border-muted/60 hover:bg-bg-panel-2/60"
      data-testid="position-row"
      data-ticker={position.ticker}
    >
      <td className="px-3 py-1.5 font-mono-tabular font-semibold text-fg-primary">
        {position.ticker}
      </td>
      <td className="px-3 py-1.5 text-right font-mono-tabular text-fg-primary">
        {position.quantity.toFixed(2)}
      </td>
      <td className="px-3 py-1.5 text-right font-mono-tabular text-fg-muted">
        {fmtPrice(position.avg_cost)}
      </td>
      <td className="px-3 py-1.5 text-right font-mono-tabular text-fg-primary">
        {fmtPrice(livePrice)}
      </td>
      <td className="px-3 py-1.5 text-right font-mono-tabular text-fg-muted">
        {fmtPrice(marketValue)}
      </td>
      <td className={`px-3 py-1.5 text-right font-mono-tabular ${tone}`}>
        {profit ? "+" : ""}
        {fmtPrice(unrealized)}
      </td>
      <td
        className={`px-3 py-1.5 text-right font-mono-tabular ${tone}`}
        data-testid="position-pnl-pct"
      >
        {profit ? "+" : ""}
        {unrealizedPct.toFixed(2)}%
      </td>
    </tr>
  );
}

export function PositionsTable() {
  const portfolio = usePortfolioStore((s) => s.portfolio);
  const refresh = usePortfolioStore((s) => s.refresh);
  const select = useSelectionStore((s) => s.select);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const positions = portfolio?.positions ?? [];

  return (
    <section className="panel flex h-full flex-col overflow-hidden" data-testid="positions-table">
      <header className="flex items-center justify-between border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-fg-muted">
          Positions
        </h2>
        <span className="font-mono-tabular text-[11px] text-fg-dim">
          {positions.length}
        </span>
      </header>

      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-bg-panel">
            <tr className="text-[10px] uppercase tracking-wider text-fg-dim">
              <th className="px-3 py-1.5 text-left font-medium">Symbol</th>
              <th className="px-3 py-1.5 text-right font-medium">Qty</th>
              <th className="px-3 py-1.5 text-right font-medium">Avg Cost</th>
              <th className="px-3 py-1.5 text-right font-medium">Last</th>
              <th className="px-3 py-1.5 text-right font-medium">Mkt Value</th>
              <th className="px-3 py-1.5 text-right font-medium">Unrlz P/L</th>
              <th className="px-3 py-1.5 text-right font-medium">% Δ</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <Row key={p.ticker} position={p} onSelect={select} />
            ))}
          </tbody>
        </table>

        {positions.length === 0 && (
          <div className="px-3 py-6 text-center text-sm text-fg-dim">
            No open positions yet. Use the trade bar below to start.
          </div>
        )}
      </div>
    </section>
  );
}
