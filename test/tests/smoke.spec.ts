import { expect, test } from "@playwright/test";

test("api health responds 200", async ({ request }) => {
  const res = await request.get("/api/health");
  expect(res.status()).toBe(200);
});

test("home page loads with FinAlly title", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/FinAlly/i);
});
