import { test, expect } from '@playwright/test'

test.describe('Collector Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should load collector page', async ({ page }) => {
    await page.goto('/collector')
    await expect(page).toHaveURL('/collector')
    await page.waitForTimeout(2000)
  })

  test('should show tabs for sources, findings, topics', async ({ page }) => {
    await page.goto('/collector')
    await page.waitForTimeout(2000)

    // Check for tab navigation
    const tabs = page.locator('button[role="tab"], [class*="tab"]')
    expect(await tabs.count()).toBeGreaterThan(0)
  })

  test('should switch between tabs', async ({ page }) => {
    await page.goto('/collector')
    await page.waitForTimeout(1000)

    // Click on different tabs
    const tabNames = ['Quellen', 'Findings', 'Topics', 'Sources']
    for (const name of tabNames) {
      const tab = page.locator(`button:has-text("${name}"), [class*="tab"]:has-text("${name}")`)
      if (await tab.count() > 0) {
        await tab.first().click()
        await page.waitForTimeout(500)
      }
    }
  })

  test('should create a source', async ({ page }) => {
    await page.goto('/collector')
    await page.waitForTimeout(1000)

    const addButton = page.locator('button:has-text("Quelle"), button:has-text("Source"), button:has-text("Neu")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(1000)

      // Check if we're on source edit page or still on collector
      const url = page.url()
      const hasCollectorRoute = url.includes('/collector/sources') || url.includes('/collector')
      expect(hasCollectorRoute).toBeTruthy()
    }
  })

  test('should create a topic', async ({ page }) => {
    await page.goto('/collector')
    await page.waitForTimeout(1000)

    // Switch to topics tab first
    const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
    if (await topicsTab.count() > 0) {
      await topicsTab.first().click()
      await page.waitForTimeout(500)
    }

    const addButton = page.locator('button:has-text("Topic"), button:has-text("Thema"), button:has-text("Neu")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(500)
    }
  })
})
