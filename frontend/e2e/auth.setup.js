import { test as setup, expect } from '@playwright/test'
import path from 'path'

const authFile = path.join(import.meta.dirname, '../.playwright/.auth/user.json')

setup('authenticate', async ({ page }) => {
  await page.goto('/login')

  // Login
  await page.fill('input[type="email"]', 'team@go4.energy')
  await page.fill('input[type="password"]', 'changeme')
  await page.click('button[type="submit"]')

  // Wait for redirect to desktop
  await expect(page).toHaveURL('/', { timeout: 10000 })

  // Save auth state
  await page.context().storageState({ path: authFile })
})
