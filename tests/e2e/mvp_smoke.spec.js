const { test, expect } = require("@playwright/test");
const path = require("path");

test("Smoke MVP: carga -> resultado -> observación -> historial -> cierre", async ({ page }) => {
  const archivoValido = path.resolve(
    process.cwd(),
    "validation_pack_mvp",
    "03_encabezado_desplazado_representativo.xlsx"
  );

  await page.goto("/");
  await expect(page.locator("#analyzeBtn")).toBeDisabled();

  await page.locator("#fileInput").setInputFiles(archivoValido);
  await expect(page.locator("#analyzeBtn")).toBeEnabled({ timeout: 30_000 });

  await page.click("#analyzeBtn");
  await expect(page.locator("#screen2Area")).toHaveClass(/active/, { timeout: 60_000 });
  await expect(page.locator("#resultText")).toContainText("Contexto del archivo");

  await expect(page.locator("#observationList .obs-btn").first()).toBeVisible({ timeout: 30_000 });
  await page.locator("#observationList .obs-btn").first().click();
  await expect(page.locator("#screen3Area")).toHaveClass(/active/);
  await expect(page.locator("#detailCode")).not.toHaveText("No disponible");

  await page.click("#backToResultBtn");
  await expect(page.locator("#screen2Area")).toHaveClass(/active/);

  await page.click("#historyNavBtn");
  await expect(page.locator("#screen5Area")).toHaveClass(/active/);
  await expect(page.locator("#historyList .history-item").first()).toBeVisible({ timeout: 30_000 });

  await page.locator("#historyList .history-item button").first().click();
  await expect(page.locator("#historyDetail")).toBeVisible();

  await page.click("#historyOpenCloseBtn");
  await expect(page.locator("#screen6Area")).toHaveClass(/active/);
  await expect(page.locator("#closeFile")).not.toHaveText("No disponible");
});
