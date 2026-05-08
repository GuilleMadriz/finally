import { expect, test } from "@playwright/test";
import { getPortfolio, gotoApp, positionQty } from "./helpers";

test.describe("scenarios 4 & 5: trade buy and sell", () => {
  test("buy AAPL via the trade bar: cash decreases, position appears", async ({ page, request }) => {
    await gotoApp(page);
    const before = await getPortfolio(request);
    const beforeQty = positionQty(before, "AAPL");

    await page.getByTestId("trade-ticker").fill("AAPL");
    await page.getByTestId("trade-quantity").fill("2");
    await page.getByTestId("trade-buy").click();

    // Position row appears in the table with the new quantity.
    const row = page.locator('[data-testid="position-row"][data-ticker="AAPL"]');
    await expect(row).toBeVisible({ timeout: 10_000 });

    const after = await getPortfolio(request);
    expect(positionQty(after, "AAPL")).toBe(beforeQty + 2);
    expect(after.cash_balance).toBeLessThan(before.cash_balance);
  });

  test("sell AAPL via the trade bar: cash increases, position decreases", async ({ page, request }) => {
    await gotoApp(page);
    // Ensure we own at least 1 AAPL share.
    const before = await getPortfolio(request);
    if (positionQty(before, "AAPL") < 1) {
      const buy = await request.post("/api/portfolio/trade", {
        data: { ticker: "AAPL", quantity: 1, side: "buy" },
      });
      expect(buy.status()).toBe(200);
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForSelector('[data-testid="watchlist"]');
    }
    const baseline = await getPortfolio(request);
    const baselineQty = positionQty(baseline, "AAPL");

    await page.getByTestId("trade-ticker").fill("AAPL");
    await page.getByTestId("trade-quantity").fill("1");
    await page.getByTestId("trade-sell").click();

    // Wait for the sell to settle by polling the API.
    await expect.poll(async () => positionQty(await getPortfolio(request), "AAPL")).toBe(baselineQty - 1);

    const after = await getPortfolio(request);
    expect(after.cash_balance).toBeGreaterThan(baseline.cash_balance);
  });
});
