// Config mínima para smoke E2E del MVP.
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "tests/e2e",
  timeout: 120_000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8501",
    headless: true,
    trace: "retain-on-failure",
  },
  webServer: {
    // Se levanta por import para asegurar carga completa de HTML_PARTS + script UI.
    command: "python -c \"import smartcounter_ui as ui; ui.serve('127.0.0.1', 8501)\"",
    url: "http://127.0.0.1:8501/health",
    timeout: 120_000,
    reuseExistingServer: true,
  },
});
