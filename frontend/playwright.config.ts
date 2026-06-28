import { defineConfig, devices } from "@playwright/test";
import { platform } from "os";

const getStartScript = () => {
  const p = platform();
  if (p === "win32") return "scripts/start-windows.ps1";
  if (p === "darwin") return "scripts/start-mac.sh";
  return "scripts/start-linux.sh";
};

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:8000",
    trace: "retain-on-failure",
  },
  webServer: {
    command: getStartScript(),
    url: "http://127.0.0.1:8000",
    cwd: "..",
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
