import { expect, test } from "@playwright/test";

// PLAN.md §12 scenario 8: assert the connection-status state machine.
//
// Reliably tearing down a live EventSource from inside Playwright is fiddly
// (context.setOffline and CDP Network.emulateNetworkConditions both leave
// already-open SSE streams intact in Chromium). Instead we assert the same
// state machine from a different angle:
//   1. Load the page with /api/stream/prices blocked at the route layer →
//      status flips away from 'connected' (initially 'connecting', then
//      'disconnected' once EventSource fires onerror).
//   2. Unblock the route and reload → status reaches 'connected'.
test.describe("scenario 8: SSE resilience", () => {
  test("status reaches 'connected' on a healthy page load", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="watchlist"]');
    await expect(page.getByTestId("connection-status")).toHaveAttribute(
      "data-state",
      "connected",
      { timeout: 15_000 },
    );
  });

  test("status flips to disconnected when SSE is unavailable, recovers when restored", async ({ page, context }) => {
    // Block SSE before navigation so the EventSource fails on its first attempt.
    await context.route("**/api/stream/prices", (route) => route.abort("failed"));

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="watchlist"]');

    // EventSource.onerror fires → status becomes 'disconnected'.
    await expect(page.getByTestId("connection-status")).toHaveAttribute(
      "data-state",
      "disconnected",
      { timeout: 15_000 },
    );

    // Restore the route and reload — the new EventSource should reach the
    // server and the dot returns to 'connected'.
    await context.unroute("**/api/stream/prices");
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="watchlist"]');

    await expect(page.getByTestId("connection-status")).toHaveAttribute(
      "data-state",
      "connected",
      { timeout: 20_000 },
    );
  });
});
