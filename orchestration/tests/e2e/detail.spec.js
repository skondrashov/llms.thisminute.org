// @ts-check
import { test, expect } from '@playwright/test';

test.describe('Orchestration — Detail Drawer', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration/');
    await page.locator('.card').first().waitFor();
  });

  test('clicking a card opens the detail drawer', async ({ page }) => {
    const firstCard = page.locator('.card').first();
    const cardName = await firstCard.locator('.card-name').textContent();
    await firstCard.click();

    const detail = page.locator('#detail');
    await expect(detail).toHaveClass(/active/);

    // Drawer should show the pattern name
    const drawerName = await detail.locator('h2').textContent();
    expect(drawerName).toBe(cardName);
  });

  test('escape closes the detail drawer', async ({ page }) => {
    await page.locator('.card').first().click();
    await expect(page.locator('#detail')).toHaveClass(/active/);

    await page.keyboard.press('Escape');
    await expect(page.locator('#detail')).not.toHaveClass(/active/);
  });

  test('close button closes the detail drawer', async ({ page }) => {
    await page.locator('.card').first().click();
    await expect(page.locator('#detail')).toHaveClass(/active/);

    await page.locator('#detail-close').click();
    await expect(page.locator('#detail')).not.toHaveClass(/active/);
  });

  test('URL hash updates when opening a pattern', async ({ page }) => {
    const firstCard = page.locator('.card').first();
    const cardId = await firstCard.getAttribute('data-id');
    await firstCard.click();

    expect(page.url()).toContain('#' + cardId);
  });

  test('deep link opens the detail drawer', async ({ page }) => {
    // Get a known pattern ID from the page first
    const firstCardId = await page.locator('.card').first().getAttribute('data-id');

    // Navigate directly to the hash URL
    await page.goto('/orchestration/#' + firstCardId);
    await expect(page.locator('#detail')).toHaveClass(/active/);
  });

  test('no console errors in detail drawer', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.locator('.card').first().click();
    await expect(page.locator('#detail')).toHaveClass(/active/);

    // Wait a moment for async operations (comments, mermaid)
    await page.waitForTimeout(500);

    expect(errors).toEqual([]);
  });

});
