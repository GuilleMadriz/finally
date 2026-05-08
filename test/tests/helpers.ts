import { APIRequestContext, expect, Page } from "@playwright/test";

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  total_unrealized_pnl: number;
  positions: Array<{
    ticker: string;
    quantity: number;
    avg_cost: number;
    current_price: number;
    unrealized_pnl: number;
    pnl_percent: number;
  }>;
}

export interface WatchlistEntry {
  ticker: string;
  price: number;
  previous_price: number;
  change: number;
  change_percent: number;
  direction: "up" | "down" | "flat";
}

export async function getPortfolio(req: APIRequestContext): Promise<Portfolio> {
  const res = await req.get("/api/portfolio");
  expect(res.status()).toBe(200);
  return (await res.json()) as Portfolio;
}

export async function getWatchlist(
  req: APIRequestContext,
): Promise<{ entries: WatchlistEntry[] }> {
  const res = await req.get("/api/watchlist");
  expect(res.status()).toBe(200);
  return (await res.json()) as { entries: WatchlistEntry[] };
}

export async function gotoApp(page: Page): Promise<void> {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="watchlist"]');
}

/** Resolves to the position quantity for a ticker, or 0 if absent. */
export function positionQty(p: Portfolio, ticker: string): number {
  return p.positions.find((x) => x.ticker === ticker)?.quantity ?? 0;
}
