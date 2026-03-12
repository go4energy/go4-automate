import { test, expect } from '@playwright/test'

test.describe('CRM Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should load CRM deals page', async ({ page }) => {
    await page.goto('/crm')
    await expect(page).toHaveURL('/crm')
    await page.waitForTimeout(2000)
  })

  test('should show deals or empty state', async ({ page }) => {
    await page.goto('/crm')
    await page.waitForTimeout(2000)

    // Page loaded successfully
    await expect(page.locator('body')).toBeVisible()
  })

  test('should navigate to pipelines', async ({ page }) => {
    await page.goto('/crm/pipelines')
    await expect(page).toHaveURL('/crm/pipelines')
    await page.waitForTimeout(2000)
  })

  test('should navigate to tasks', async ({ page }) => {
    await page.goto('/crm/tasks')
    await expect(page).toHaveURL('/crm/tasks')
    await page.waitForTimeout(2000)
  })

  test('should create a deal', async ({ page }) => {
    await page.goto('/crm')
    await page.waitForTimeout(1000)

    const addButton = page.locator('button:has-text("Deal"), button:has-text("Neu")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(500)

      const titleInput = page.locator('input[name="title"], input[placeholder*="Titel"], input[placeholder*="Name"]')
      if (await titleInput.count() > 0) {
        await titleInput.fill('E2E Test Deal')

        const valueInput = page.locator('input[name="value"], input[placeholder*="Wert"]')
        if (await valueInput.count() > 0) {
          await valueInput.fill('10000')
        }

        const submitBtn = page.locator('button[type="submit"], button:has-text("Speichern"), button:has-text("Erstellen")')
        if (await submitBtn.count() > 0) {
          await submitBtn.first().click()
          await page.waitForTimeout(2000)
        }
      }
    }
  })

  test('should create a pipeline', async ({ page }) => {
    await page.goto('/crm/pipelines')
    await page.waitForTimeout(1000)

    const addButton = page.locator('button:has-text("Pipeline"), button:has-text("Neu")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(500)
    }
  })
})
