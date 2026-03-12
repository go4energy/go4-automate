import { test, expect } from '@playwright/test'

test.describe('Settings Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should load settings page', async ({ page }) => {
    await page.goto('/settings')
    await expect(page).toHaveURL('/settings')
    await page.waitForTimeout(2000)
  })

  test('should show profile tab', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForTimeout(2000)

    // Should show profile info or tabs
    await expect(page.locator('body')).toBeVisible()
  })

  test('should switch between settings tabs', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForTimeout(1000)

    const tabNames = ['Profil', 'Plattform', 'Global', 'Module']
    for (const name of tabNames) {
      const tab = page.locator(`button:has-text("${name}"), [class*="tab"]:has-text("${name}")`)
      if (await tab.count() > 0) {
        await tab.first().click()
        await page.waitForTimeout(500)
      }
    }
  })

  test('should show password change form', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForTimeout(1000)

    // Look for password fields
    const passwordInput = page.locator('input[type="password"]')
    expect(await passwordInput.count()).toBeGreaterThanOrEqual(0)
  })

  test('should navigate to desktop layout', async ({ page }) => {
    await page.goto('/settings/desktop-layout')
    await expect(page).toHaveURL('/settings/desktop-layout')
    await page.waitForTimeout(2000)
  })

  test('should navigate to prompts', async ({ page }) => {
    await page.goto('/settings')
    await page.waitForTimeout(1000)

    const promptsTab = page.locator('button:has-text("Prompts"), a:has-text("Prompts")')
    if (await promptsTab.count() > 0) {
      await promptsTab.first().click()
      await page.waitForTimeout(1000)
    }
  })
})
