import { test, expect } from '@playwright/test';

// First-visit experience: what a reader sees in the seconds a cold load takes, and the
// small cues that say what is clickable, how recent the data is and what is thin.

test('the engine is requested before the front-door JSON', async ({ page }) => {
  const order = [];
  page.on('request', r => {
    const u = r.url();
    if (u.includes('duckdb-wasm@')) order.push('engine');
    if (u.endsWith('/panorama.json')) order.push('panorama');
  });
  await page.goto('/');
  await expect(page.locator('#panorama .pan').first()).toBeVisible();
  await expect.poll(() => order.includes('engine')).toBe(true);
  expect(order.indexOf('engine')).toBeLessThan(order.indexOf('panorama'));
});

test('a search typed while the engine loads is queued and then runs', async ({ page }) => {
  // Hold the engine back so the queue is observable on a fast machine.
  await page.route('**/duckdb-*.wasm', async route => {
    await new Promise(resolve => setTimeout(resolve, 4000));
    await route.continue();
  });
  await page.goto('/');
  await expect(page.locator('#panorama .pan').first()).toBeVisible();
  await expect(page.locator('#run')).toBeEnabled();
  await page.locator('#q').fill('fundeni');
  await page.locator('#run').click();
  await expect(page.locator('#status')).toContainText('imediat ce');
  await expect(page).toHaveURL(/v=dosar/, { timeout: 90_000 });
  await expect(page.locator('#dosar')).not.toBeEmpty();
});

test('a tab change replaces the old table at once', async ({ page }) => {
  await page.goto('/#v=sumar');
  await expect(page.locator('#out tbody tr:not(.skeleton)').first()).toBeVisible();
  const first = await page.evaluate(() => {
    document.querySelector('#tabs [data-key="cpv"]').click();
    return document.querySelector('#out tbody tr')?.className;
  });
  expect(first).toBe('skeleton');
});

test('codes are shown as words', async ({ page }) => {
  await page.goto('/#v=contracte');
  const out = page.locator('#out tbody');
  await expect(out.locator('tr:not(.skeleton)').first()).toBeVisible();
  await expect(out).not.toContainText('plafon_acord_cadru');
  await expect(out).not.toContainText('contract_subsecvent');
  await page.goto('/#v=indicatori&s=dependenta-01');
  await expect(out.locator('tr:not(.skeleton)').first()).toBeVisible();
  await expect(out).not.toContainText('dependenta-01');
  await expect(out).toContainText('Concentrare');
});

test('clickable rows carry a visible cue', async ({ page }) => {
  await page.goto('/');
  const rows = page.locator('#panorama tr.drillable');
  await expect(rows.first()).toBeVisible();
  for (const row of await rows.all()) {
    await expect(row.locator('td').last()).toHaveText(/^(Fișă|Detalii) →$/);
  }
});

test('the front door: no stray bullets, thin groups marked, data date shown', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#panorama .pan').first()).toBeVisible();
  expect(await page.locator('#panorama ul.legend').first()
    .evaluate(el => getComputedStyle(el).listStyleType)).toBe('none');
  const n = await page.evaluate(async () =>
    (await (await fetch('data/panorama.json')).json()).preturi.map(r => r.n));
  if (n.some(x => x < 10)) {
    await expect(page.locator('#panorama td.slab').first()).toBeVisible();
    await expect(page.locator('#panorama .nota-slab')).toContainText('10');
  }
  await expect(page.locator('#la-zi')).toContainText(/date până la \d{1,2} \S+ \d{4}/);
  await expect(page.locator('footer')).toContainText(/date până la \d{1,2} \S+ \d{4}/);
});

test('the phone tab bar shows that it scrolls', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#v=ruti');
  await expect(page.locator('#run')).toBeEnabled();
  const tabs = page.locator('#tabs');
  expect(await tabs.evaluate(el => getComputedStyle(el).scrollSnapType)).toContain('x');
  expect(await tabs.evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
  expect(await tabs.evaluate(el => {
    const s = getComputedStyle(el);
    return s.maskImage || s.webkitMaskImage;
  })).not.toBe('none');
  const selected = tabs.locator('[aria-selected="true"]');
  await expect.poll(() => selected.evaluate(b => {
    const t = b.parentElement.getBoundingClientRect(), r = b.getBoundingClientRect();
    return r.left >= t.left - 1 && r.right <= t.right + 1;
  })).toBe(true);
});
