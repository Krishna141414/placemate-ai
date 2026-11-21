import { expect, type Page } from "@playwright/test";

// Same host as the app uses (lib/api.ts), so the session cookie applies to it.
export const API = "http://localhost:8000";

export const STATE = {
  student: "e2e/.auth/student.json",
  coordinator: "e2e/.auth/coordinator.json",
} as const;

/**
 * Collects console errors for a test. Requests that exist to be refused (an
 * invalid upload, a security check) make the browser log "Failed to load
 * resource"; tests that trigger them on purpose pass the status codes to allow.
 */
export function watchConsole(page: Page) {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return {
    expectClean(allowedStatuses: number[] = []) {
      const unexpected = errors.filter((text) => {
        const status = /status of (\d{3})/.exec(text)?.[1];
        return !(status && allowedStatuses.includes(Number(status)));
      });
      expect(unexpected, "console errors").toEqual([]);
    },
  };
}

/** The newest answer on the Ask page, once it has finished. */
export async function lastAnswer(page: Page, timeout = 180_000) {
  const turns = page.locator('[data-tour="answer-turn"]');
  const last = turns.last();
  await expect(last).toHaveAttribute("data-status", /done|error/, { timeout });
  return last;
}
