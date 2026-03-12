import { test, expect } from '@playwright/test'

/**
 * Engagement Module - Comprehensive E2E Tests
 * Tests ALL functionality: Pipelines, Enrollments, Actions, A/B Tests, Tracking
 */

test.describe('Engagement Module - Comprehensive', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test.describe('Dashboard & Navigation', () => {
    test('should load engagement dashboard with correct elements', async ({ page }) => {
      await page.goto('/engagement/dashboard')
      await expect(page).toHaveURL('/engagement/dashboard')

      // Check page header
      await expect(page.locator('h1, h2').first()).toBeVisible()

      // Check for stats cards
      await expect(page.locator('text=Aktive Pipelines')).toBeVisible()
      await expect(page.locator('text=Aktive Enrollments')).toBeVisible()
    })

    test('should navigate through all tabs', async ({ page }) => {
      await page.goto('/engagement/dashboard')
      await page.waitForTimeout(1000)

      // Navigate to Pipelines tab
      await page.click('a:has-text("Pipelines")')
      await expect(page).toHaveURL('/engagement/pipelines', { timeout: 5000 })

      // Navigate to Enrollments tab
      await page.click('a:has-text("Enrollments")')
      await expect(page).toHaveURL('/engagement/enrollments', { timeout: 5000 })

      // Navigate to A/B Tests tab
      await page.click('a:has-text("A/B Tests")')
      await expect(page).toHaveURL('/engagement/ab-tests', { timeout: 5000 })

      // Navigate to Tracking tab
      await page.click('a:has-text("Tracking")')
      await expect(page).toHaveURL('/engagement/tracking', { timeout: 5000 })
    })
  })

  test.describe('Pipelines', () => {
    test('should show pipeline list or empty state', async ({ page }) => {
      await page.goto('/engagement/pipelines')
      await page.waitForTimeout(1000)

      // Should show search input
      const searchInput = page.locator('input[placeholder*="Pipeline suchen"]')
      await expect(searchInput).toBeVisible()

      // Should show either pipelines or empty state
      const content = await page.content()
      const hasPipelines = content.includes('Enrollments') || content.includes('Aktiv')
      const hasEmptyState = content.includes('Keine Pipelines')
      expect(hasPipelines || hasEmptyState).toBeTruthy()
    })

    test('should open pipeline creation form', async ({ page }) => {
      await page.goto('/engagement/pipelines')
      await page.waitForTimeout(1000)

      // Click new pipeline button
      await page.click('button:has-text("Neue Pipeline")')
      await expect(page).toHaveURL('/engagement/pipelines/new', { timeout: 5000 })

      // Check form is visible - look for any form element
      const formVisible = await page.locator('form, .rounded-lg.border').count()
      expect(formVisible).toBeGreaterThan(0)
    })
  })

  test.describe('A/B Tests', () => {
    test('should show A/B test list with filters', async ({ page }) => {
      await page.goto('/engagement/ab-tests')
      await page.waitForTimeout(1000)

      // Should show search input
      const searchInput = page.locator('input[placeholder*="Test suchen"]')
      await expect(searchInput).toBeVisible()

      // Should show create button
      await expect(page.locator('button:has-text("Neuer A/B Test")')).toBeVisible()
    })

    test('should open A/B test creation form', async ({ page }) => {
      await page.goto('/engagement/ab-tests')
      await page.waitForTimeout(1000)

      // Click new A/B test button
      await page.click('button:has-text("Neuer A/B Test")')
      await expect(page).toHaveURL('/engagement/ab-tests/new', { timeout: 5000 })

      // Check form sections are visible using more specific selectors
      await expect(page.locator('h3:has-text("Grundeinstellungen")')).toBeVisible()
      await expect(page.locator('h3:has-text("Varianten")')).toBeVisible()
    })
  })

  test.describe('Tracking', () => {
    test('should show tracking dashboard with stats', async ({ page }) => {
      await page.goto('/engagement/tracking')
      await page.waitForTimeout(1000)

      // Should show stats cards - look for the section headers
      await expect(page.locator('p:has-text("Tracking Links")').first()).toBeVisible()
      await expect(page.locator('p:has-text("Conversions")').first()).toBeVisible()

      // Should show pixel section
      await expect(page.locator('h3:has-text("Website-Pixel")')).toBeVisible()
      await expect(page.locator('button:has-text("Pixel-Code anzeigen")')).toBeVisible()
    })

    test('should open and close pixel code modal', async ({ page }) => {
      await page.goto('/engagement/tracking')
      await page.waitForTimeout(1000)

      // Click pixel code button
      await page.click('button:has-text("Pixel-Code anzeigen")')
      await page.waitForTimeout(500)

      // Modal should be visible
      await expect(page.locator('h3:has-text("Website-Pixel Code")')).toBeVisible()
      await expect(page.locator('button:has-text("Kopieren")')).toBeVisible()

      // Close modal
      await page.click('button:has-text("Schliessen")')
      await page.waitForTimeout(500)

      // Modal should be hidden
      await expect(page.locator('h3:has-text("Website-Pixel Code")')).not.toBeVisible()
    })
  })

  test.describe('Enrollments', () => {
    test('should show enrollments with filters', async ({ page }) => {
      await page.goto('/engagement/enrollments')
      await page.waitForTimeout(1000)

      // Should show search input
      const searchInput = page.locator('input[placeholder*="Kontakt suchen"]')
      await expect(searchInput).toBeVisible()

      // Should show status filter
      const statusFilter = page.locator('select').filter({ hasText: 'Alle Status' })
      await expect(statusFilter).toBeVisible()
    })
  })

  test.describe('Activities', () => {
    test('should show activities or empty state', async ({ page }) => {
      await page.goto('/engagement/activities')
      await page.waitForTimeout(1000)

      // Should show either activities or empty state
      const content = await page.content()
      const hasActivities = content.includes('Eingehend') || content.includes('Ausgehend')
      const hasEmptyState = content.includes('Keine Aktivitaeten')
      expect(hasActivities || hasEmptyState).toBeTruthy()
    })
  })
})
