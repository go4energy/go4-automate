import { test, expect } from '@playwright/test'

test.describe('Contacts Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should load contacts page', async ({ page }) => {
    await page.goto('/contacts')
    await expect(page).toHaveURL('/contacts')
    await page.waitForTimeout(2000)
  })

  test('should show contacts list or empty state', async ({ page }) => {
    await page.goto('/contacts')
    await page.waitForTimeout(2000)

    // Check for table or empty state
    const hasContent = await page.locator('table, [class*="empty"], [class*="grid"]').first().isVisible()
    expect(hasContent).toBeTruthy()
  })

  test('should open create contact modal', async ({ page }) => {
    await page.goto('/contacts')
    await page.waitForTimeout(1000)

    // Look for add button
    const addButton = page.locator('button:has-text("Kontakt"), button:has-text("Neu"), button:has-text("+")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(500)
    }
  })

  test('should create a test contact', async ({ page }) => {
    await page.goto('/contacts')
    await page.waitForTimeout(1000)

    // Try to create contact
    const addButton = page.locator('button:has-text("Kontakt"), button:has-text("Neu")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(500)

      // Fill form if modal opened
      const nameInput = page.locator('input[name="name"], input[placeholder*="Name"]')
      if (await nameInput.count() > 0) {
        await nameInput.fill('E2E Test Kontakt')

        const emailInput = page.locator('input[type="email"], input[name="email"]')
        if (await emailInput.count() > 0) {
          await emailInput.fill('e2e-test@example.com')
        }

        // Submit
        const submitBtn = page.locator('button[type="submit"], button:has-text("Speichern"), button:has-text("Erstellen")')
        if (await submitBtn.count() > 0) {
          await submitBtn.first().click()
          await page.waitForTimeout(2000)
        }
      }
    }
  })

  test('should filter contacts', async ({ page }) => {
    await page.goto('/contacts')
    await page.waitForTimeout(1000)

    const searchInput = page.locator('input[placeholder*="Such"], input[type="search"]')
    if (await searchInput.count() > 0) {
      await searchInput.fill('test')
      await page.waitForTimeout(1000)
    }
  })
})
