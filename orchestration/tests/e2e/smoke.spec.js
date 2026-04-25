// @ts-check
import { test, expect } from '@playwright/test';

test.describe('Orchestration — Smoke', () => {

  test('page loads and renders pattern cards', async ({ page }) => {
    await page.goto('/orchestration/');
    // Wait for the grid to populate
    const cards = page.locator('.card');
    await expect(cards.first()).toBeVisible();
    // First visit defaults to "core" lens — clear it to see all
    await page.keyboard.press('Escape');
    // Should have a substantial number of patterns
    const count = await cards.count();
    expect(count).toBeGreaterThan(200);
  });

  test('no console errors on load', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto('/orchestration/');
    // Wait for init to complete
    await page.locator('.card').first().waitFor();
    expect(errors).toEqual([]);
  });

  test('stats bar shows non-zero counts', async ({ page }) => {
    await page.goto('/orchestration/');
    await page.locator('.card').first().waitFor();

    const totalCount = await page.locator('#total-count').textContent();
    expect(Number(totalCount)).toBeGreaterThan(200);

    const categoryCount = await page.locator('#category-count').textContent();
    expect(Number(categoryCount)).toBeGreaterThan(10);

    const structureCount = await page.locator('#structure-count').textContent();
    expect(Number(structureCount)).toBeGreaterThan(5);
  });

});
