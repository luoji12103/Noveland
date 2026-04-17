import { expect, test, type Page } from "@playwright/test";

test("redirects unauthenticated visitors to login", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Sign in to Noveland" })).toBeVisible();
});

test("renders the login form", async ({ page }) => {
  await page.goto("/login");

  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("signs in and shows the protected dashboard", async ({ page }) => {
  await signIn(page);

  await expect(page).toHaveURL("/");
  await expect(page.getByRole("heading", { name: "World management console" })).toBeVisible();
  await expect(page.getByText("Admin - admin@example.test")).toBeVisible();
  await expect(page.getByText("platform_admin")).toBeVisible();
  await expect(page.getByRole("heading", { name: "First World" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "World clock" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Replay and snapshots" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent memory" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Runtime control" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Provider profiles" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent runs" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Narrative artifacts" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Guide", exact: true })).toBeVisible();
  await expect(page.getByText("admin@example.test - world_admin")).toBeVisible();
});

test("redirects already authenticated users away from login", async ({ page }) => {
  await signIn(page);

  await page.goto("/login");

  await expect(page).toHaveURL("/");
});

test("logs out and returns to login", async ({ page }) => {
  await signIn(page);

  await page.getByRole("button", { name: "Log out" }).click();

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Sign in to Noveland" })).toBeVisible();
});

test("platform admin creates a world", async ({ page }) => {
  await signIn(page);

  await page.getByPlaceholder("world-slug").fill(`e2e-world-${Date.now()}`);
  await page.getByPlaceholder("World name").fill("E2E World");
  await page.getByRole("button", { name: "Create world" }).click();

  await expect(page.getByRole("heading", { name: "E2E World" })).toBeVisible();
});

test("world admin manages scenes agents and memberships", async ({ page }) => {
  await signIn(page);

  await page.getByPlaceholder("scene-key").fill(`scene-${Date.now()}`);
  await page.getByPlaceholder("Scene name").fill("E2E Scene");
  await page.getByRole("button", { name: "Create scene" }).click();
  await expect(page.getByRole("heading", { name: "E2E Scene" })).toBeVisible();

  await page.getByPlaceholder("agent-key").fill(`agent-${Date.now()}`);
  await page.getByPlaceholder("Display name", { exact: true }).fill("E2E Agent");
  await page.getByRole("button", { name: "Create agent" }).click();
  await expect(page.getByRole("heading", { name: "E2E Agent" })).toBeVisible();

  await page.getByPlaceholder("Search email or display name").fill("candidate");
  await page.getByRole("button", { name: "Search users" }).click();
  await expect(page.getByRole("heading", { name: "Candidate" })).toBeVisible();
  await page.getByRole("button", { name: "Set world admin" }).click();
  await expect(page.getByText("candidate@example.test - world_admin").first()).toBeVisible();

  await page.getByRole("button", { name: "Deactivate scene" }).last().click();
  await expect(page.getByText(/E2E Scene[\s\S]*Inactive/)).toBeVisible();
  await page.getByRole("button", { name: "Deactivate agent" }).last().click();
  await expect(page.getByText(/E2E Agent[\s\S]*Disabled/)).toBeVisible();

  await page.getByPlaceholder("Speed multiplier").fill("2");
  await page.getByRole("button", { name: "Resume clock" }).click();
  await expect(page.getByText("Clock resumed.")).toBeVisible();
  await page.getByRole("button", { name: "Pause clock" }).click();
  await expect(page.getByText("Clock paused.")).toBeVisible();
  await page.getByPlaceholder("2030-01-01T00:00:00Z").fill("2030-01-01T00:00:00Z");
  await page.getByRole("button", { name: "Skip clock" }).click();
  await expect(page.getByText("Clock skipped.")).toBeVisible();

  await page.getByRole("button", { name: "Create snapshot" }).click();
  await expect(page.getByText("Snapshot created.")).toBeVisible();
  await expect(page.getByText(/Latest snapshot covers sequence/)).toBeVisible();

  await page.getByPlaceholder("rule-key").fill(`rule-${Date.now()}`);
  await page.getByPlaceholder("Rule name").fill("E2E Rule");
  await page.getByRole("button", { name: "Create schedule rule" }).click();
  await expect(page.getByRole("heading", { name: "E2E Rule" })).toBeVisible();

  await page.getByPlaceholder("Calendar title").fill("E2E Calendar");
  await page.getByPlaceholder("Calendar start").fill("2030-01-01T08:00:00Z");
  await page.getByRole("button", { name: "Create calendar entry" }).click();
  await expect(page.getByRole("heading", { name: "E2E Calendar" })).toBeVisible();

  await page.getByPlaceholder("Memory content").fill("E2E memory");
  await page.getByPlaceholder("[1,0,0]").fill("[1,0,0]");
  await page.getByRole("button", { name: "Add memory item" }).click();
  await expect(page.getByRole("heading", { name: "E2E memory" })).toBeVisible();
  await page.getByPlaceholder("Search embedding").fill("[1,0,0]");
  await page.getByRole("button", { name: "Search memory" }).click();
  await expect(page.getByText(/score/)).toBeVisible();

  await page.getByPlaceholder("Persona text").fill("E2E persona");
  await page.getByRole("button", { name: "Save persona" }).click();
  await expect(page.getByText("Agent persona updated.")).toBeVisible();
  await page.getByPlaceholder("Observation").fill("E2E observation");
  await page.getByRole("button", { name: "Add observation" }).click();
  await expect(page.getByText("E2E observation")).toBeVisible();
  await page.getByRole("button", { name: "Refresh observations" }).click();
  await expect(page.getByText("Agent observations refreshed.")).toBeVisible();

  await page.getByRole("button", { name: "Start runtime" }).click();
  await expect(page.getByText("Runtime start requested.")).toBeVisible();

  await page.getByPlaceholder("profile-key").fill(`profile-${Date.now()}`);
  await page.getByPlaceholder("Profile name").fill("E2E Provider");
  await page.getByPlaceholder("https://api.example.test/v1").fill("https://api.example.test/v1");
  await page.getByPlaceholder("Model name").fill("gpt-e2e");
  await page.getByPlaceholder("api-key-ref").fill("openai-local");
  await page.getByRole("button", { name: "Create provider profile" }).click();
  await expect(page.getByRole("heading", { name: "E2E Provider" })).toBeVisible();

  await page.getByPlaceholder("Manual run prompt").fill("Say hello from runtime");
  await page.getByRole("button", { name: "Run agent" }).click();
  await expect(page.getByText("Agent run completed.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "succeeded" }).first()).toBeVisible();

  await page.getByPlaceholder("Artifact title").fill("E2E Artifact");
  await page.getByPlaceholder("Artifact content").fill("Artifact body");
  await page.getByRole("button", { name: "Create narrative artifact" }).click();
  await expect(page.getByRole("heading", { name: "E2E Artifact" })).toBeVisible();
});

test("world member sees read-only dashboard", async ({ page }) => {
  await signIn(page, "member@example.test");

  await expect(page.getByText("Read-only world access.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "First World" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "World clock" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Replay and snapshots" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Schedule rules" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent calendar" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent memory" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent persona and observations" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent runs" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Narrative artifacts" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save world" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Resume clock" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Create snapshot" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Add memory item" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Save persona" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Run agent" })).toHaveCount(0);
});

async function signIn(page: Page, email = "admin@example.test") {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL("/");
}
