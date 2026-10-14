import { test, expect } from '@playwright/test';

for (const page of ['privacy.html', 'metodologie.html', 'replica.html']) {
  test(`${page}: the RO/EN toggle switches the document language`, async ({ page: p }) => {
    await p.goto(`/${page}`);
    await expect(p.locator('html')).toHaveAttribute('lang', 'ro');
    await expect(p.locator('article[data-lang="ro"]')).toBeVisible();
    await expect(p.locator('article[data-lang="en"]')).toBeHidden();
    await expect(p.locator('[data-set-lang="ro"]')).toHaveAttribute('aria-pressed', 'true');

    await p.locator('[data-set-lang="en"]').click();
    await expect(p.locator('html')).toHaveAttribute('lang', 'en');
    await expect(p.locator('article[data-lang="en"]')).toBeVisible();
    await expect(p.locator('article[data-lang="ro"]')).toBeHidden();
    await expect(p.locator('[data-set-lang="en"]')).toHaveAttribute('aria-pressed', 'true');

    await p.reload();
    await expect(p.locator('html')).toHaveAttribute('lang', 'en');
    await expect(p.locator('article[data-lang="en"]')).toBeVisible();

    await p.locator('[data-set-lang="ro"]').click();
    await expect(p.locator('html')).toHaveAttribute('lang', 'ro');
    await expect(p.locator('article[data-lang="ro"]')).toBeVisible();
  });
}

test('the caveat leads to the methodology on this site', async ({ page }) => {
  await page.goto('/');
  await page.locator('#banner a', { hasText: 'metodologia' }).click();
  await expect(page).toHaveURL(/\/metodologie\.html$/);
  await expect(page.locator('h1').first()).toBeVisible();
});
