// @ts-check
import { test, expect } from '@playwright/test';

test.describe('Orchestration — Filters', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/orchestration/');
    await page.locator('.card').first().waitFor();
    // Clear any default lens filter (first visit defaults to "core")
    await page.keyboard.press('Escape');
  });

  test('domain filter reduces card count', async ({ page }) => {
    const totalCards = await page.locator('.card').count();

    // Open domain panel and click the first non-All tile
    await page.locator('#domain-panel-header').click();
    const domainTile = page.locator('#domain-tiles .filter-tile[data-domain]:not(.filter-tile-all)').first();
    await domainTile.click();

    // Card count should decrease
    const filteredCards = await page.locator('.card').count();
    expect(filteredCards).toBeLessThan(totalCards);
    expect(filteredCards).toBeGreaterThan(0);

    // Result count should be visible
    const resultCount = page.locator('#result-count');
    await expect(resultCount).not.toBeEmpty();
  });

  test('category filter reduces card count', async ({ page }) => {
    const totalCards = await page.locator('.card').count();

    // Open category panel and click the first non-All tile
    await page.locator('#category-panel-header').click();
    const categoryTile = page.locator('#category-tiles .filter-tile[data-category]:not(.filter-tile-all)').first();
    await categoryTile.click();

    const filteredCards = await page.locator('.card').count();
    expect(filteredCards).toBeLessThan(totalCards);
    expect(filteredCards).toBeGreaterThan(0);
  });

  test('structure filter reduces card count', async ({ page }) => {
    const totalCards = await page.locator('.card').count();

    // Open structure panel and click the first non-All tile
    await page.locator('#structure-panel-header').click();
    const structureTile = page.locator('#structure-tiles .filter-tile[data-sc]:not(.filter-tile-all)').first();
    await structureTile.click();

    const filteredCards = await page.locator('.card').count();
    expect(filteredCards).toBeLessThan(totalCards);
    expect(filteredCards).toBeGreaterThan(0);
  });

  test('search filters by text', async ({ page }) => {
    const totalCards = await page.locator('.card').count();

    await page.locator('#search').fill('military');
    // Wait for debounce
    await page.waitForTimeout(200);

    const filteredCards = await page.locator('.card').count();
    expect(filteredCards).toBeLessThan(totalCards);
    expect(filteredCards).toBeGreaterThan(0);

    // Cards should contain the search term
    const firstCardText = await page.locator('.card').first().textContent();
    expect(firstCardText?.toLowerCase()).toContain('military');
  });

  test('escape clears all filters', async ({ page }) => {
    // Apply a search filter
    await page.locator('#search').fill('pipeline');
    await page.waitForTimeout(200);
    const filteredCards = await page.locator('.card').count();

    // Press Escape (blur input first)
    await page.locator('#search').blur();
    await page.keyboard.press('Escape');

    const resetCards = await page.locator('.card').count();
    expect(resetCards).toBeGreaterThan(filteredCards);

    // Search should be cleared
    await expect(page.locator('#search')).toHaveValue('');
  });

  test('domain tile counts are non-zero', async ({ page }) => {
    // Open domain panel
    await page.locator('#domain-panel-header').click();
    const tiles = page.locator('#domain-tiles .filter-tile:not(.filter-tile-all) .filter-tile-count');
    const tileCount = await tiles.count();
    expect(tileCount).toBeGreaterThan(0);

    // Each tile should have a non-zero count
    for (let i = 0; i < tileCount; i++) {
      const count = await tiles.nth(i).textContent();
      expect(Number(count)).toBeGreaterThan(0);
    }
  });

  test('no console errors when clicking filters', async ({ page }) => {
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));

    // Click through each filter type
    await page.locator('#domain-panel-header').click();
    await page.locator('#domain-tiles .filter-tile[data-domain]:not(.filter-tile-all)').first().click();

    await page.locator('#structure-panel-header').click();
    await page.locator('#structure-tiles .filter-tile[data-sc]:not(.filter-tile-all)').first().click();

    await page.locator('#category-panel-header').click();
    await page.locator('#category-tiles .filter-tile[data-category]:not(.filter-tile-all)').first().click();

    expect(errors).toEqual([]);
  });

});
