"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { usePortfolioStore } from "@/lib/portfolioStore";
import { useSelectionStore } from "@/lib/selectionStore";
import type { TradeResponse } from "@/lib/types";

interface TradeBarProps {
  onTrade?: (trade: TradeResponse) => void;
}

export function TradeBar({ onTrade }: TradeBarProps) {
  const selected = useSelectionStore((s) => s.selected);
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<TradeResponse | null>(null);
  const refresh = usePortfolioStore((s) => s.refresh);

  const effectiveTicker = (ticker || selected || "").trim().toUpperCase();
  const qty = Number(quantity);
  const valid = effectiveTicker.length > 0 && qty > 0 && Number.isFinite(qty);

  const submit = async (side: "buy" | "sell") => {
    if (!valid) return;
    setBusy(true);
    setError(null);
    setLast(null);
    try {
      const result = await api.trade({
        ticker: effectiveTicker,
        side,
        quantity: qty,
      });
      setLast(result);
      setQuantity("");
      onTrade?.(result);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className="panel flex flex-col gap-2 px-3 py-2"
      data-testid="trade-bar"
    >
      <div className="flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-[0.18em] text-fg-dim">
          Trade
        </span>
        <input
          aria-label="Ticker"
          data-testid="trade-ticker"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder={selected ?? "TICKER"}
          maxLength={8}
          className="w-24 rounded border border-border-muted bg-bg-base px-2 py-1 font-mono-tabular text-sm uppercase text-fg-primary placeholder:text-fg-dim focus:border-accent-blue focus:outline-none"
        />
        <input
          aria-label="Quantity"
          data-testid="trade-quantity"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="Qty"
          inputMode="decimal"
          className="w-24 rounded border border-border-muted bg-bg-base px-2 py-1 font-mono-tabular text-sm text-fg-primary placeholder:text-fg-dim focus:border-accent-blue focus:outline-none"
        />
        <button
          type="button"
          aria-label="Buy"
          data-testid="trade-buy"
          onClick={() => submit("buy")}
          disabled={!valid || busy}
          className="rounded bg-up/90 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-bg-base transition hover:bg-up disabled:opacity-40"
        >
          Buy
        </button>
        <button
          type="button"
          aria-label="Sell"
          data-testid="trade-sell"
          onClick={() => submit("sell")}
          disabled={!valid || busy}
          className="rounded bg-down/90 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-bg-base transition hover:bg-down disabled:opacity-40"
        >
          Sell
        </button>
        <span className="ml-auto font-mono-tabular text-[11px] text-fg-dim">
          Market order · instant fill
        </span>
      </div>

      {error && (
        <div className="rounded border border-down/40 bg-down/10 px-2 py-1 text-xs text-down" role="alert">
          {error}
        </div>
      )}
      {last && (
        <div className="rounded border border-up/40 bg-up/10 px-2 py-1 text-xs text-up">
          Filled: {last.side.toUpperCase()} {last.quantity} {last.ticker} @ ${last.price.toFixed(2)}
        </div>
      )}
    </section>
  );
}
