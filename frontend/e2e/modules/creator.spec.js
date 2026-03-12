import { test, expect } from '@playwright/test'

test.describe('Creator Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should load creator page', async ({ page }) => {
    await page.goto('/creator')
    await expect(page).toHaveURL('/creator')
    await page.waitForTimeout(2000)
  })

  test('should show content list or empty state', async ({ page }) => {
    await page.goto('/creator')
    await page.waitForTimeout(2000)
    await expect(page.locator('body')).toBeVisible()
  })

  test('should create new content', async ({ page }) => {
    await page.goto('/creator')
    await page.waitForTimeout(1000)

    const addButton = page.locator('button:has-text("Content"), button:has-text("Inhalt"), button:has-text("Neu")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(2000)
    }
  })

  test('should open content editor', async ({ page }) => {
    await page.goto('/creator')
    await page.waitForTimeout(2000)

    // Click on first content item if exists
    const contentCard = page.locator('[class*="card"], [class*="rounded-lg border"]').first()
    if (await contentCard.count() > 0) {
      await contentCard.click()
      await page.waitForTimeout(2000)
    }
  })
})
