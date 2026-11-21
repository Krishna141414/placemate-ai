import { expect, test, type Page } from "@playwright/test";

import { lastAnswer, STATE } from "./helpers";

// README / submission screenshots of the landing page and every app page, at
// desktop (1280x800) and mobile (390x844). Saved to ../screenshots/<device>/.
// Run with: npm run screenshots

function folder(projectName: string) {
  return projectName.endsWith("mobile") ? "mobile" : "desktop";
}

async function shot(page: Page, name: string, projectName: string, options: { fullPage?: boolean } = {}) {
  // Let reveals, count-ups and chart animations finish first.
  await page.waitForTimeout(2200);
  await page.screenshot({ path: `../screenshots/${folder(projectName)}/${name}.png`, fullPage: options.fullPage ?? false });
}

/** Toasts are useful in use but cover the top bar in a still image. */
async function waitForToasts(page: Page) {
  await expect(page.locator("[data-sonner-toast]")).toHaveCount(0, { timeout: 15_000 });
}

async function scrollTo(page: Page, selector: string) {
  await page.locator(selector).first().evaluate((el) => el.scrollIntoView({ block: "start" }));
  await page.waitForTimeout(400);
}

test.describe("visitor pages", () => {
  test("landing", async ({ page }, info) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await shot(page, "01-landing-hero", info.project.name);
    await scrollTo(page, '[data-tour="landing-problem"]');
    await shot(page, "02-landing-problem", info.project.name);
    await scrollTo(page, '[data-tour="landing-walkthrough"]');
    await shot(page, "03-landing-walkthrough", info.project.name);
    await scrollTo(page, "#how");
    await page.mouse.wheel(0, 300);
    await shot(page, "04-landing-pipeline", info.project.name);
    await scrollTo(page, "#evidence");
    await shot(page, "05-landing-evidence", info.project.name);
  });

  test("login and error pages", async ({ page }, info) => {
    await page.goto("/login");
    await expect(page.locator('[data-tour="demo-buttons"]')).toBeVisible();
    await shot(page, "06-login", info.project.name);
    await page.goto("/no-such-page");
    await shot(page, "24-not-found", info.project.name);
  });
});

test.describe("student pages", () => {
  test.use({ storageState: STATE.student });

  test("dashboard, ask, eligibility, resume", async ({ page }, info) => {
    await page.goto("/ask");
    await page.locator('[data-tour="ask-example-policy"]').click();
    const answer = await lastAnswer(page);
    await answer.evaluate((el) => el.scrollIntoView({ block: "start" }));
    await shot(page, "08-ask-cited-answer", info.project.name);
    await page.locator('[data-tour="ask-example-injection"]').click();
    const blocked = await lastAnswer(page);
    await blocked.evaluate((el) => el.scrollIntoView({ block: "start" }));
    await shot(page, "09-ask-injection-blocked", info.project.name);

    // After the questions, so the dashboard's recent questions are not empty on a fresh demo.
    await page.goto("/dashboard");
    await expect(page.locator('[data-tour="dashboard-eligibility"]')).toBeVisible();
    await shot(page, "07-dashboard", info.project.name);

    await page.goto("/eligibility?company=orbitpay");
    await expect(page.locator('[data-tour="eligibility-result"]')).toBeVisible();
    await shot(page, "10-eligibility", info.project.name);
    await page.goto("/eligibility?view=all");
    await expect(page.locator('[data-tour="eligibility-all"]')).toBeVisible();
    await shot(page, "11-eligibility-all", info.project.name);

    await page.goto("/resume?company=nimbusware");
    await page.locator('[data-tour="resume-demo"]').click();
    await expect(page.locator('[data-tour="resume-text"]')).not.toHaveValue("");
    await page.locator('[data-tour="resume-match-button"]').click();
    await expect(page.locator('[data-tour="match-result"]')).toBeVisible();
    await scrollTo(page, '[data-tour="match-result"]');
    await shot(page, "12-resume-match", info.project.name);
    await scrollTo(page, '[data-tour="pii-notice"]');
    await shot(page, "13-resume-pii-redaction", info.project.name);
  });

  test("prep agent and applications", async ({ page }, info) => {
    await page.goto("/agent?company=nimbusware&fault=retrieve_process");
    await page.locator('[data-tour="agent-start"]').click();
    await expect(page.locator('[data-tour="approval-dialog"]')).toBeVisible({ timeout: 180_000 });
    // Move the pointer off the dialog so no citation preview is open in the image.
    await page.mouse.move(1, 1);
    await page.waitForTimeout(400);
    await shot(page, "14-agent-approval", info.project.name);
    await page.locator('[data-tour="approval-approve"]').click();
    await expect(page.locator('[data-tour="agent-confirmation"]')).toBeVisible();
    await page.mouse.move(0, 0);
    await page.evaluate(() => window.scrollTo(0, 0));
    await waitForToasts(page);
    await shot(page, "15-agent-recovered-and-saved", info.project.name);

    await page.goto("/applications");
    await expect(page.locator('[data-tour="applications-table"]')).toBeVisible();
    await shot(page, "16-applications", info.project.name);
  });

  test("forbidden page and dark mode", async ({ page }, info) => {
    await page.goto("/documents");
    await expect(page.getByRole("heading", { name: "This page is not part of your role" })).toBeVisible();
    await shot(page, "25-forbidden", info.project.name);
    await page.emulateMedia({ colorScheme: "dark" });
    await page.addInitScript(() => window.localStorage.setItem("theme", "dark"));
    await page.goto("/dashboard");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await shot(page, "26-dashboard-dark", info.project.name);
  });
});

test.describe("coordinator pages", () => {
  test.use({ storageState: STATE.coordinator });

  test("documents, analytics, evaluation, security", async ({ page }, info) => {
    await page.goto("/documents");
    await page.locator('[data-tour="upload-demo-invalid"]').click();
    await expect(page.locator('[data-tour="upload-error"]')).toBeVisible();
    await waitForToasts(page);
    await shot(page, "17-documents-upload-rejected", info.project.name);

    await page.goto("/analytics");
    await expect(page.locator('[data-tour="analytics-totals"]')).toBeVisible();
    await shot(page, "18-analytics", info.project.name);
    await scrollTo(page, '[data-tour="analytics-unanswered"]');
    await shot(page, "19-analytics-unanswered", info.project.name);

    await page.goto("/evaluation");
    await expect(page.locator('[data-tour="eval-headlines"]')).toBeVisible();
    await shot(page, "20-evaluation", info.project.name);
    await scrollTo(page, '[data-tour="eval-chart"]');
    await shot(page, "21-evaluation-chart", info.project.name);

    await page.goto("/security");
    await page.locator('[data-tour="security-injection-try"]').click();
    await expect(page.locator('[data-tour="security-injection-result"]')).toBeVisible();
    await page.locator('[data-tour="security-pii-try"]').click();
    await expect(page.locator('[data-tour="security-pii-result"]')).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await shot(page, "22-security", info.project.name);
  });
});

test.describe("guided tour", () => {
  test("tour bar with spotlight", async ({ page }, info) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Start tour" }).click();
    const bar = page.getByRole("region", { name: "Guided tour" });
    await expect(bar).toHaveAttribute("data-phase", "ready");
    await page.keyboard.press("ArrowRight");
    await expect(bar).toContainText("2 / ");
    await expect(bar).toHaveAttribute("data-phase", "ready", { timeout: 30_000 });
    await shot(page, "23-guided-tour", info.project.name);
    await page.getByRole("button", { name: "Exit tour" }).click();
  });
});
