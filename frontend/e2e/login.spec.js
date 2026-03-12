import { test, expect } from '@playwright/test'

test.describe('Login', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('should login successfully', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')

    // Should redirect to desktop
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[type="email"]', 'wrong@email.com')
    await page.fill('input[type="password"]', 'wrongpassword')
    await page.click('button[type="submit"]')

    // Should stay on login page (not redirect)
    await page.waitForTimeout(2000)
    await expect(page).toHaveURL('/login')
  })

  test('should redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/surveys')
    await expect(page).toHaveURL('/login')
  })
})
