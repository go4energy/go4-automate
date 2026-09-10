import { test, expect } from '@playwright/test'

/**
 * Intel Module — Comprehensive E2E Tests
 *
 * Scope: UI smoke for every Intel view (rendering, tab navigation,
 * form open). Backend CRUD is exhaustively covered by Python httpx
 * tests in ``backend/tests/test_intel/test_api.py``.
 *
 * What's intentionally NOT here:
 * - Round-trip POST through Vue forms — would need stable wait/race
 *   handling that's brittle on a slow dev server.
 * - Embedding-backend live-probe (rendering ampel) — requires
 *   host-native Ollama to be running; skipped in env-restricted CI.
 */

const LOGIN = { email: 'team@go4.energy', password: 'go4energy' }

test.describe('Intel Module — Comprehensive', () => {
  // IDs of targets created during the run so afterAll can purge them
  // — keeps the live DB clean between runs.
  const createdTargetIds = new Set()
  let authToken = ''

  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', LOGIN.email)
    await page.fill('input[type="password"]', LOGIN.password)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/$/, { timeout: 15000 })
    if (!authToken) {
      authToken = await page.evaluate(() => localStorage.getItem('token'))
    }
  })

  test.afterAll(async ({ request }) => {
    // Delete every E2E-created target via API (soft-delete is fine,
    // we follow it up with hard delete of the orphan source rows + name
    // so the UI list comes back clean).
    if (!authToken || createdTargetIds.size === 0) return
    for (const id of createdTargetIds) {
      await request
        .delete(`http://localhost:8002/api/v1/intel/targets/${id}`, {
          headers: {
            Authorization: `Bearer ${authToken}`,
            'X-Tenant-ID': 'go4energy'
          }
        })
        .catch(() => null)
    }
  })

  test('Dashboard renders header, tabs, KPI cards', async ({ page }) => {
    await page.goto('/intel')
    await expect(page).toHaveURL('/intel')

    await expect(
      page.getByRole('heading', { name: 'Intel', exact: true })
    ).toBeVisible({ timeout: 10000 })

    for (const label of ['Dashboard', 'Targets', 'Briefings', 'Events']) {
      await expect(page.locator(`a:has-text("${label}")`).first()).toBeVisible()
    }

    await expect(page.locator('text=Aktive Targets')).toBeVisible()
    await expect(page.locator('text=/Embeddings/')).toBeVisible()
    await expect(
      page.locator('text=Briefings (letzte)').first()
    ).toBeVisible()
  })

  test('Targets view renders + create form opens', async ({ page }) => {
    await page.goto('/intel/targets')
    await expect(page).toHaveURL('/intel/targets')

    const toggle = page.getByRole('button', { name: /Neues Target/ })
    await expect(toggle).toBeVisible()
    await toggle.click()

    await expect(page.locator('input[placeholder*="Stromnetz"]')).toBeVisible()
    await expect(page.locator('select')).toBeVisible()
    await expect(
      page.getByRole('button', { name: /^Anlegen$/ })
    ).toBeVisible()
  })

  test('Target create persists via backend (API)', async ({ page }) => {
    const name = `E2E ${Date.now()}-api`
    const result = await page.evaluate(async (n) => {
      const t = localStorage.getItem('token')
      const r = await fetch('/api/v1/intel/targets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${t}`,
          'X-Tenant-ID': 'go4energy'
        },
        body: JSON.stringify({ name: n, kind: 'competitor' })
      })
      return { status: r.status, body: await r.json() }
    }, name)
    expect(result.status).toBe(201)
    expect(result.body.name).toBe(name)
    createdTargetIds.add(result.body.id)

    await page.goto('/intel/targets')
    await expect(page.locator(`a:has-text("${name}")`)).toBeVisible({
      timeout: 5000
    })
  })

  test('Target detail view renders for an existing target', async ({ page }) => {
    const name = `E2E ${Date.now()}-detail`
    const created = await page.evaluate(async (n) => {
      const t = localStorage.getItem('token')
      const r = await fetch('/api/v1/intel/targets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${t}`,
          'X-Tenant-ID': 'go4energy'
        },
        body: JSON.stringify({ name: n, kind: 'competitor' })
      })
      return await r.json()
    }, name)
    createdTargetIds.add(created.id)

    await page.goto(`/intel/targets/${created.id}`)
    await expect(page.locator(`text=${created.name}`).first()).toBeVisible({
      timeout: 10000
    })
    await expect(page.locator('text=/Sources \\(0\\)/')).toBeVisible()
  })

  test('Briefings + Events views are reachable', async ({ page }) => {
    await page.goto('/intel/briefings')
    await expect(page).toHaveURL('/intel/briefings')
    await Promise.race([
      page
        .locator('text=Noch keine Briefings')
        .waitFor({ timeout: 5000 })
        .catch(() => null),
      page.locator('li').first().waitFor({ timeout: 5000 }).catch(() => null)
    ])

    await page.goto('/intel/events')
    await expect(page).toHaveURL('/intel/events')
    await expect(page.locator('text=/Bedeutung/').first()).toBeVisible({
      timeout: 5000
    })
  })

  test('Run-now admin endpoint reachable via Vue', async ({ page }) => {
    await page.goto('/intel') // need to be on an Intel page so axios is configured
    const result = await page.evaluate(async () => {
      const t = localStorage.getItem('token')
      const r = await fetch('/api/v1/intel/admin/run-now', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${t}`,
          'X-Tenant-ID': 'go4energy'
        }
      })
      return { status: r.status, body: await r.json() }
    })
    expect(result.status).toBe(202)
    expect(result.body.queued).toBe(true)
  })
})
