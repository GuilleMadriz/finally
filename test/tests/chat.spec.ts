import { expect, test } from "@playwright/test";
import { getPortfolio, getWatchlist, gotoApp, positionQty } from "./helpers";

async function sendChat(page: import("@playwright/test").Page, text: string) {
  await page.getByTestId("chat-input").fill(text);
  await page.getByTestId("chat-send").click();
}

test.describe("scenario 7: AI chat (LLM_MOCK)", () => {
  test("plain text echo: 'hello' produces 'Mock: hello' assistant reply", async ({ page }) => {
    await gotoApp(page);
    await sendChat(page, "hello");

    const assistantMsgs = page.locator('[data-testid="chat-message"][data-role="assistant"]');
    await expect(assistantMsgs.last()).toContainText("Mock: hello", { timeout: 10_000 });
  });

  test("'buy 1 AAPL' triggers a trade and shows a trade action chip", async ({ page, request }) => {
    await gotoApp(page);
    const before = await getPortfolio(request);
    const beforeQty = positionQty(before, "AAPL");

    await sendChat(page, "buy 1 AAPL");

    const chip = page.locator(
      '[data-testid="chat-action-chip"][data-action="trade"][data-ticker="AAPL"][data-success="true"]',
    );
    await expect(chip).toBeVisible({ timeout: 10_000 });

    await expect.poll(async () => positionQty(await getPortfolio(request), "AAPL")).toBe(beforeQty + 1);
  });

  test("'add PYPL' triggers a watchlist add and shows a watchlist action chip", async ({ page, request }) => {
    // Defensive cleanup so the trigger has work to do.
    await request.delete("/api/watchlist/PYPL");

    await gotoApp(page);
    await sendChat(page, "add PYPL");

    const chip = page.locator(
      '[data-testid="chat-action-chip"][data-action="watchlist"][data-ticker="PYPL"][data-success="true"]',
    );
    await expect(chip).toBeVisible({ timeout: 10_000 });

    const wl = await getWatchlist(request);
    expect(wl.entries.map((e) => e.ticker)).toContain("PYPL");
  });
});
