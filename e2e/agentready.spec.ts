import { expect, test } from "@playwright/test";

test("automated telemetry lab records CUA trace and readiness outputs", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Merchant OS · Automated computer-use telemetry lab")).toBeVisible();
  await expect(page.getByRole("button", { name: "Rerun Simulation" })).toBeVisible();
  await expect(page.getByText("Status: completed")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Action success")).toBeVisible();
  await expect(page.getByText("DOM action coverage")).toBeVisible();
  await expect(page.getByText("task completed")).toBeVisible();
  await expect(page.getByText("cart.prepare")).toBeVisible();
});
