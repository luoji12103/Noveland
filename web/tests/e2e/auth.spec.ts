import { expect, test, type Page } from "@playwright/test";

const worldOneId = "10000000-0000-4000-8000-000000000001";

test.describe.configure({ timeout: 60000 });

test("redirects unauthenticated visitors to login", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Sign in to Noveland" })).toBeVisible();
});

test("redirects unauthenticated reader visitors to login", async ({ page }) => {
  await page.goto(`/worlds/${worldOneId}/reader`);

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Sign in to Noveland" })).toBeVisible();
});

test("renders the login form", async ({ page }) => {
  await page.goto("/login");

  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("signs in and opens the world workspace", async ({ page }) => {
  await signIn(page);

  await expect(page).toHaveURL(/\/worlds$/);
  await expect(page.getByRole("heading", { level: 1, name: "Worlds" })).toBeVisible();
  await expect(page.getByText("Admin - admin@example.test")).toBeVisible();
  await expect(page.getByText("platform_admin")).toBeVisible();
  await expect(page.getByRole("heading", { name: "First World" })).toBeVisible();

  await page.goto(`/worlds/${worldOneId}`);
  await expect(page.getByRole("heading", { name: "World clock" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Replay and snapshots" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Schedule rules" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Members" })).toBeVisible();
  await expect(page.getByText("admin@example.test - world_admin")).toBeVisible();
});

test("redirects already authenticated users away from login", async ({ page }) => {
  await signIn(page);

  await page.goto("/login");

  await expect(page).toHaveURL(/\/worlds$/);
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

  await expect(page).toHaveURL(/\/worlds\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { level: 1, name: "E2E World" })).toBeVisible();
});

test("platform admin manages presets and world composition import/export", async ({ page }) => {
  await signIn(page);

  await page.goto("/admin/presets");
  await page.getByPlaceholder("preset-key").fill("storyteller");
  await page.getByPlaceholder("Preset name").fill("Storyteller");
  await page.getByPlaceholder("Description").fill("Narrative preset");
  await page.getByPlaceholder("Persona").fill("Writes clearly.");
  await page.getByRole("button", { name: "Create preset" }).click();
  await expect(page.getByRole("heading", { name: "Storyteller" })).toBeVisible();

  await page.goto(`/worlds/${worldOneId}/agents`);
  await page.locator('select[name="preset_id"]').selectOption({ label: "Storyteller" });
  await expect(page.getByText("Preset preview")).toBeVisible();
  await expect(page.getByText("Provider key: none")).toBeVisible();
  await page.getByPlaceholder("agent-key").fill(`preset-agent-${Date.now()}`);
  await page.getByPlaceholder("Display name").fill("Preset Agent");
  await page.getByRole("button", { name: "Create agent" }).click();
  await expect(page.getByText("Source preset: Storyteller (storyteller)")).toBeVisible();
  await expect(page.locator('textarea[name="persona_text"]')).toHaveValue("Writes clearly.");

  await page.goto(`/worlds/${worldOneId}`);
  await page.getByRole("button", { name: "Export composition" }).click();
  await expect(page.getByText("Composition exported.")).toBeVisible();
  const exportedComposition = await page.locator('textarea[readonly]').inputValue();
  expect(exportedComposition).toContain("\"preset_references\"");

  const importedSlug = `imported-${Date.now()}`;
  await page.getByPlaceholder("imported-world-slug").fill(importedSlug);
  await page.getByPlaceholder("Imported world name").fill("Imported World");
  await page.getByPlaceholder("Paste exported composition JSON").fill(exportedComposition);
  await page.getByRole("button", { name: "Import as new world" }).click();

  await expect(page).toHaveURL(/\/worlds\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { level: 1, name: "Imported World" })).toBeVisible();
});

test("world admin manages workspace pages and conversations", async ({ page }) => {
  await signIn(page);

  await page.goto(`/worlds/${worldOneId}`);
  await page.getByPlaceholder("scene-key").fill(`scene-${Date.now()}`);
  await page.getByPlaceholder("Scene name").fill("E2E Scene");
  await page.getByRole("button", { name: "Create scene" }).click();
  await expect(page.getByRole("heading", { name: "E2E Scene" })).toBeVisible();

  await page.getByPlaceholder("Search email or display name").fill("candidate");
  await page.getByRole("button", { name: "Search users" }).click();
  await expect(page.getByRole("heading", { name: "Candidate" })).toBeVisible();
  await page.getByRole("button", { name: "Set world admin" }).click();
  await expect(page.getByText("candidate@example.test - world_admin").first()).toBeVisible();

  await page.getByPlaceholder("Speed multiplier").fill("2");
  await page.getByRole("button", { name: "Resume with multiplier" }).click();
  await expect(page.getByText("Clock resumed.")).toBeVisible();
  await page.getByRole("button", { name: "Pause clock" }).click();
  await expect(page.getByText("Clock paused.")).toBeVisible();
  await page.getByPlaceholder("2030-01-01T00:00:00Z").fill("2030-01-01T00:00:00Z");
  await page.getByRole("button", { name: "Skip clock" }).click();
  await expect(page.getByText("Clock skipped.")).toBeVisible();

  await page.getByRole("button", { name: "Create snapshot" }).click();
  await expect(page.getByText("Snapshot created.")).toBeVisible();

  await page.getByPlaceholder("rule-key").fill(`rule-${Date.now()}`);
  await page.getByPlaceholder("Rule name").fill("E2E Rule");
  await page.getByRole("button", { name: "Create schedule rule" }).click();
  await expect(page.getByRole("heading", { name: "E2E Rule" })).toBeVisible();

  await page.goto(`/worlds/${worldOneId}/agents`);
  await page.getByPlaceholder("agent-key").fill(`agent-${Date.now()}`);
  await page.getByPlaceholder("Display name").fill("E2E Agent");
  await page.getByRole("button", { name: "Create agent" }).click();
  await expect(page).toHaveURL(/\/worlds\/[0-9a-f-]+\/agents\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: "Agent builder" })).toBeVisible();

  await page.getByPlaceholder("Persona text").fill("E2E persona");
  await page.getByRole("button", { name: "Save persona" }).click();
  await expect(page.getByText("Persona saved.")).toBeVisible();
  await page.getByPlaceholder("Observation").fill("E2E observation");
  await page.getByRole("button", { name: "Add observation" }).click();
  await expect(page.getByText("E2E observation")).toBeVisible();
  await page.getByRole("button", { name: "Refresh observations" }).click();
  await expect(page.getByText("Observations refreshed.")).toBeVisible();

  await page.getByPlaceholder("Calendar title").fill("E2E Calendar");
  await page.getByPlaceholder("2030-01-01T08:00:00Z").fill("2030-01-01T08:00:00Z");
  await page.getByRole("button", { name: "Create calendar entry" }).click();
  await expect(page.getByRole("heading", { name: "E2E Calendar" })).toBeVisible();

  await page.getByPlaceholder("Memory content").fill("E2E memory");
  await page.getByPlaceholder("[1,0,0]").fill("[1,0,0]");
  await page.getByRole("button", { name: "Add memory item" }).click();
  await expect(page.getByRole("heading", { name: "E2E memory" })).toBeVisible();

  await page.getByPlaceholder("Manual run prompt").fill("Say hello from runtime");
  await page.getByRole("button", { name: "Run agent" }).click();
  await expect(page.getByText("Agent run completed.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "succeeded" }).first()).toBeVisible();

  await page.goto(`/worlds/${worldOneId}/conversations`);
  await page.getByPlaceholder("session-key").fill(`manual-${Date.now()}`);
  await page.getByPlaceholder("Conversation title").fill("Manual Chain");
  await page.getByPlaceholder("Objective").fill("Let agents exchange one reply.");
  await page.getByPlaceholder("Opening prompt").fill("Start the scene.");
  await page.getByRole("button", { name: "Create conversation" }).click();
  await expect(page).toHaveURL(/\/conversations\/[0-9a-f-]+$/);
  await page.getByLabel(/Guide/).check();
  await page.getByRole("button", { name: "Save participants" }).click();
  await expect(page.getByText("Participants saved.")).toBeVisible();
  await page.getByPlaceholder("Seed text").fill("Operator starts.");
  await page.getByRole("button", { name: "Seed conversation" }).click();
  await expect(page.getByText("Operator starts.")).toBeVisible();
  await page.getByRole("button", { name: "Advance one turn" }).click();
  await expect(page.getByText(/replies to/)).toBeVisible();
  await page.getByRole("button", { name: "Generate summary + chapter" }).click();
  await expect(page.getByText("Conversation narrative generated.")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Manual Chain summary/i })).toBeVisible();

  await page.goto(`/worlds/${worldOneId}/conversations`);
  await page.getByPlaceholder("session-key").fill(`auto-${Date.now()}`);
  await page.getByPlaceholder("Conversation title").fill("Auto Dialogue");
  await page.locator('select[name="mode"]').selectOption("auto_dialogue");
  await page.getByPlaceholder("Opening prompt").fill("Begin auto dialogue.");
  await page.getByRole("button", { name: "Create conversation" }).click();
  await page.getByLabel(/Guide/).check();
  await page.getByRole("button", { name: "Save participants" }).click();
  await page.getByRole("button", { name: "Start auto dialogue" }).click();
  await expect(page.getByText("Conversation started.")).toBeVisible();
  await expect(page.getByText(/replies to/)).toBeVisible();

  await page.goto(`/worlds/${worldOneId}/narrative`);
  await page.getByPlaceholder("Artifact title").fill("E2E Artifact");
  await page.getByPlaceholder("Artifact content").fill("Artifact body");
  await page.getByRole("button", { name: "Create artifact" }).click();
  await expect(page.getByRole("heading", { name: "E2E Artifact" })).toBeVisible();

  await page.goto("/admin/runtime");
  await page.getByRole("button", { name: "Start runtime" }).click();
  await expect(page.getByText("Runtime start requested.")).toBeVisible();

  await page.goto("/admin/providers");
  await page.getByPlaceholder("profile-key").fill(`profile-${Date.now()}`);
  await page.getByPlaceholder("Profile name").fill("E2E Provider");
  await page.getByPlaceholder("https://api.example.test/v1").fill("https://api.example.test/v1");
  await page.getByPlaceholder("Model name").fill("gpt-e2e");
  await page.getByPlaceholder("api-key-ref").fill("openai-local");
  await page.getByRole("button", { name: "Create provider profile" }).click();
  await expect(page.getByRole("heading", { name: "E2E Provider" })).toBeVisible();
});

test("world member sees read-only workspace pages", async ({ page }) => {
  await signIn(page, "member@example.test");

  await page.goto(`/worlds/${worldOneId}`);
  await expect(page.getByText("Read-only world access.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "World clock" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Replay and snapshots" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save world" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Resume with multiplier" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Create snapshot" })).toHaveCount(0);

  await page.goto(`/worlds/${worldOneId}/conversations`);
  await expect(page.getByRole("heading", { name: "Create conversation" })).toHaveCount(0);

  await page.goto(`/worlds/${worldOneId}/narrative`);
  await expect(page.getByRole("button", { name: "Create artifact" })).toHaveCount(0);

  await page.goto(`/worlds/${worldOneId}/reader`);
  await expect(page.getByRole("heading", { name: "Narrative reader" })).toBeVisible();
  await page.getByRole("link", { name: "Seed conversation summary" }).click();
  await expect(page).toHaveURL(/\/reader\/[0-9a-f-]+$/);
  await expect(page.getByText("Summary for the seeded conversation.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open source conversation" })).toBeVisible();
});

async function signIn(page: Page, email = "admin@example.test") {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/worlds$/);
}
