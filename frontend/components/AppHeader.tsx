"use client";

import { usePortfolioStore } from "@/lib/portfolioStore";
import { useConnectionStore } from "@/lib/connectionStore";
import { useChatVisibility } from "@/lib/watchlistStore";
import { fmtPrice } from "@/lib/format";

const STATUS_COLOR = {
  connected: { dot: "bg-up", label: "live", tone: "text-up" },
  connecting: { dot: "bg-accent-yellow", label: "connecting", tone: "text-accent-yellow" },
  disconnected: { dot: "bg-down", label: "offline", tone: "text-down" },
} as const;

export function AppHeader() {
  const portfolio = usePortfolioStore((s) => s.portfolio);
  const status = useConnectionStore((s) => s.status);
  const chatOpen = useChatVisibility((s) => s.open);
  const toggleChat = useChatVisibility((s) => s.toggle);
  const meta = STATUS_COLOR[status];

  const total = portfolio?.total_value ?? null;
  const cash = portfolio?.cash_balance ?? null;
  const pnl = portfolio?.total_unrealized_pnl ?? null;
  const pnlTone =
    pnl == null ? "text-fg-muted" : pnl >= 0 ? "text-up" : "text-down";

  return (
    <header className="flex items-center justify-between border-b border-border-muted bg-bg-base/95 px-4 py-2 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span
            className="text-base font-semibold tracking-tight"
            style={{ color: "var(--color-accent-yellow)" }}
          >
            FinAlly
          </span>
          <span className="hidden text-[10px] uppercase tracking-[0.18em] text-fg-dim sm:inline">
            AI Trading Workstation
          </span>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <Stat
          label="Total Value"
          value={fmtPrice(total)}
          mono
          testId="portfolio-total"
        />
        <Stat
          label="Unrealized P/L"
          value={
            pnl != null
              ? `${pnl >= 0 ? "+" : ""}${fmtPrice(pnl)}`
              : "—"
          }
          mono
          tone={pnlTone}
        />
        <Stat label="Cash" value={fmtPrice(cash)} mono testId="cash-balance" />

        <div
          className="flex items-center gap-2 rounded border border-border-muted bg-bg-panel-2 px-2 py-1"
          data-testid="connection-status"
          data-state={status === "connecting" ? "reconnecting" : status}
          aria-label={`SSE ${meta.label}`}
        >
          <span
            className={`relative inline-flex h-2 w-2 rounded-full ${meta.dot}`}
          >
            {status === "connecting" && (
              <span className="absolute inset-0 animate-ping rounded-full bg-accent-yellow opacity-75" />
            )}
          </span>
          <span
            className={`font-mono-tabular text-[10px] uppercase tracking-wider ${meta.tone}`}
          >
            {meta.label}
          </span>
        </div>

        <button
          type="button"
          onClick={toggleChat}
          aria-label={chatOpen ? "Hide chat" : "Show chat"}
          aria-pressed={chatOpen}
          data-testid="chat-toggle"
          className="rounded border border-border-muted bg-bg-panel-2 px-2 py-1 font-mono-tabular text-[10px] uppercase tracking-wider text-fg-muted transition hover:text-accent-yellow"
        >
          {chatOpen ? "hide chat" : "show chat"}
        </button>
      </div>
    </header>
  );
}

interface StatProps {
  label: string;
  value: string;
  mono?: boolean;
  tone?: string;
  testId?: string;
}

function Stat({ label, value, mono, tone, testId }: StatProps) {
  return (
    <div className="flex flex-col items-end leading-tight">
      <span className="text-[9px] uppercase tracking-[0.18em] text-fg-dim">
        {label}
      </span>
      <span
        className={`${mono ? "font-mono-tabular" : ""} text-sm ${tone ?? "text-fg-primary"}`}
        data-testid={testId}
      >
        {value}
      </span>
    </div>
  );
}
