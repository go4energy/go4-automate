import { test } from '@playwright/test';

test('test scroll behavior detailed', async ({ page }) => {
  // Login
  await page.goto('http://192.168.1.227:8081/login');
  await page.fill('input[type="email"]', 'team@go4.energy');
  await page.fill('input[type="password"]', 'changeme');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard**', { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(1000);

  // Go to guide page
  await page.goto('http://192.168.1.227:8081/linkedin/guide');
  await page.waitForTimeout(1500);

  // Get viewport and scroll position before
  const before = await page.evaluate(() => ({
    scrollY: window.scrollY,
    viewportHeight: window.innerHeight
  }));
  console.log('Before click:', before);

  // Screenshot before
  await page.screenshot({ path: '/tmp/scroll-before.png', fullPage: false });

  // Click on "Best Practices" in sidebar (near bottom)
  await page.click('a[href="#best-practices"]');
  await page.waitForTimeout(800);

  // Get scroll position after
  const after = await page.evaluate(() => ({
    scrollY: window.scrollY,
    headerHeight: document.querySelector('header')?.offsetHeight || 0
  }));
  console.log('After click:', after);

  // Screenshot after
  await page.screenshot({ path: '/tmp/scroll-after.png', fullPage: false });

  // Check if "Best Practices" heading is visible
  const headingVisible = await page.evaluate(() => {
    const h = document.getElementById('best-practices');
    if (!h) return { found: false };
    const rect = h.getBoundingClientRect();
    return { 
      found: true, 
      top: rect.top, 
      visible: rect.top > 60 && rect.top < 200 
    };
  });
  console.log('Heading visibility:', headingVisible);
});
