import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should show desktop with modules', async ({ page }) => {
    await page.goto('/')
    // Should have content on the page
    await expect(page.locator('body')).toBeVisible()
    await page.waitForTimeout(1000)
  })

  test('should navigate to contacts', async ({ page }) => {
    await page.goto('/contacts')
    await expect(page).toHaveURL('/contacts')
  })

  test('should navigate to CRM', async ({ page }) => {
    await page.goto('/crm')
    await expect(page.locator('text=CRM')).toBeVisible()
  })

  test('should navigate to funnels', async ({ page }) => {
    await page.goto('/funnels')
    await expect(page).toHaveURL('/funnels')
  })

  test('should navigate to settings', async ({ page }) => {
    await page.goto('/settings')
    await expect(page).toHaveURL('/settings')
  })

  test('should toggle dark mode', async ({ page }) => {
    await page.goto('/')

    // Find and click dark mode toggle
    const darkModeButton = page.locator('button[title*="Mode"]')
    await darkModeButton.click()

    // Body should have dark class
    await expect(page.locator('html')).toHaveClass(/dark/)
  })

  test('should logout', async ({ page }) => {
    await page.goto('/')

    // Open user menu
    await page.click('button:has-text("Team")')

    // Click logout
    await page.click('text=Abmelden')

    // Should redirect to login
    await expect(page).toHaveURL('/login')
  })
})
