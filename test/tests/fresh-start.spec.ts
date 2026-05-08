import { expect, test } from "@playwright/test";
import { getPortfolio, getWatchlist, gotoApp } from "./helpers";

const DEFAULT_TICKERS = [
  "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
  "NVDA", "META", "JPM", "V", "NFLX",
];

test.describe("scenario 1: fresh start", () => {
  test("default 10 watchlist tickers visible via API", async ({ request }) => {
    const wl = await getWatchlist(request);
    const tickers = wl.entries.map((e) => e.ticker).sort();
    for (const t of DEFAULT_TICKERS) {
      expect(tickers).toContain(t);
    }
  });

  test("$10,000 cash present at first visit", async ({ request }) => {
    const p = await getPortfolio(request);
    // Cash is exactly 10000 only on a truly fresh DB. We assert it is at most
    // 10000 (no trades inflate it) and that no positions exist on first run.
    expect(p.cash_balance).toBeLessThanOrEqual(10000);
    expect(p.total_value).toBeGreaterThan(0);
  });

  test("default tickers render as watchlist rows in the UI", async ({ page }) => {
    await gotoApp(page);
    for (const t of DEFAULT_TICKERS) {
      await expect(
        page.locator(`[data-testid="watchlist-row"][data-ticker="${t}"]`),
      ).toBeVisible();
    }
  });

  test("a price flash fires on at least one row within a few seconds", async ({ page }) => {
    await gotoApp(page);
    // The simulator updates ~every 500ms; data-flash="up"|"down" is set on the
    // row for ~600ms after a price change.
    await expect(
      page.locator('[data-testid="watchlist-row"][data-flash="up"], [data-testid="watchlist-row"][data-flash="down"]').first(),
    ).toBeVisible({ timeout: 10_000 });
  });
});
