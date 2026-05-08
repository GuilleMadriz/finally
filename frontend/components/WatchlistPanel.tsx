"use client";

import { useCallback, useEffect, useState } from "react";
import { WatchlistRow } from "./WatchlistRow";
import { api } from "@/lib/api";
import { useSelectionStore } from "@/lib/selectionStore";
import { useWatchlistStore } from "@/lib/watchlistStore";
import type { WatchlistEntry } from "@/lib/types";

export function WatchlistPanel() {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  const selected = useSelectionStore((s) => s.selected);
  const select = useSelectionStore((s) => s.select);
  const refreshKey = useWatchlistStore((s) => s.refreshKey);

  const refresh = useCallback(async () => {
    try {
      const data = await api.getWatchlist();
      setEntries(data.entries);
      if (!selected && data.entries.length > 0) select(data.entries[0].ticker);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [select, selected]);

  useEffect(() => {
    refresh();
  }, [refresh, refreshKey]);

  const onAdd = async () => {
    const ticker = input.trim().toUpperCase();
    if (!ticker) return;
    setBusy(true);
    setError(null);
    try {
      await api.addToWatchlist(ticker);
      setInput("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onRemove = async (ticker: string) => {
    setError(null);
    try {
      await api.removeFromWatchlist(ticker);
      setEntries((rows) => rows.filter((r) => r.ticker !== ticker));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <section
      data-testid="watchlist"
      className="panel flex h-full flex-col overflow-hidden"
    >
      <header className="flex items-center justify-between border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-fg-muted">
          Watchlist
        </h2>
        <span className="font-mono-tabular text-[11px] text-fg-dim">
          {entries.length}
        </span>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onAdd();
        }}
        className="flex items-center gap-2 border-b border-border-muted px-3 py-2"
      >
        <input
          aria-label="Add ticker"
          data-testid="watchlist-add-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Add ticker"
          className="flex-1 rounded border border-border-muted bg-bg-base px-2 py-1 font-mono-tabular text-sm uppercase text-fg-primary placeholder:text-fg-dim focus:border-accent-blue focus:outline-none"
          maxLength={8}
        />
        <button
          type="submit"
          data-testid="watchlist-add-submit"
          disabled={busy || !input.trim()}
          className="rounded bg-accent-blue px-3 py-1 text-xs font-semibold text-white transition-opacity disabled:opacity-40"
        >
          Add
        </button>
      </form>

      <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-3 border-b border-border-muted px-3 py-1.5 text-[10px] uppercase tracking-wider text-fg-dim">
        <span>Symbol</span>
        <span className="text-right">Trend</span>
        <span className="text-right">Price</span>
        <span className="text-right">Δ %</span>
        <span />
      </div>

      <div className="flex-1 overflow-y-auto">
        {entries.map((entry) => (
          <WatchlistRow
            key={entry.ticker}
            entry={entry}
            selected={selected === entry.ticker}
            onSelect={select}
            onRemove={onRemove}
          />
        ))}
        {entries.length === 0 && (
          <div className="px-3 py-6 text-center text-sm text-fg-dim">
            No tickers yet.
          </div>
        )}
      </div>

      {error && (
        <div
          className="truncate border-t border-down/40 bg-down/10 px-3 py-1.5 text-xs text-down"
          title={error}
        >
          {error.slice(0, 120)}
        </div>
      )}
    </section>
  );
}
