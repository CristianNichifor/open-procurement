import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// WCAG 2.0/2.1/2.2 A and AA. Serious and critical findings fail; the rest are reported in
// the test output so they are seen, not silently accepted.
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

async function scan(page, info, label) {
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  const blocking = violations.filter(v => ['serious', 'critical'].includes(v.impact));
  for (const v of violations) {
    info.annotations.push({ type: `axe ${v.impact}`, description: `${label}: ${v.id} (${v.nodes.length})` });
  }
  expect(blocking.map(v => `${v.id}: ${v.nodes.map(n => n.target.join(' ')).join(', ')}`),
    `${label} has serious or critical axe violations`).toEqual([]);
}

for (const colorScheme of ['light', 'dark']) {
  test(`front door and a results table pass axe in ${colorScheme}`, async ({ page }, info) => {
    await page.emulateMedia({ colorScheme });
    await page.goto('/');
    await expect(page.locator('#panorama .pan').first()).toBeVisible();
    await expect(page.locator('#run')).toBeEnabled();
    await scan(page, info, 'front door');
    await page.goto('/#v=cpv');
    await expect(page.locator('#out tbody tr').first()).toBeVisible();
    await scan(page, info, 'cpv table');
  });

  for (const path of ['privacy.html', 'metodologie.html', 'replica.html', 'privacy.html?lang=en']) {
    test(`${path} passes axe in ${colorScheme}`, async ({ page }, info) => {
      await page.emulateMedia({ colorScheme });
      await page.goto(`/${path}`);
      await expect(page.locator('h1:visible')).toHaveCount(1);
      await scan(page, info, path);
    });
  }
}
