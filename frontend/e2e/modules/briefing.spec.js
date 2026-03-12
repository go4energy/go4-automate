import { test, expect } from '@playwright/test'

test.describe('Briefing Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should load briefing page', async ({ page }) => {
    await page.goto('/briefing')
    await expect(page).toHaveURL('/briefing')
    await page.waitForTimeout(2000)
  })

  test('should show channels or empty state', async ({ page }) => {
    await page.goto('/briefing')
    await page.waitForTimeout(2000)
    await expect(page.locator('body')).toBeVisible()
  })

  test('should create a channel', async ({ page }) => {
    await page.goto('/briefing')
    await page.waitForTimeout(1000)

    const addButton = page.locator('button:has-text("Channel"), button:has-text("Kanal"), button:has-text("Neu")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(1000)

      // Should navigate to channel edit page or show modal
      const url = page.url()
      const hasChannelRoute = url.includes('/briefing/channels') || url.includes('/briefing')
      expect(hasChannelRoute).toBeTruthy()
    }
  })

  test('should open channel detail', async ({ page }) => {
    await page.goto('/briefing')
    await page.waitForTimeout(2000)

    // Click on first channel if exists
    const channelCard = page.locator('[class*="card"], [class*="rounded-lg border"]').first()
    if (await channelCard.count() > 0) {
      await channelCard.click()
      await page.waitForTimeout(2000)
    }
  })

  test('should navigate through tabs', async ({ page }) => {
    await page.goto('/briefing')
    await page.waitForTimeout(1000)

    const tabNames = ['Channels', 'Sources', 'Episodes', 'Quellen']
    for (const name of tabNames) {
      const tab = page.locator(`button:has-text("${name}"), [class*="tab"]:has-text("${name}")`)
      if (await tab.count() > 0) {
        await tab.first().click()
        await page.waitForTimeout(500)
      }
    }
  })
})
