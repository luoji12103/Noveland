import { expect, test, type Page } from "@playwright/test";

const worldOneId = "10000000-0000-4000-8000-000000000001";
const seedConversationId = "76000000-0000-4000-8000-000000000001";

test.describe.configure({ timeout: 60000 });
test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  const response = await request.get("http://127.0.0.1:3207/__mock/health");
  expect(response.ok()).toBe(true);
  const health = await response.json();
  expect(health.state_isolation?.mode).toBe("single_worker_serial");
});

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

test("redirects unauthenticated player visitors to login", async ({ page }) => {
  await page.goto(`/worlds/${worldOneId}/player`);

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
  await Promise.all([
    page.waitForURL(/\/agents\/[0-9a-f-]+$/),
    page.getByRole("button", { name: "Create agent" }).click(),
  ]);
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
  const [importResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/api/world-compositions/import"),
    ),
    page.getByRole("button", { name: "Import as new world" }).click(),
  ]);
  expect(importResponse.ok()).toBe(true);

  await expect(page).toHaveURL(/\/worlds\/[0-9a-f-]+$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { level: 1, name: "Imported World" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText(`${importedSlug} - Active`)).toBeVisible();
});

test("world admin manages workspace pages and conversations", async ({ page }) => {
  test.setTimeout(300_000);
  await signIn(page);

  await page.goto(`/worlds/${worldOneId}`);
  const sceneKey = `scene-${Date.now()}`;
  await page.getByPlaceholder("scene-key").fill(sceneKey);
  await page.getByPlaceholder("Scene name").fill("E2E Scene");
  const [sceneResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/api/worlds/${worldOneId}/scenes`),
    ),
    page.getByRole("button", { name: "Create scene" }).click(),
  ]);
  expect(sceneResponse.ok()).toBe(true);
  await expect(sceneResponse.json()).resolves.toMatchObject({
    scene_key: sceneKey,
    name: "E2E Scene",
  });
  await expect(page.getByText("Scene created.")).toBeVisible({ timeout: 15_000 });

  await page.getByPlaceholder("Search email or display name").fill("candidate");
  await page.getByRole("button", { name: "Search users" }).click();
  await expect(page.getByRole("heading", { level: 3, name: "Candidate", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Set world admin" }).click();
  await expect(page.getByText("candidate@example.test - world_admin").first()).toBeVisible();

  await page.getByPlaceholder("Speed multiplier").fill("2");
  const [resumeResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/api/worlds/${worldOneId}/clock/resume`),
    ),
    page.getByRole("button", { name: "Resume with multiplier" }).click(),
  ]);
  expect(resumeResponse.ok()).toBe(true);
  await expect(resumeResponse.json()).resolves.toMatchObject({ status: "running" });
  await expect(page.getByText("Clock resumed.")).toBeVisible({ timeout: 15_000 });
  const [pauseResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/api/worlds/${worldOneId}/clock/pause`),
    ),
    page.getByRole("button", { name: "Pause clock" }).click(),
  ]);
  expect(pauseResponse.ok()).toBe(true);
  await expect(pauseResponse.json()).resolves.toMatchObject({ status: "paused" });
  await expect(page.getByText("Clock paused.")).toBeVisible({ timeout: 15_000 });
  await page.getByPlaceholder("2030-01-01T00:00:00Z").fill("2030-01-01T00:00:00Z");
  const [skipResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/api/worlds/${worldOneId}/clock/skip`),
    ),
    page.getByRole("button", { name: "Skip clock" }).click(),
  ]);
  expect(skipResponse.ok()).toBe(true);
  await expect(skipResponse.json()).resolves.toMatchObject({
    current_world_time: "2030-01-01T00:00:00.000Z",
  });
  await expect(page.getByText("Clock skipped.")).toBeVisible({ timeout: 15_000 });

  const [snapshotResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/api/worlds/${worldOneId}/snapshots`),
    ),
    page.getByRole("button", { name: "Create snapshot" }).click(),
  ]);
  expect(snapshotResponse.ok()).toBe(true);
  await expect(snapshotResponse.json()).resolves.toMatchObject({ world_id: worldOneId });
  await expect(page.getByText("Snapshot created.")).toBeVisible({ timeout: 15_000 });

  const scheduleRules = page.getByRole("region", { name: "Schedule rules" });
  await scheduleRules.getByPlaceholder("rule-key").fill(`rule-${Date.now()}`);
  await scheduleRules.getByPlaceholder("Rule name").fill("E2E Rule");
  await scheduleRules.getByRole("button", { name: "Create schedule rule" }).click();
  await expect(page.getByText("Schedule rule created.")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "E2E Rule" })).toBeVisible({
    timeout: 15_000,
  });

  await page.goto(`/worlds/${worldOneId}/agents`);
  await page.getByPlaceholder("agent-key").fill(`agent-${Date.now()}`);
  await page.getByPlaceholder("Display name").fill("E2E Agent");
  await Promise.all([
    page.waitForURL(/\/worlds\/[0-9a-f-]+\/agents\/[0-9a-f-]+$/, { timeout: 15_000 }),
    page.getByRole("button", { name: "Create agent" }).click(),
  ]);
  await expect(page.getByRole("heading", { name: "Agent builder" })).toBeVisible();

  await page.getByPlaceholder("Persona text").fill("E2E persona");
  const [personaResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "PATCH" &&
        response.url().includes(`/api/worlds/${worldOneId}/agents/`) &&
        response.url().endsWith("/persona"),
    ),
    page.getByRole("button", { name: "Save persona" }).click(),
  ]);
  expect(personaResponse.ok()).toBe(true);
  await expect(personaResponse.json()).resolves.toMatchObject({
    persona_text: "E2E persona",
  });
  await page.getByPlaceholder("Observation").fill("E2E observation");
  await page.getByRole("button", { name: "Add observation" }).click();
  await expect(page.getByText("Observation added.")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/E2E observation/)).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "Refresh observations" }).click();
  await expect(page.getByText("Observations refreshed.")).toBeVisible();

  await page.getByPlaceholder("Calendar title").fill("E2E Calendar");
  await page.getByPlaceholder("2030-01-01T08:00:00Z").fill("2030-01-01T08:00:00Z");
  await page.getByRole("button", { name: "Create calendar entry" }).click();
  await expect(page.getByText("Calendar entry created.")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "E2E Calendar" })).toBeVisible({
    timeout: 15_000,
  });

  await expect(page.getByText("Long-term memory is written asynchronously by runtime. This view is read-only.")).toBeVisible();
  await page.getByRole("button", { name: "Refresh memory profile" }).click();
  await expect(page.getByText("Memory profile snapshot refreshed.")).toBeVisible();

  await page.getByPlaceholder("Manual run prompt").fill("Say hello from runtime");
  await page.getByRole("button", { name: "Run agent" }).click();
  await expect(page.getByText("Agent run completed.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "succeeded" }).first()).toBeVisible();
  await page.getByPlaceholder("Search memory context").fill("Run output");
  await page.getByRole("button", { name: "Search memory" }).click();
  await expect(page.getByText("Memory search returned 1 item(s).")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Run output for/ })).toBeVisible();

  await page.goto(`/worlds/${worldOneId}/conversations`);
  await page.getByPlaceholder("session-key").fill(`manual-${Date.now()}`);
  await page.getByPlaceholder("Conversation title").fill("Manual Chain");
  await page.getByPlaceholder("Objective").fill("Let agents exchange one reply.");
  await page.getByPlaceholder("Opening prompt").fill("Start the scene.");
  const [manualConversationResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/api/worlds/${worldOneId}/conversations`),
    ),
    page.getByRole("button", { name: "Create conversation" }).click(),
  ]);
  expect(manualConversationResponse.ok()).toBe(true);
  await expect(page.getByRole("heading", { level: 1, name: "Manual Chain" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page).toHaveURL(/\/conversations\/[0-9a-f-]+$/, { timeout: 15_000 });
  await page.getByLabel(/Guide/).check();
  const [manualParticipantsResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "PUT" &&
        response.url().endsWith("/participants"),
    ),
    page.getByRole("button", { name: "Save participants" }).click(),
  ]);
  expect(manualParticipantsResponse.ok()).toBe(true);
  await expect(manualParticipantsResponse.json()).resolves.toEqual(
    expect.arrayContaining([expect.objectContaining({ is_enabled: true })]),
  );
  await expect(page.getByText("Participants saved.")).toBeVisible({ timeout: 15_000 });
  await page.getByPlaceholder("Seed text").fill("Operator starts.");
  const [seedResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" && response.url().endsWith("/seed"),
    ),
    page.getByRole("button", { name: "Seed conversation" }).click(),
  ]);
  expect(seedResponse.ok()).toBe(true);
  await expect(seedResponse.json()).resolves.toMatchObject({
    output_text: "Operator starts.",
  });
  await expect(page.getByText("Operator starts.")).toBeVisible({ timeout: 15_000 });
  const [advanceResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" && response.url().endsWith("/advance"),
    ),
    page.getByRole("button", { name: "Advance one turn" }).click(),
  ]);
  expect(advanceResponse.ok()).toBe(true);
  await expect(advanceResponse.json()).resolves.toMatchObject({
    turn: expect.objectContaining({ output_text: expect.stringContaining("replies to") }),
  });
  await expect(page.getByText(/replies to/)).toBeVisible({ timeout: 15_000 });
  const [narrativeResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith("/narrative/generate"),
    ),
    page.getByRole("button", { name: "Generate summary + chapter" }).click(),
  ]);
  expect(narrativeResponse.ok()).toBe(true);
  await expect(narrativeResponse.json()).resolves.toEqual(
    expect.arrayContaining([expect.objectContaining({ title: expect.stringMatching(/Manual Chain summary/i) })]),
  );
  await expect(page.getByText("Conversation narrative generated.")).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("heading", { name: /Manual Chain summary/i })).toBeVisible({
    timeout: 15_000,
  });

  await page.goto(`/worlds/${worldOneId}/conversations`);
  await page.getByPlaceholder("session-key").fill(`auto-${Date.now()}`);
  await page.getByPlaceholder("Conversation title").fill("Auto Dialogue");
  await page.locator('select[name="mode"]').selectOption("auto_dialogue");
  await page.getByPlaceholder("Opening prompt").fill("Begin auto dialogue.");
  const [autoConversationResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().endsWith(`/api/worlds/${worldOneId}/conversations`),
    ),
    page.getByRole("button", { name: "Create conversation" }).click(),
  ]);
  expect(autoConversationResponse.ok()).toBe(true);
  await expect(page.getByRole("heading", { level: 1, name: "Auto Dialogue" })).toBeVisible({
    timeout: 15_000,
  });
  await page.getByLabel(/Guide/).check();
  const [autoParticipantsResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "PUT" &&
        response.url().endsWith("/participants"),
    ),
    page.getByRole("button", { name: "Save participants" }).click(),
  ]);
  expect(autoParticipantsResponse.ok()).toBe(true);
  const [startResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" && response.url().endsWith("/start"),
    ),
    page.getByRole("button", { name: "Start auto dialogue" }).click(),
  ]);
  expect(startResponse.ok()).toBe(true);
  await expect(startResponse.json()).resolves.toMatchObject({ status: "running" });
  await expect(page.getByText("Conversation started.")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/replies to/)).toBeVisible({ timeout: 15_000 });

  await page.goto(`/worlds/${worldOneId}/narrative`);
  await page.getByPlaceholder("Artifact title").fill("E2E Artifact");
  await page.getByPlaceholder("Artifact content").fill("Artifact body");
  await page.getByRole("button", { name: "Create artifact" }).click();
  await expect(page.getByText("Narrative artifact created.")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "E2E Artifact" })).toBeVisible({
    timeout: 15_000,
  });

  await page.goto("/admin/runtime");
  await expect(page.getByRole("heading", { name: "External tool policy" })).toBeVisible();
  await expect(page.getByText("policy_only")).toBeVisible();
  await expect(page.getByText("External tool policy is defined for audit")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Scale readiness" })).toBeVisible();
  await expect(page.getByText("database_indexes - ok")).toBeVisible();
  await expect(page.getByText("realtime_fanout - ok")).toBeVisible();
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

  await page.goto("/admin/memory-backends");
  await expect(page.getByRole("heading", { name: "Primary Mem0" })).toBeVisible();
  await expect(page.getByText("Jobs: 1 / failed 1")).toBeVisible();
  await expect(page.getByText("Error: mock backend timeout")).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry job" })).toBeEnabled({
    timeout: 15_000,
  });
  const [retryResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().includes("/api/memory-write-jobs/") &&
        response.url().endsWith("/retry"),
    ),
    page.getByRole("button", { name: "Retry job" }).click(),
  ]);
  expect(retryResponse.ok()).toBe(true);
  await expect(retryResponse.json()).resolves.toMatchObject({
    status: "pending",
    last_error: null,
  });
  await expect(page.getByText("Memory write job queued for retry.")).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText("Jobs: 1 / failed 0")).toBeVisible({ timeout: 15_000 });
});

