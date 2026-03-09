import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  outputDir: "./results",
  timeout: 30_000,
  retries: 1,
  workers: 1,

  use: {
    baseURL: process.env.BASE_URL ?? "https://nginx",
    ignoreHTTPSErrors: true,
    video: "on",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  reporter: [["list"], ["html", { open: "never", outputFolder: "./report" }]],
});
