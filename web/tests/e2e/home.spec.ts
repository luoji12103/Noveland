import { expect, test } from "@playwright/test";

test("loads the dashboard shell", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "World kernel standing by" })).toBeVisible();
  await expect(page.getByText("Health endpoint ready")).toBeVisible();
  await expect(page.getByText("Domain logic pending")).toBeVisible();
});
