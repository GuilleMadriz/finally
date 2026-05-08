"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkline } from "./Sparkline";
import { usePriceStore } from "@/lib/priceStore";
import { fmtPrice } from "@/lib/format";
import type { WatchlistEntry } from "@/lib/types";

interface WatchlistRowProps {
  entry: WatchlistEntry;
  selected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

const formatChangePct = (pct: number) => {
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
};

export function WatchlistRow({
  entry,
  selected,
  onSelect,
  onRemove,
}: WatchlistRowProps) {
  const tick = usePriceStore((s) => s.byTicker[entry.ticker]);
  const [flashClass, setFlashClass] = useState("");
  const lastFlashKey = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!tick) return;
    if (lastFlashKey.current === tick.flashKey) return;
    lastFlashKey.current = tick.flashKey;
    if (tick.direction === "up") setFlashClass("price-flash-up");
    else if (tick.direction === "down") setFlashClass("price-flash-down");
    const t = setTimeout(() => setFlashClass(""), 600);
    return () => clearTimeout(t);
  }, [tick?.flashKey, tick?.direction, tick]);

  const price = tick?.price ?? entry.price ?? null;
  const changePct = tick?.change_percent ?? entry.change_percent ?? null;

  const changeColor =
    changePct == null
      ? "text-fg-muted"
      : changePct >= 0
        ? "text-up"
        : "text-down";

  const flashState =
    flashClass === "price-flash-up"
      ? "up"
      : flashClass === "price-flash-down"
        ? "down"
        : undefined;

  return (
    <div
      data-testid="watchlist-row"
      data-ticker={entry.ticker}
      data-flash={flashState}
      onClick={() => onSelect(entry.ticker)}
      className={`group grid cursor-pointer grid-cols-[1fr_auto_auto_auto_auto] items-center gap-3 border-b border-border-muted/60 px-3 py-2 text-sm transition-colors ${
        selected ? "bg-bg-panel-2" : "hover:bg-bg-panel-2/60"
      } ${flashClass}`}
    >
      <div className="flex flex-col">
        <span className="font-mono-tabular font-semibold text-fg-primary">
          {entry.ticker}
        </span>
        <span className="text-[10px] uppercase tracking-wider text-fg-dim">
          {selected ? "selected" : ""}
        </span>
      </div>
      <Sparkline points={tick?.sparkline ?? []} width={88} height={24} />
      <span
        className="font-mono-tabular text-right text-fg-primary"
        data-testid="watchlist-price"
      >
        {fmtPrice(price)}
      </span>
      <span
        className={`font-mono-tabular text-right text-xs ${changeColor}`}
        data-testid="watchlist-change"
      >
        {changePct != null ? formatChangePct(changePct) : "—"}
      </span>
      <button
        type="button"
        data-testid="watchlist-remove"
        onClick={(e) => {
          e.stopPropagation();
          onRemove(entry.ticker);
        }}
        aria-label={`Remove ${entry.ticker}`}
        className="rounded px-2 py-0.5 text-xs text-fg-dim opacity-0 transition-opacity hover:bg-border-muted hover:text-fg-primary group-hover:opacity-100"
      >
        ×
      </button>
    </div>
  );
}
