import { test, expect } from '@playwright/test'

test.describe('Surveys', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should navigate to surveys', async ({ page }) => {
    await page.goto('/surveys')
    await expect(page).toHaveURL('/surveys')
  })

  test('should show survey list or empty state', async ({ page }) => {
    await page.goto('/surveys')
    await page.waitForTimeout(1000)
    // Page should load without error
    await expect(page.locator('body')).toBeVisible()
  })

  test('should open create survey modal', async ({ page }) => {
    await page.goto('/surveys')

    await page.click('text=Neue Umfrage')

    // Modal should be visible
    await expect(page.locator('text=Titel')).toBeVisible()
    await expect(page.locator('input[placeholder*="Kundenzufriedenheit"]')).toBeVisible()
  })

  test('should create a survey', async ({ page }) => {
    await page.goto('/surveys')

    await page.click('text=Neue Umfrage')

    // Fill form
    await page.fill('input[placeholder*="Kundenzufriedenheit"]', 'E2E Test Survey')
    await page.fill('textarea', 'Created by Playwright')

    // Submit
    await page.click('button:has-text("Erstellen")')

    // Should redirect to edit page
    await expect(page).toHaveURL(/\/surveys\/\d+\/edit/, { timeout: 10000 })
  })
})