test("publication blockers are surfaced and blocked drafts stay out of the reader", async ({ page }) => {
  await signIn(page);

  await page.goto(`/worlds/${worldOneId}/narrative`);
  const blockerDraft = page
    .locator("article")
    .filter({ has: page.getByRole("heading", { name: "Publication blocker draft" }) });
  await blockerDraft.getByRole("button", { name: "Publish" }).click();
  await expect(
    page.getByText("Narrative publication blocked by continuity review (fail)"),
  ).toBeVisible();
  await expect(blockerDraft.getByText(/world_summary - world - draft/)).toBeVisible();

  const initialDraft = page
    .locator("article")
    .filter({ has: page.getByRole("heading", { name: "Initial artifact" }) });
  await initialDraft.getByRole("button", { name: "Publish" }).click();
  await expect(page.getByText("Narrative artifact published.")).toBeVisible();
  await expect(initialDraft.getByText("Publication gate: pass (0 issues)")).toBeVisible();
  await initialDraft.getByRole("button", { name: "Unpublish" }).click();
  await expect(page.getByText("Narrative artifact unpublished.")).toBeVisible({
    timeout: 15_000,
  });
  await expect(initialDraft.getByText(/agent_note - Guide - draft/)).toBeVisible({
    timeout: 15_000,
  });
  await expect(initialDraft.getByRole("button", { name: "Publish" })).toBeVisible();

  await Promise.all([
    page.waitForURL(/\/login$/),
    page.getByRole("button", { name: "Log out" }).click(),
  ]);
  await signIn(page, "member@example.test");
  await page.goto(`/worlds/${worldOneId}/reader?q=Publication%20blocker`);
  await expect(page.getByRole("heading", { name: "Narrative reader" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "No readable artifacts" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Publication blocker draft" })).toHaveCount(0);
});

test("reader honors search, source, status, and published ordering filters", async ({ page }) => {
  await signIn(page, "member@example.test");

  await page.goto(`/worlds/${worldOneId}/reader?order_by=published_at`);
  await expect(page.getByRole("heading", { name: "Narrative reader" })).toBeVisible();
  const links = page.locator('section[aria-labelledby="reader-list-title"] article h3 a');
  await expect(links.first()).toHaveText("Published agent field note");
  await expect(links.nth(1)).toHaveText("Seed conversation summary");

  await page.goto(`/worlds/${worldOneId}/reader?q=summary&source_kind=conversation&order_by=published_at`);
  await expect(page.getByRole("link", { name: "Seed conversation summary" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Published agent field note" })).toHaveCount(0);

  await page.goto(`/worlds/${worldOneId}/reader?source_kind=agent&order_by=published_at`);
  await expect(page.getByRole("link", { name: "Published agent field note" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Seed conversation summary" })).toHaveCount(0);

  await page.goto(`/worlds/${worldOneId}/reader?publication_status=draft&q=Publication%20blocker`);
  await expect(page.getByRole("heading", { name: "No readable artifacts" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Publication blocker draft" })).toHaveCount(0);
});

test("reader playback renders conversation turns through safe media", async ({ page }) => {
  await signIn(page, "member@example.test");

  await page.goto(`/worlds/${worldOneId}/reader/conversations/${seedConversationId}/playback`);
  await expect(page.getByRole("heading", { name: "Playback", exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Turn 2/ }).click();
  await expect(page.getByText("Guide replies to seed the conversation.")).toBeVisible();
  await expect(page.getByLabel("Reader-safe scene media")).toBeVisible();
  await expect(page.getByLabel("Turn audio")).toHaveAttribute(
    "src",
    `/api/worlds/${worldOneId}/reader/media/objects/76810000-0000-4000-8000-000000000002/download`,
  );

  const pageText = await page.locator("body").innerText();
  expect(pageText).not.toMatch(/storage_uri|media:\/\/|base64|raw_prompt|raw_output|api_key|secret/i);

  await page.getByRole("button", { name: /Turn 1/ }).click();
  await expect(page.getByText("No reader-visible image for this turn.")).toBeVisible();
  await expect(page.getByText("No reader-visible audio for this turn.")).toBeVisible();
});

test("player interactions reuse existing player records", async ({ page }) => {
  await signIn(page, "member@example.test");

  await page.goto(`/worlds/${worldOneId}/player`);
  await expect(page.getByRole("heading", { name: "Player interactions" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Member Player" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Festival prep" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Club room notice" })).toBeVisible();
  await expect(page.getByText("0 relationship update(s)")).toBeVisible();

  await page.getByPlaceholder("choice-key").fill(`member-route-${Date.now()}`);
  await page.getByPlaceholder("Choice prompt").fill("Help with route preparations?");
  await page.getByPlaceholder("Selected option").fill("Stay and help.");
  await page.getByRole("button", { name: "Preview choice" }).click();
  await expect(page.getByText("Choice consequence preview loaded.")).toBeVisible();
  await page.getByRole("button", { name: "Record choice" }).click();
  await expect(page.getByText("Player choice recorded.")).toBeVisible();

  await page.getByPlaceholder("Intervention prompt").fill("Contact the guide after class.");
  await page.getByRole("button", { name: "Submit intervention" }).click();
  await expect(page.getByText("Intervention recorded.")).toBeVisible();

  const pageText = await page.locator("body").innerText();
  expect(pageText).not.toMatch(/storage_uri|media:\/\/|base64|raw_prompt|raw_output|api_key|secret/i);
});

test("release gate blockers are enforced by the workspace backend contract", async ({ page }) => {
  await signIn(page);

  await page.goto(`/worlds/${worldOneId}`);
  const releaseForm = page
    .locator("form")
    .filter({ has: page.getByRole("heading", { name: "Release profile" }) });

  await releaseForm.locator('select[name="status"]').selectOption("ready");
  await releaseForm.locator('textarea[name="checklist"]').fill(
    JSON.stringify({
      worldline_id: "11000000-0000-4000-8000-000000000002",
      evidence_refs: [],
      warning_decisions: { style: "accepted" },
    }),
  );
  await releaseForm.getByRole("button", { name: "Save release profile" }).click();
  await expect(page.getByText(/missing_beta_checklist: Run a beta checklist/)).toBeVisible();
  await expect(page.getByText(/missing_long_run_eval: Run a long-run eval/)).toBeVisible();

  await releaseForm.locator('textarea[name="checklist"]').fill(
    JSON.stringify({
      worldline_id: "11000000-0000-4000-8000-000000000001",
      evidence_refs: [
        {
          kind: "snapshot",
          id: "00000000-0000-4000-8000-000000000000",
          label: "stale snapshot",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "worldline",
          id: "11000000-0000-4000-8000-000000000001",
          label: "primary worldline",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "publication",
          id: "73500000-0000-4000-8000-000000000001",
          label: "seed publication",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "continuity_review",
          id: "84300000-0000-4000-8000-000000000001",
          label: "seed continuity review",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "beta_checklist",
          id: "84100000-0000-4000-8000-000000000001",
          label: "seed checklist",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "long_run_eval",
          id: "83800000-0000-4000-8000-000000000001",
          label: "seed long-run eval",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
      ],
      warning_decisions: { style: "accepted" },
    }),
  );
  await releaseForm.getByRole("button", { name: "Save release profile" }).click();
  await expect(page.getByText(/unresolved_required_evidence_refs/)).toBeVisible();

  await releaseForm.locator('textarea[name="checklist"]').fill(
    JSON.stringify({
      worldline_id: "11000000-0000-4000-8000-000000000001",
      evidence_refs: [
        {
          kind: "snapshot",
          id: "74500000-0000-4000-8000-000000000001",
          label: "seed snapshot",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "worldline",
          id: "11000000-0000-4000-8000-000000000001",
          label: "primary worldline",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "publication",
          id: "73500000-0000-4000-8000-000000000001",
          label: "seed publication",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "continuity_review",
          id: "84300000-0000-4000-8000-000000000001",
          label: "seed continuity review",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "beta_checklist",
          id: "84100000-0000-4000-8000-000000000001",
          label: "seed checklist",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
        {
          kind: "long_run_eval",
          id: "83800000-0000-4000-8000-000000000001",
          label: "seed long-run eval",
          worldline_id: "11000000-0000-4000-8000-000000000001",
        },
      ],
    }),
  );
  await releaseForm.getByRole("button", { name: "Save release profile" }).click();
  await expect(page.getByText(/Gate ready - allowed - blockers 0 - warnings 1/)).toBeVisible();

  await releaseForm.locator('select[name="status"]').selectOption("released");
  await releaseForm.getByRole("button", { name: "Save release profile" }).click();

  await expect(
    page.getByText(/release_launch_gate_missing: Released status is blocked/),
  ).toBeVisible();
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
  const summaryLink = page.getByRole("link", { name: "Seed conversation summary" }).first();
  await expect(summaryLink).toBeVisible();
  await Promise.all([
    page.waitForURL(/\/reader\/[0-9a-f-]+$/),
    summaryLink.click(),
  ]);
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
