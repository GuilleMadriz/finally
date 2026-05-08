import { expect, test } from "@playwright/test";
import { gotoApp } from "./helpers";

test.describe("scenario 6: portfolio visualization", () => {
  test("heatmap renders at least one tile and P&L chart is visible", async ({ page, request }) => {
    // Buy something so the heatmap has at least one ticker tile beyond CASH.
    await request.post("/api/portfolio/trade", {
      data: { ticker: "MSFT", quantity: 1, side: "buy" },
    });

    await gotoApp(page);

    const heatmap = page.getByTestId("heatmap");
    await expect(heatmap).toBeVisible();

    const tiles = heatmap.getByTestId("heatmap-tile");
    await expect(tiles.first()).toBeVisible({ timeout: 10_000 });
    expect(await tiles.count()).toBeGreaterThan(0);

    await expect(page.getByTestId("pnl-chart")).toBeVisible();
  });
});
