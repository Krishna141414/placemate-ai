import { expect, test } from "@playwright/test";

import { TOUR_STEPS } from "../lib/tour-script";
import { watchConsole } from "./helpers";

// The whole guided tour in Auto mode, from the landing page to the last
// security check, with a pause in the middle. Every step must finish (no
// "did not finish in time"). Run with: npm run test:tour

test("the full guided tour runs in auto mode, and pause holds it", async ({ page }) => {
  test.setTimeout(20 * 60_000);
  const console = watchConsole(page);
  const total = TOUR_STEPS.length;

  await page.goto("/");
  await page.getByRole("button", { name: "Start tour" }).click();
  const bar = page.getByRole("region", { name: "Guided tour" });
  await expect(bar).toContainText(`1 / ${total}`);
  await bar.getByRole("radio", { name: "Fast" }).click();
  await bar.getByRole("radio", { name: "Auto" }).click();

  const stuck: string[] = [];
  let paused = false;
  for (let step = 1; step <= total; step++) {
    await expect(bar).toContainText(`${step} / ${total}`, { timeout: 240_000 });
    await expect(bar).not.toHaveAttribute("data-phase", "running", { timeout: 240_000 });
    if ((await bar.getAttribute("data-phase")) === "stuck") stuck.push(TOUR_STEPS[step - 1].id);

    // Halfway: Space pauses; the tour must stay on this step, then resume.
    if (!paused && step === Math.floor(total / 2)) {
      paused = true;
      await page.keyboard.press("Space");
      await expect(bar.getByRole("button", { name: "Play" })).toBeVisible();
      await page.waitForTimeout(5_000);
      await expect(bar).toContainText(`${step} / ${total}`);
      await page.keyboard.press("Space");
    }
  }

  // After the last step, auto mode finishes the tour and the bar closes.
  await expect(page.getByRole("region", { name: "Guided tour" })).toHaveCount(0, { timeout: 30_000 });
  expect(stuck, "steps that did not finish").toEqual([]);
  // The tour deliberately triggers refused requests: invalid upload (415),
  // oversized upload (413), rate limit (429), and the 401 an anonymous admin call gets.
  console.expectClean([401, 403, 413, 415, 429]);
});
