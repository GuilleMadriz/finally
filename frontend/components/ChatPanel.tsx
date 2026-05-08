"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { fmtPrice } from "@/lib/format";
import { usePortfolioStore } from "@/lib/portfolioStore";
import type {
  ChatActions,
  ChatBubble,
  ExecutedTrade,
  ExecutedWatchlistChange,
} from "@/lib/types";

interface ChatPanelProps {
  onWatchlistChanged?: () => void;
}

const newId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `local-${Math.random().toString(36).slice(2)}`;

function TradeChip({ trade }: { trade: ExecutedTrade }) {
  const success = !trade.error;
  const tone = success
    ? "border-up/40 bg-up/10 text-up"
    : "border-down/40 bg-down/10 text-down";
  return (
    <div
      data-testid="chat-action-chip"
      data-action="trade"
      data-success={success}
      data-ticker={trade.ticker}
      className={`mt-1 inline-flex items-center gap-2 rounded border px-2 py-1 font-mono-tabular text-[11px] ${tone}`}
    >
      <span className="font-semibold tracking-wider">TRADE</span>
      <span>
        {trade.side.toUpperCase()} {trade.quantity} {trade.ticker}
        {success ? ` @ ${fmtPrice(trade.price)}` : ""}
      </span>
      {!success && trade.error && (
        <span className="text-fg-muted">· {trade.error}</span>
      )}
    </div>
  );
}

function WatchlistChip({ change }: { change: ExecutedWatchlistChange }) {
  const tone = change.applied
    ? "border-accent-blue/40 bg-accent-blue/10 text-accent-blue"
    : "border-down/40 bg-down/10 text-down";
  return (
    <div
      data-testid="chat-action-chip"
      data-action="watchlist"
      data-success={change.applied}
      data-ticker={change.ticker}
      className={`mt-1 inline-flex items-center gap-2 rounded border px-2 py-1 font-mono-tabular text-[11px] ${tone}`}
    >
      <span className="font-semibold tracking-wider">WATCHLIST</span>
      <span>
        {change.action.toUpperCase()} {change.ticker}
      </span>
      {change.error && <span className="text-fg-muted">· {change.error}</span>}
    </div>
  );
}

function Bubble({ bubble }: { bubble: ChatBubble }) {
  const mine = bubble.role === "user";
  const trades = bubble.actions?.trades ?? [];
  const watchlist = bubble.actions?.watchlist_changes ?? [];
  return (
    <div
      data-testid="chat-message"
      data-role={bubble.role}
      className={`flex ${mine ? "justify-end" : "justify-start"}`}
    >
      <div className="max-w-[85%] space-y-1">
        <div
          className={`whitespace-pre-wrap rounded-lg px-3 py-2 text-sm leading-relaxed ${
            mine
              ? "bg-accent-blue/20 text-fg-primary"
              : "bg-bg-panel-2 text-fg-primary"
          }`}
        >
          {bubble.content}
        </div>
        {!mine &&
          trades.map((t, i) => <TradeChip key={`t${i}`} trade={t} />)}
        {!mine &&
          watchlist.map((w, i) => (
            <WatchlistChip key={`w${i}`} change={w} />
          ))}
      </div>
    </div>
  );
}

const hasSuccessfulTrade = (a: ChatActions | undefined) =>
  !!a && a.trades.some((t) => !t.error);
const hasSuccessfulWatchlist = (a: ChatActions | undefined) =>
  !!a && a.watchlist_changes.some((w) => w.applied);

export function ChatPanel({ onWatchlistChanged }: ChatPanelProps) {
  const [bubbles, setBubbles] = useState<ChatBubble[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const refreshPortfolio = usePortfolioStore((s) => s.refresh);
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [bubbles, busy]);

  const onSend = async () => {
    const content = input.trim();
    if (!content || busy) return;
    setBubbles((b) => [
      ...b,
      { id: newId(), role: "user", content },
    ]);
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const res = await api.sendChat(content);
      setBubbles((b) => [
        ...b,
        {
          id: newId(),
          role: "assistant",
          content: res.message,
          actions: res.actions,
        },
      ]);
      if (hasSuccessfulTrade(res.actions)) await refreshPortfolio();
      if (hasSuccessfulWatchlist(res.actions)) onWatchlistChanged?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className="panel flex h-full flex-col overflow-hidden"
      data-testid="chat-panel"
    >
      <header className="flex items-center justify-between border-b border-border-muted px-3 py-2">
        <div className="flex items-baseline gap-2">
          <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-fg-muted">
            FinAlly
          </h2>
          <span className="text-[10px] text-fg-dim">AI copilot</span>
        </div>
        <span
          className="font-mono-tabular text-[10px] uppercase tracking-wider text-accent-yellow"
          aria-hidden="true"
        >
          live
        </span>
      </header>

      <div
        ref={scrollerRef}
        className="flex-1 space-y-3 overflow-y-auto px-3 py-3"
        data-testid="chat-scroll"
      >
        {bubbles.length === 0 && !busy && (
          <p className="text-xs text-fg-dim">
            Ask FinAlly about your portfolio, request analysis, or have it place
            a trade.
          </p>
        )}
        {bubbles.map((b) => (
          <Bubble key={b.id} bubble={b} />
        ))}
        {busy && (
          <div
            className="flex items-center gap-2 text-xs text-fg-muted"
            role="status"
            aria-live="polite"
          >
            <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-accent-yellow" />
            Thinking…
          </div>
        )}
      </div>

      {error && (
        <div className="border-t border-down/40 bg-down/10 px-3 py-1.5 text-xs text-down">
          {error}
        </div>
      )}

      <form
        className="flex items-center gap-2 border-t border-border-muted px-3 py-2"
        onSubmit={(e) => {
          e.preventDefault();
          onSend();
        }}
      >
        <input
          aria-label="Chat message"
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={busy ? "Sending…" : "Ask FinAlly…"}
          disabled={busy}
          className="flex-1 rounded border border-border-muted bg-bg-base px-2 py-1.5 text-sm text-fg-primary placeholder:text-fg-dim focus:border-accent-blue focus:outline-none disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          aria-label="Send"
          data-testid="chat-send"
          className="rounded bg-accent-purple px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-white transition disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </section>
  );
}
