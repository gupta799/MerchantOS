import { expect, test } from "@playwright/test";

test("merchant dashboard auto-runs computer-use telemetry simulation", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("link", { name: "Merchant OS home" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Automated computer-use telemetry for agent-ready commerce" })
  ).toBeVisible();
  await expect(page.getByText("Autonomous commerce readiness probe")).toBeVisible();
  await expect(page.getByText("Readiness score")).toBeVisible();
  await expect(page.getByText("Computer-use trace")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recommended tools and resources for agents" })).toBeVisible();

  await expect(page.getByText("succeeded").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("catalog.search")).toBeVisible();
  await expect(page.getByText("Task completion")).toBeVisible();
  await expect(page.getByText("StormRunner GTX").first()).toBeVisible();
  await expect(page.getByText("Pay now")).toHaveCount(0);
});
