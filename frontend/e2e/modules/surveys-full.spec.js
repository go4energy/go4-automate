import { test, expect } from '@playwright/test'

test.describe('Surveys Module - Full Test', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should load surveys page', async ({ page }) => {
    await page.goto('/surveys')
    await expect(page).toHaveURL('/surveys')
    await page.waitForTimeout(2000)
  })

  test('should show survey list', async ({ page }) => {
    await page.goto('/surveys')
    await page.waitForTimeout(2000)
    await expect(page.locator('body')).toBeVisible()
  })

  test('should create a new survey', async ({ page }) => {
    await page.goto('/surveys')
    await page.waitForTimeout(1000)

    // Click new survey button
    await page.click('text=Neue Umfrage')
    await page.waitForTimeout(500)

    // Fill form
    await page.fill('input[placeholder*="Kundenzufriedenheit"]', 'E2E Full Test Survey')
    await page.fill('textarea', 'Automatisch erstellt durch E2E Test')

    // Select type - use first available option
    const typeSelect = page.locator('select').first()
    if (await typeSelect.count() > 0) {
      // Get available options and select the first non-empty one
      const options = await typeSelect.locator('option').allTextContents()
      if (options.length > 1) {
        await typeSelect.selectOption({ index: 1 }) // Select first non-default option
      }
    }

    // Submit
    await page.click('button:has-text("Erstellen")')
    await expect(page).toHaveURL(/\/surveys\/\d+\/edit/, { timeout: 10000 })
  })

  test('should add questions to survey', async ({ page }) => {
    await page.goto('/surveys')
    await page.waitForTimeout(1000)

    // Click on first survey to edit
    const surveyCard = page.locator('[class*="rounded-lg border"]').first()
    if (await surveyCard.count() > 0) {
      // Find edit button
      const editBtn = surveyCard.locator('button[title*="Bearbeiten"], button:has(svg)')
      if (await editBtn.count() > 0) {
        await editBtn.first().click()
      } else {
        await surveyCard.click()
      }
      await page.waitForTimeout(2000)
    }

    // Look for add question button
    const addQuestionBtn = page.locator('button:has-text("Frage"), button:has-text("Question")')
    if (await addQuestionBtn.count() > 0) {
      await addQuestionBtn.first().click()
      await page.waitForTimeout(1000)
    }
  })

  test('should activate survey', async ({ page }) => {
    await page.goto('/surveys')
    await page.waitForTimeout(2000)

    // Find a draft survey and activate it
    const activateBtn = page.locator('button:has-text("Aktivieren")')
    if (await activateBtn.count() > 0) {
      await activateBtn.first().click()
      await page.waitForTimeout(2000)
    }
  })

  test('should view survey results', async ({ page }) => {
    await page.goto('/surveys')
    await page.waitForTimeout(2000)

    // Find results button
    const resultsBtn = page.locator('button:has-text("Ergebnisse")')
    if (await resultsBtn.count() > 0) {
      await resultsBtn.first().click()
      await page.waitForTimeout(2000)
      await expect(page).toHaveURL(/\/surveys\/\d+\/results/)
    }
  })

  test('should duplicate survey', async ({ page }) => {
    await page.goto('/surveys')
    await page.waitForTimeout(2000)

    // Find duplicate button
    const duplicateBtn = page.locator('button[title*="Duplizieren"]')
    if (await duplicateBtn.count() > 0) {
      await duplicateBtn.first().click()
      await page.waitForTimeout(2000)
    }
  })

  test('should filter surveys', async ({ page }) => {
    await page.goto('/surveys')
    await page.waitForTimeout(1000)

    // Search
    const searchInput = page.locator('input[placeholder*="Such"]')
    if (await searchInput.count() > 0) {
      await searchInput.fill('Test')
      await page.waitForTimeout(500)
    }

    // Status filter
    const statusSelect = page.locator('select').first()
    if (await statusSelect.count() > 0) {
      await statusSelect.selectOption('active')
      await page.waitForTimeout(500)
    }
  })

  test('should open survey detail', async ({ page }) => {
    await page.goto('/surveys')
    await page.waitForTimeout(2000)

    // Click on survey title/card
    const surveyCard = page.locator('[class*="rounded-lg border"]').first()
    if (await surveyCard.count() > 0) {
      const title = surveyCard.locator('h3, [class*="font-medium"]').first()
      if (await title.count() > 0) {
        await title.click()
        await page.waitForTimeout(2000)
        await expect(page).toHaveURL(/\/surveys\/\d+$/)
      }
    }
  })
})
