import { expect, test } from "@playwright/test";

import { lastAnswer, STATE, watchConsole } from "./helpers";

// Smoke tests of the main flows against the real backend and the configured
// model (Gemini, or the local / extractive fallback when there is no key).

test.describe("visitor", () => {
  test("landing page renders and nothing moves until Start tour", async ({ page }) => {
    const console = watchConsole(page);
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Placement answers, with the source attached");
    await expect(page.locator('[data-tour="landing-answer"]')).toContainText("dream exception");
    // Manual by default: only the Start button is on screen, no tour bar.
    await expect(page.getByRole("button", { name: "Start tour" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Guided tour" })).toHaveCount(0);
    // Evidence numbers come from the published results file.
    await expect(page.locator("#evidence dd").first()).toHaveText(/\d+%/);
    console.expectClean();
  });

  test("demo student button logs in and lands on the dashboard", async ({ page }) => {
    const console = watchConsole(page);
    await page.goto("/login");
    await page.locator('[data-tour="demo-student"]').click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.locator('[data-tour="dashboard-eligibility"]')).toContainText("companies on campus");
    console.expectClean();
  });

  test("app pages redirect to login without a session", async ({ page }) => {
    await page.goto("/eligibility");
    await expect(page).toHaveURL(/\/login\?next=%2Feligibility/);
  });

  test("unknown pages show the 404 page", async ({ page }) => {
    await page.goto("/no-such-page");
    await expect(page.getByText("This page does not exist")).toBeVisible();
  });
});

test.describe("student", () => {
  test.use({ storageState: STATE.student });

  test("ask: cited answer with sources and pipeline steps", async ({ page }) => {
    const console = watchConsole(page);
    await page.goto("/ask");
    await page.locator('[data-tour="ask-example-policy"]').click();
    const answer = await lastAnswer(page);
    await expect(answer).toHaveAttribute("data-status", "done");
    await expect(answer.locator(".cite-chip").first()).toBeVisible();
    await expect(answer.locator('[data-tour="source-cards"]')).toContainText("Placement Policy");
    await expect(answer.locator('[data-tour="provider-badge"]')).toBeVisible();
    console.expectClean();
  });

  test("ask: a question outside the documents is refused", async ({ page }) => {
    await page.goto("/ask");
    await page.locator('[data-tour="ask-example-unanswerable"]').click();
    const answer = await lastAnswer(page);
    await expect(answer).toContainText("Not in the documents");
  });

  test("ask: a prompt-injection attempt is blocked", async ({ page }) => {
    await page.goto("/ask");
    await page.locator('[data-tour="ask-example-injection"]').click();
    const answer = await lastAnswer(page);
    await expect(answer).toContainText("Blocked by the input guard");
    await expect(answer.locator('[data-tour="source-cards"]')).toHaveCount(0);
  });

  test("eligibility: a failing criterion is shown with its reason", async ({ page }) => {
    const console = watchConsole(page);
    await page.goto("/eligibility?company=orbitpay");
    const result = page.locator('[data-tour="eligibility-result"]');
    await expect(result).toContainText("Not eligible");
    await expect(result.locator('[data-tour="eligibility-criteria"]')).toContainText("CGPA");
    console.expectClean();
  });

  test("resume match: score, skills and the PII notice", async ({ page }) => {
    const console = watchConsole(page);
    await page.goto("/resume?company=nimbusware");
    await page.locator('[data-tour="resume-demo"]').click();
    await expect(page.locator('[data-tour="resume-text"]')).not.toHaveValue("");
    await page.locator('[data-tour="resume-match-button"]').click();
    await expect(page.locator('[data-tour="match-ring"]')).toContainText("%");
    await expect(page.locator('[data-tour="skill-chips"]').first()).toBeVisible();
    await expect(page.locator('[data-tour="pii-notice"]')).toContainText("removed");
    console.expectClean();
  });

  test("prep agent: recovers from a failed step and saves only after approval", async ({ page }) => {
    const console = watchConsole(page);
    await page.goto("/agent?company=nimbusware&fault=retrieve_process");
    await page.locator('[data-tour="agent-start"]').click();
    const dialog = page.locator('[data-tour="approval-dialog"]');
    await expect(dialog).toBeVisible({ timeout: 180_000 });
    await expect(page.locator('[data-tour="agent-timeline"]')).toContainText("Recovered after retry");
    await page.locator('[data-tour="approval-approve"]').click();
    await expect(page.locator('[data-tour="agent-confirmation"]')).toContainText("Approved");
    await expect(page.locator('[data-tour="agent-state"]')).toContainText("Approved and saved");
    console.expectClean();
  });

  test("applications tracker lists the saved application", async ({ page }) => {
    await page.goto("/applications");
    await expect(page.locator('[data-tour="applications-table"]')).toContainText("Nimbusware");
  });

  test("a coordinator page shows 403 to a student", async ({ page }) => {
    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "This page is not part of your role" })).toBeVisible();
    await expect(page.getByRole("main")).toHaveCount(1);
  });
});

test.describe("coordinator", () => {
  test.use({ storageState: STATE.coordinator });

  test("documents: an invalid file is rejected with a reason", async ({ page }) => {
    const console = watchConsole(page);
    await page.goto("/documents");
    await page.locator('[data-tour="upload-demo-invalid"]').click();
    await expect(page.locator('[data-tour="upload-error"]')).toContainText(".md, .txt and .pdf");
    console.expectClean([415]);
  });

  test("analytics and evaluation pages load real data", async ({ page }) => {
    const console = watchConsole(page);
    await page.goto("/analytics");
    await expect(page.locator('[data-tour="analytics-totals"]')).toBeVisible();
    await expect(page.locator('[data-tour="analytics-top"]')).toBeVisible();
    await page.goto("/evaluation");
    await expect(page.locator('[data-tour="eval-headlines"]')).toContainText("%");
    await expect(page.locator('[data-tour="eval-tests"]')).toContainText("Passed");
    console.expectClean();
  });

  test("security: the injection check runs live and reports protected", async ({ page }) => {
    await page.goto("/security");
    await page.locator('[data-tour="security-injection-try"]').click();
    await expect(page.locator('[data-tour="security-injection-result"]')).toContainText("Protected");
  });
});

test.describe("guided tour", () => {
  test("manual mode: Start, Next, Space pauses, Back, Exit", async ({ page }) => {
    const console = watchConsole(page);
    await page.goto("/");
    await page.getByRole("button", { name: "Start tour" }).click();
    const bar = page.getByRole("region", { name: "Guided tour" });
    await expect(bar).toContainText("1 / ");
    await expect(bar).toHaveAttribute("data-phase", "ready");
    // Manual: it stays on step 1 until Next.
    await page.waitForTimeout(4000);
    await expect(bar).toContainText("1 / ");
    await page.keyboard.press("ArrowRight");
    await expect(bar).toContainText("2 / ");
    await expect(bar).toContainText("Proves: RAG: answers carry numbered citations");
    await page.keyboard.press("Space");
    await expect(bar.getByRole("button", { name: "Play" })).toBeVisible();
    await page.keyboard.press("Space");
    await expect(bar.getByRole("button", { name: "Pause" })).toBeVisible();
    await page.keyboard.press("ArrowLeft");
    await expect(bar).toContainText("1 / ");
    // State survives a reload.
    await page.reload();
    await expect(page.getByRole("region", { name: "Guided tour" })).toContainText("1 / ");
    await page.getByRole("button", { name: "Exit tour" }).click();
    await expect(page.getByRole("region", { name: "Guided tour" })).toHaveCount(0);
    console.expectClean();
  });
});
