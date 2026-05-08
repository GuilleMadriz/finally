"use client";

import { useEffect } from "react";
import { AppHeader } from "./AppHeader";
import { ChatPanel } from "./ChatPanel";
import { MainChart } from "./MainChart";
import { PnlChart } from "./PnlChart";
import { PortfolioHeatmap } from "./PortfolioHeatmap";
import { PositionsTable } from "./PositionsTable";
import { PriceStreamProvider } from "./PriceStreamProvider";
import { TradeBar } from "./TradeBar";
import { WatchlistPanel } from "./WatchlistPanel";
import { usePortfolioStore } from "@/lib/portfolioStore";
import { useChatVisibility, useWatchlistStore } from "@/lib/watchlistStore";

export function AppShell() {
  const chatOpen = useChatVisibility((s) => s.open);
  const setChatOpen = useChatVisibility((s) => s.setOpen);
  const refreshPortfolio = usePortfolioStore((s) => s.refresh);
  const bumpWatchlist = useWatchlistStore((s) => s.bumpRefresh);

  useEffect(() => {
    refreshPortfolio();
  }, [refreshPortfolio]);

  return (
    <PriceStreamProvider>
      <div className="flex h-screen flex-col bg-bg-base text-fg-primary">
        <AppHeader />

        <div className="grid min-h-0 flex-1 gap-2 p-2 lg:grid-cols-[280px_minmax(0,1fr)_320px] lg:grid-rows-1">
          <aside className="min-h-0 lg:row-span-1">
            <WatchlistPanel />
          </aside>

          <main className="grid min-h-0 grid-rows-[minmax(0,3fr)_minmax(0,2fr)_auto] gap-2">
            <div className="min-h-0">
              <MainChart />
            </div>
            <div className="min-h-0">
              <PositionsTable />
            </div>
            <TradeBar onTrade={() => bumpWatchlist()} />
          </main>

          <aside className="grid min-h-0 grid-rows-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.4fr)] gap-2">
            <PortfolioHeatmap />
            <PnlChart />
            {chatOpen ? (
              <div className="min-h-0">
                <ChatPanel onWatchlistChanged={() => bumpWatchlist()} />
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setChatOpen(true)}
                className="panel flex items-center justify-center text-xs uppercase tracking-[0.18em] text-fg-muted hover:text-accent-yellow"
              >
                Open AI copilot
              </button>
            )}
          </aside>
        </div>
      </div>
    </PriceStreamProvider>
  );
}
