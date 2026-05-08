import { expect, test } from "@playwright/test";
import { getWatchlist, gotoApp } from "./helpers";

test.describe("scenarios 2 & 3: watchlist add/remove", () => {
  test("add a new ticker via UI input", async ({ page, request }) => {
    await gotoApp(page);

    const ticker = "PYPL";
    // Ensure it's not already present (defensive cleanup via API).
    await request.delete(`/api/watchlist/${ticker}`);
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="watchlist"]');

    const input = page.getByTestId("watchlist-add-input");
    await input.fill(ticker);
    await page.getByTestId("watchlist-add-submit").click();

    await expect(
      page.locator(`[data-testid="watchlist-row"][data-ticker="${ticker}"]`),
    ).toBeVisible({ timeout: 10_000 });

    const wl = await getWatchlist(request);
    expect(wl.entries.map((e) => e.ticker)).toContain(ticker);
  });

  test("remove a ticker via UI button", async ({ page, request }) => {
    await gotoApp(page);

    const ticker = "TSLA";
    const row = page.locator(`[data-testid="watchlist-row"][data-ticker="${ticker}"]`);
    await expect(row).toBeVisible();

    await row.getByTestId("watchlist-remove").click();

    await expect(row).toBeHidden({ timeout: 10_000 });

    const wl = await getWatchlist(request);
    expect(wl.entries.map((e) => e.ticker)).not.toContain(ticker);
  });
});
