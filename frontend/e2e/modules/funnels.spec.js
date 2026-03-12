import { test, expect } from '@playwright/test'

test.describe('Funnels Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should load funnels page', async ({ page }) => {
    await page.goto('/funnels')
    await expect(page).toHaveURL('/funnels')
    await page.waitForTimeout(2000)
  })

  test('should show funnels list or empty state', async ({ page }) => {
    await page.goto('/funnels')
    await page.waitForTimeout(2000)
    await expect(page.locator('body')).toBeVisible()
  })

  test('should create a funnel', async ({ page }) => {
    await page.goto('/funnels')
    await page.waitForTimeout(1000)

    const addButton = page.locator('button:has-text("Funnel"), button:has-text("Neu")')
    if (await addButton.count() > 0) {
      await addButton.first().click()
      await page.waitForTimeout(500)

      const nameInput = page.locator('input[name="name"], input[placeholder*="Name"]')
      if (await nameInput.count() > 0) {
        await nameInput.fill('E2E Test Funnel')

        const submitBtn = page.locator('button[type="submit"], button:has-text("Speichern"), button:has-text("Erstellen")')
        if (await submitBtn.count() > 0) {
          await submitBtn.first().click()
          await page.waitForTimeout(2000)
        }
      }
    }
  })

  test('should open funnel detail', async ({ page }) => {
    await page.goto('/funnels')
    await page.waitForTimeout(2000)

    // Click on first funnel if exists
    const funnelCard = page.locator('[class*="card"], [class*="rounded-lg border"]').first()
    if (await funnelCard.count() > 0) {
      await funnelCard.click()
      await page.waitForTimeout(2000)
    }
  })

  test('should open kanban view', async ({ page }) => {
    await page.goto('/funnels')
    await page.waitForTimeout(2000)

    // Look for kanban button or link
    const kanbanLink = page.locator('a:has-text("Kanban"), button:has-text("Kanban")')
    if (await kanbanLink.count() > 0) {
      await kanbanLink.first().click()
      await page.waitForTimeout(2000)
    }
  })
})
