import { test, expect } from '@playwright/test';

// The Content-Security-Policy travels in a <meta> tag, so a directive that is too tight
// shows up only at run time: an engine that never starts, a worker that never loads. Any
// violation on the real paths fails here instead of on the published site.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.__cspViolations = [];
    document.addEventListener('securitypolicyviolation', e => {
      window.__cspViolations.push(`${e.violatedDirective} ${e.blockedURI}`);
    });
  });
});

test('the engine starts and queries run under the policy', async ({ page }) => {
  await page.goto('/#v=cpv');
  // The tabs, not Caută: search is enabled during boot and queues until the engine is up.
  await expect(page.locator('#tabs button').first()).toBeEnabled();
  await expect(page.locator('#out tbody tr').first()).toBeVisible();
  await page.goto('/#v=preturi');
  await expect(page.locator('#out tbody tr').first()).toBeVisible();
  expect(await page.evaluate(() => window.__cspViolations)).toEqual([]);
});

test('the static pages run under their policy', async ({ page }) => {
  for (const path of ['privacy.html', 'metodologie.html', 'replica.html']) {
    await page.goto(`/${path}`);
    await page.locator('[data-set-lang="en"]').click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    expect(await page.evaluate(() => window.__cspViolations)).toEqual([]);
  }
});
