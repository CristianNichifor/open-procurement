import { test, expect } from '@playwright/test';

// OP-9: names are suggested from a small JSON index while the engine is still loading.

const INDEX = {
  entitati: [
    ['DEDEMAN S.R.L.', '2816464', 'f'],
    ['INSTITUTUL CLINIC FUNDENI', '4204003', 'a'],
    ['SPITALUL CLINIC DE URGENȚĂ BUCUREȘTI', '4283120', 'a'],
    ['PRIMĂRIA MUNICIPIULUI IAȘI', '4541580', 'a'],
  ],
};

test.beforeEach(async ({ page }) => {
  await page.route('**/data/entitati.json', route => route.fulfill({ json: INDEX }));
  // Hold the engine back: the suggestions must not wait for it.
  await page.route('**/duckdb-*.wasm', async route => {
    await new Promise(resolve => setTimeout(resolve, 8000));
    await route.continue().catch(() => {});
  });
});

test('names are suggested before the engine loads, ignoring diacritics', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#run')).toBeEnabled();
  const q = page.locator('#q');
  await q.pressSequentially('urgenta');
  const list = page.locator('#sugestii');
  await expect(list).toBeVisible();
  await expect(list.getByRole('option')).toHaveText([/SPITALUL CLINIC DE URGENȚĂ/]);
  await expect(q).toHaveAttribute('aria-expanded', 'true');

  await q.fill('');
  await q.pressSequentially('iasi');
  await expect(list.getByRole('option')).toHaveText([/PRIMĂRIA MUNICIPIULUI IAȘI/]);
  await q.press('Escape');
  await expect(list).toBeHidden();
  await expect(q).toHaveAttribute('aria-expanded', 'false');
});

test('choosing a suggestion opens that organisation by its CUI', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#run')).toBeEnabled();
  const q = page.locator('#q');
  await q.pressSequentially('cl');
  await expect(page.locator('#sugestii [role=option]')).toHaveCount(2);
  await q.press('ArrowDown');
  await q.press('ArrowDown');
  await expect(page.locator('#sugestii [aria-selected=true]')).toContainText('URGENȚĂ');
  await q.press('Enter');
  await expect(q).toHaveValue('4283120');
  await expect(page.locator('#sugestii')).toBeHidden();
  await expect(page).toHaveURL(/v=dosar.*q=4283120/, { timeout: 90_000 });
});

test('one letter suggests nothing', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#run')).toBeEnabled();
  await page.locator('#q').pressSequentially('d');
  await expect(page.locator('#sugestii')).toBeHidden();
});
