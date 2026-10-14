import { test, expect } from '@playwright/test';

// OP-10: on a phone a price group is two lines — product and median, then its p10–p90
// range — rather than a card of seven labelled lines.

test('price rows are two lines at 390px', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const row = page.locator('#panorama tr.pret').first();
  await expect(row).toBeVisible();

  const visible = await row.locator('td').evaluateAll(tds => tds
    .filter(td => getComputedStyle(td).display !== 'none')
    .map(td => td.className));
  expect(visible.some(c => c.includes('c-produs'))).toBe(true);
  expect(visible.some(c => c.includes('c-mediana'))).toBe(true);
  expect(visible.some(c => c.includes('interval'))).toBe(true);

  const bar = row.locator('td.interval');
  await expect(bar.locator('.bara')).toBeVisible();
  await expect(bar).toContainText('între');
  // Two lines: the product's top and the bar's top are the only two row positions.
  const tops = await row.locator('td').evaluateAll(tds => [...new Set(tds
    .filter(td => getComputedStyle(td).display !== 'none')
    .map(td => Math.round(td.getBoundingClientRect().top)))]);
  expect(tops.length).toBe(2);
  const box = await row.boundingBox();
  expect(box.height).toBeLessThan(110);
  // Still clickable, and still says so.
  await expect(row.locator('td').last()).toHaveText(/^(Fișă|Detalii) →$/);
});

test('price rows are unchanged on a wide screen', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/');
  const row = page.locator('#panorama tr.pret').first();
  await expect(row).toBeVisible();
  await expect(row.locator('td.interval')).toBeHidden();
  await expect(row.locator('td.c-mediana')).toBeVisible();
  await expect(row.locator('td', { hasText: /^\d/ }).first()).toBeVisible();
});
