import { test, expect } from '@playwright/test';

// The query engine comes from cdn.jsdelivr.net. A network, an extension or a country that
// blocks that host must cost the reader the filters, not the page: the front door is
// drawn from JSON on this origin and needs no engine at all.
for (const hash of ['', '#v=cpv']) {
  test(`blocked CDN still shows the front door${hash ? ` (link ${hash})` : ''}`, async ({ page }) => {
    await page.route('**/cdn.jsdelivr.net/**', route => route.abort());
    await page.goto(`/${hash}`);
    await expect(page.locator('#panorama .pan').first()).toBeVisible();
    const status = page.locator('#status');
    await expect(status).toContainText('cdn.jsdelivr.net');
    await expect(status).not.toContainText('file://');
    await expect(page.locator('#run')).toBeDisabled();
    // The link the reader came with is kept: it works again once the engine can load.
    if (hash) await expect(page).toHaveURL(new RegExp(`${hash}$`));
  });
}
