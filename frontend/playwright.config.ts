import { existsSync } from "node:fs";

import { chromium, defineConfig, devices } from "@playwright/test";

// End-to-end smoke tests and the README screenshots.
// Both servers start automatically (or are reused if already running):
//   npm run test:e2e          smoke tests
//   npm run test:tour         the whole guided tour in auto mode
//   npm run screenshots       desktop + mobile screenshots into ../screenshots

// Use Playwright's own Chromium when it is installed (`npx playwright install chromium`);
// on Windows without it, fall back to Microsoft Edge, which ships with the OS.
const bundled = (() => {
  try {
    return existsSync(chromium.executablePath());
  } catch {
    return false;
  }
})();
const CHANNEL = process.env.PW_CHANNEL ?? (!bundled && process.platform === "win32" ? "msedge" : undefined);

const BACKEND_PYTHON = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  // Answers come from a real model (or the local fallback), so allow for slow replies.
  timeout: 240_000,
  expect: { timeout: 20_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:3000",
    channel: CHANNEL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "smoke",
      testMatch: /smoke\.spec\.ts/,
      dependencies: ["setup"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
    },
    {
      name: "tour",
      testMatch: /tour\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
    },
    {
      name: "screenshots-desktop",
      testMatch: /screenshots\.spec\.ts/,
      dependencies: ["setup"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
    },
    {
      name: "screenshots-mobile",
      testMatch: /screenshots\.spec\.ts/,
      dependencies: ["setup"],
      use: { ...devices["Pixel 7"], viewport: { width: 390, height: 844 } },
    },
  ],
  webServer: [
    {
      command: `${BACKEND_PYTHON} -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: "../backend",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: true,
      timeout: 180_000,
    },
    {
      command: "npx next dev --port 3000",
      url: "http://localhost:3000/login",
      reuseExistingServer: true,
      timeout: 180_000,
    },
  ],
});
