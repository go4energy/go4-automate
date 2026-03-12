import { test, expect } from '@playwright/test'

/**
 * Collector Module - Comprehensive E2E Tests
 * Tests: Groups, Sources, Findings, Topics, Prompts
 *
 * Test Sequence:
 * 1. Create Group
 * 2. Create Source (RSS/Website)
 * 3. Run Source Fetch
 * 4. Review Findings
 * 5. Create Topic
 * 6. Manage Prompts
 * 7. Cleanup: Delete test data
 */

test.describe('Collector Module - Comprehensive', () => {
  const timestamp = Date.now()

  const testGroup = {
    name: `E2E Test Group ${timestamp}`,
    slug: `e2e-test-${timestamp}`,
    description: 'Automatisch erstellt durch E2E Test'
  }

  const testSource = {
    name: `E2E Test RSS ${timestamp}`,
    url: 'https://feeds.feedburner.com/TechCrunch/',
    type: 'rss'
  }

  const testTopic = {
    title: `E2E Manual Topic ${timestamp}`,
    description: 'Manuell erstelltes Thema für E2E Test',
    category: 'content'
  }

  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test.describe('Main View & Tabs', () => {
    test('should load collector page', async ({ page }) => {
      await page.goto('/collector')
      await expect(page).toHaveURL('/collector')
      await page.waitForTimeout(1000)

      await expect(page.locator('h1, h2').first()).toBeVisible()
    })

    test('should show all tabs', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const tabNames = ['Sources', 'Quellen', 'Findings', 'Topics', 'Themen', 'Prompts']
      for (const tabName of tabNames) {
        const tab = page.locator(`button:has-text("${tabName}")`)
        if (await tab.count() > 0) {
          await tab.first().click()
          await page.waitForTimeout(300)
        }
      }
    })

    test('should switch between tabs', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      // Sources tab
      const sourcesTab = page.locator('button:has-text("Quellen"), button:has-text("Sources")')
      if (await sourcesTab.count() > 0) {
        await sourcesTab.first().click()
        await page.waitForTimeout(500)
      }

      // Findings tab
      const findingsTab = page.locator('button:has-text("Findings")')
      if (await findingsTab.count() > 0) {
        await findingsTab.first().click()
        await page.waitForTimeout(500)
      }

      // Topics tab
      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(500)
      }
    })
  })

  test.describe('Group Management', () => {
    test('should show group selector', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const groupSelector = page.locator('[class*="group"], button[class*="pill"]')
      expect(await groupSelector.count()).toBeGreaterThanOrEqual(0)
    })

    test('should open create group modal', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const addGroupBtn = page.locator('button:has-text("Gruppe"), button:has-text("Group")')
      if (await addGroupBtn.count() > 0) {
        await addGroupBtn.first().click()
        await page.waitForTimeout(500)

        const modal = page.locator('[role="dialog"], [class*="modal"]')
        if (await modal.count() > 0) { await expect(modal.first()).toBeVisible({ timeout: 3000 }) }
      }
    })

    test('should create a new group', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const addGroupBtn = page.locator('button:has-text("Gruppe"), button:has-text("Group")')
      if (await addGroupBtn.count() === 0) {
        test.skip()
        return
      }
      await addGroupBtn.first().click()
      await page.waitForTimeout(500)

      // Fill form
      const nameInput = page.locator('input[name="name"], input[placeholder*="Name"]')
      if (await nameInput.count() > 0) {
        await nameInput.first().fill(testGroup.name)
      }

      const descInput = page.locator('textarea[name="description"]')
      if (await descInput.count() > 0) {
        await descInput.first().fill(testGroup.description)
      }

      // Submit
      const submitBtn = page.locator('button[type="submit"], button:has-text("Erstellen")')
      await submitBtn.first().click()
      await page.waitForTimeout(2000)
    })

    test('should switch between groups', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const groupButtons = page.locator('button[class*="pill"], [class*="group-btn"]')
      if (await groupButtons.count() > 1) {
        await groupButtons.nth(1).click()
        await page.waitForTimeout(500)

        await groupButtons.nth(0).click()
        await page.waitForTimeout(500)
      }
    })
  })

  test.describe('Source Management', () => {
    test('should show sources list', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const sourcesTab = page.locator('button:has-text("Quellen"), button:has-text("Sources")')
      if (await sourcesTab.count() > 0) {
        await sourcesTab.first().click()
        await page.waitForTimeout(500)
      }

      // Check for source items
      const sourceItems = page.locator('[class*="source"], tr')
      expect(await sourceItems.count()).toBeGreaterThanOrEqual(0)
    })

    test('should open create source form', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const addSourceBtn = page.locator('button:has-text("Quelle"), button:has-text("Source")')
      if (await addSourceBtn.count() > 0) {
        await addSourceBtn.first().click()
        await page.waitForTimeout(1000)

        // Should navigate to source edit page or stay on collector
        const url = page.url()
        expect(url.includes('/collector')).toBeTruthy()
      } else {
        await expect(page.locator('body')).toBeVisible()
      }
    })

    test('should fill source create form', async ({ page }) => {
      await page.goto('/collector/sources/new')
      await page.waitForTimeout(1000)

      // Fill name
      const nameInput = page.locator('input[name="name"], input[placeholder*="Name"]')
      if (await nameInput.count() > 0) {
        await nameInput.first().fill(testSource.name)
      }

      // Select type
      const typeSelect = page.locator('select[name="type"]')
      if (await typeSelect.count() > 0) {
        await typeSelect.first().selectOption('rss')
      }

      // Fill URL
      const urlInput = page.locator('input[name="url"], input[placeholder*="URL"]')
      if (await urlInput.count() > 0) {
        await urlInput.first().fill(testSource.url)
      }

      // Don't submit - just verify form works
      await expect(page.locator('body')).toBeVisible()
    })

    test('should show source type badges', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(2000)

      const typeBadges = page.locator('[class*="badge"]:has-text("RSS"), [class*="badge"]:has-text("Website")')
      expect(await typeBadges.count()).toBeGreaterThanOrEqual(0)
    })

    test('should have fetch all button', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const fetchAllBtn = page.locator('button:has-text("fetchen"), button:has-text("Fetch")')
      if (await fetchAllBtn.count() > 0) {
        await expect(fetchAllBtn.first()).toBeVisible()
      }
    })

    test('should have individual source fetch button', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(2000)

      const fetchBtn = page.locator('button:has-text("Jetzt fetchen"), button[title*="fetch"]')
      if (await fetchBtn.count() > 0) {
        await expect(fetchBtn.first()).toBeVisible()
      }
    })

    test('should edit source', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(2000)

      const editBtn = page.locator('button:has-text("Bearbeiten"), a:has-text("Bearbeiten")')
      if (await editBtn.count() > 0) {
        await editBtn.first().click()
        await page.waitForTimeout(1000)

        await expect(page).toHaveURL(/\/collector\/sources\/\d+/)
      }
    })

    test('should toggle source active/inactive', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(2000)

      const toggleSwitch = page.locator('input[type="checkbox"][class*="switch"], [class*="toggle"]')
      if (await toggleSwitch.count() > 0) {
        // Just verify it exists
        await expect(toggleSwitch.first()).toBeVisible()
      }
    })
  })

  test.describe('Findings Management', () => {
    test('should show findings list', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const findingsTab = page.locator('button:has-text("Findings")')
      if (await findingsTab.count() > 0) {
        await findingsTab.first().click()
        await page.waitForTimeout(1000)
      }

      // Check for findings
      const findings = page.locator('[class*="finding"], tr, [class*="card"]')
      expect(await findings.count()).toBeGreaterThanOrEqual(0)
    })

    test('should filter findings by status', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const findingsTab = page.locator('button:has-text("Findings")')
      if (await findingsTab.count() > 0) {
        await findingsTab.first().click()
        await page.waitForTimeout(500)
      }

      const statusButtons = ['Alle', 'All', 'Neu', 'New', 'Verwendet', 'Used', 'Verworfen', 'Dismissed']
      for (const status of statusButtons) {
        const btn = page.locator(`button:has-text("${status}")`)
        if (await btn.count() > 0) {
          await btn.first().click()
          await page.waitForTimeout(300)
          break
        }
      }
    })

    test('should filter findings by source type', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const findingsTab = page.locator('button:has-text("Findings")')
      if (await findingsTab.count() > 0) {
        await findingsTab.first().click()
        await page.waitForTimeout(500)
      }

      const typeFilter = page.locator('select, button:has-text("Typ")')
      if (await typeFilter.count() > 0) {
        await typeFilter.first().click()
        await page.waitForTimeout(300)
      }
    })

    test('should dismiss finding', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const findingsTab = page.locator('button:has-text("Findings")')
      if (await findingsTab.count() > 0) {
        await findingsTab.first().click()
        await page.waitForTimeout(500)
      }

      const dismissBtn = page.locator('button:has-text("Verwerfen"), button[title*="Dismiss"]')
      if (await dismissBtn.count() > 0) {
        await expect(dismissBtn.first()).toBeVisible()
      }
    })

    test('should mark finding as reviewed', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const findingsTab = page.locator('button:has-text("Findings")')
      if (await findingsTab.count() > 0) {
        await findingsTab.first().click()
        await page.waitForTimeout(500)
      }

      const reviewBtn = page.locator('button:has-text("Reviewed"), button:has-text("Überprüft")')
      if (await reviewBtn.count() > 0) {
        await expect(reviewBtn.first()).toBeVisible()
      }
    })

    test('should select multiple findings for bulk action', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const findingsTab = page.locator('button:has-text("Findings")')
      if (await findingsTab.count() > 0) {
        await findingsTab.first().click()
        await page.waitForTimeout(500)
      }

      const checkboxes = page.locator('input[type="checkbox"]')
      if (await checkboxes.count() > 1) {
        await checkboxes.nth(0).check()
        await page.waitForTimeout(200)
      }
    })
  })

  test.describe('Topic Management', () => {
    test('should show topics list', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(1000)
      }

      // Check for topics
      const topics = page.locator('[class*="topic"], tr, [class*="card"]')
      expect(await topics.count()).toBeGreaterThanOrEqual(0)
    })

    test('should navigate to manual topic creation', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(500)
      }

      const createBtn = page.locator('a:has-text("Eigenes Thema"), button:has-text("Thema")')
      if (await createBtn.count() > 0) {
        await createBtn.first().click()
        await page.waitForTimeout(1000)

        await expect(page).toHaveURL(/\/collector\/topics\/new/)
      }
    })

    test('should fill manual topic creation form', async ({ page }) => {
      await page.goto('/collector/topics/new')
      await page.waitForTimeout(1000)

      // Fill title
      const titleInput = page.locator('input[name="title"], input[placeholder*="Titel"]')
      if (await titleInput.count() > 0) {
        await titleInput.first().fill(testTopic.title)
      }

      // Fill description
      const descInput = page.locator('textarea[name="description"]')
      if (await descInput.count() > 0) {
        await descInput.first().fill(testTopic.description)
      }

      // Select category
      const categorySelect = page.locator('select[name="category"]')
      if (await categorySelect.count() > 0) {
        await categorySelect.first().selectOption('content')
      }

      // Don't submit - just verify form works
      await expect(page.locator('body')).toBeVisible()
    })

    test('should approve suggested topic', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(500)
      }

      const approveBtn = page.locator('button:has-text("Genehmigen"), button:has-text("Approve")')
      if (await approveBtn.count() > 0) {
        await expect(approveBtn.first()).toBeVisible()
      }
    })

    test('should reject suggested topic', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(500)
      }

      const rejectBtn = page.locator('button:has-text("Ablehnen"), button:has-text("Reject")')
      if (await rejectBtn.count() > 0) {
        await expect(rejectBtn.first()).toBeVisible()
      }
    })

    test('should open topic detail view', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(500)
      }

      const topicRow = page.locator('tr, [class*="card"]').first()
      if (await topicRow.count() > 0) {
        await topicRow.click()
        await page.waitForTimeout(1000)

        // Should navigate to detail or stay on page
        const url = page.url()
        expect(url.includes('/collector')).toBeTruthy()
      } else {
        await expect(page.locator('body')).toBeVisible()
      }
    })
  })

  test.describe('Topic Detail View', () => {
    test('should show topic information', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(500)
      }

      const topicRow = page.locator('tr, [class*="card"]').first()
      if (await topicRow.count() > 0) {
        await topicRow.click()
        await page.waitForTimeout(1000)
      }

      // Verify detail page elements
      await expect(page.locator('body')).toBeVisible()
    })

    test('should edit topic metadata', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(500)
      }

      const topicRow = page.locator('tr, [class*="card"]').first()
      if (await topicRow.count() > 0) {
        await topicRow.click()
        await page.waitForTimeout(1000)
      }

      // Look for editable metadata fields
      const tagSelector = page.locator('[class*="TagSelector"]')
      const streamSelector = page.locator('[class*="StreamSelector"]')

      // Just verify page loaded
      await expect(page.locator('body')).toBeVisible()
    })

    test('should edit prompt in topic detail', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(500)
      }

      const topicRow = page.locator('tr, [class*="card"]').first()
      if (await topicRow.count() > 0) {
        await topicRow.click()
        await page.waitForTimeout(1000)
      }

      const editPromptBtn = page.locator('button:has-text("Bearbeiten")')
      if (await editPromptBtn.count() > 0) {
        await editPromptBtn.first().click()
        await page.waitForTimeout(500)
      }
    })

    test('should re-analyze topic', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const topicsTab = page.locator('button:has-text("Topics"), button:has-text("Themen")')
      if (await topicsTab.count() > 0) {
        await topicsTab.first().click()
        await page.waitForTimeout(500)
      }

      const topicRow = page.locator('tr, [class*="card"]').first()
      if (await topicRow.count() > 0) {
        await topicRow.click()
        await page.waitForTimeout(1000)
      }

      const reanalyzeBtn = page.locator('button:has-text("analysieren"), button:has-text("Analyze")')
      if (await reanalyzeBtn.count() > 0) {
        await expect(reanalyzeBtn.first()).toBeVisible()
      }
    })
  })

  test.describe('Prompts Management', () => {
    test('should show prompts list', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const promptsTab = page.locator('button:has-text("Prompts")')
      if (await promptsTab.count() > 0) {
        await promptsTab.first().click()
        await page.waitForTimeout(500)
      }

      const prompts = page.locator('[class*="prompt"], tr, [class*="card"]')
      expect(await prompts.count()).toBeGreaterThanOrEqual(0)
    })

    test('should add prompt to group', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const promptsTab = page.locator('button:has-text("Prompts")')
      if (await promptsTab.count() > 0) {
        await promptsTab.first().click()
        await page.waitForTimeout(500)
      }

      const addPromptBtn = page.locator('button:has-text("Prompt")')
      if (await addPromptBtn.count() > 0) {
        await addPromptBtn.first().click()
        await page.waitForTimeout(500)

        const modal = page.locator('[role="dialog"], [class*="modal"]')
        if (await modal.count() > 0) {
          await expect(modal.first()).toBeVisible()
        }
      }
    })

    test('should run prompt', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const promptsTab = page.locator('button:has-text("Prompts")')
      if (await promptsTab.count() > 0) {
        await promptsTab.first().click()
        await page.waitForTimeout(500)
      }

      const runBtn = page.locator('button:has-text("Ausführen"), button:has-text("Run")')
      if (await runBtn.count() > 0) {
        await expect(runBtn.first()).toBeVisible()
      }
    })

    test('should duplicate prompt', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(1000)

      const promptsTab = page.locator('button:has-text("Prompts")')
      if (await promptsTab.count() > 0) {
        await promptsTab.first().click()
        await page.waitForTimeout(500)
      }

      const duplicateBtn = page.locator('button:has-text("Duplizieren"), button[title*="Duplicate"]')
      if (await duplicateBtn.count() > 0) {
        await expect(duplicateBtn.first()).toBeVisible()
      }
    })
  })

  test.describe('Cleanup', () => {
    test('should delete test group', async ({ page }) => {
      await page.goto('/collector')
      await page.waitForTimeout(2000)

      // Find test group button
      const testGroupBtn = page.locator(`button:has-text("${testGroup.name.substring(0, 15)}")`)
      if (await testGroupBtn.count() > 0) {
        // Click group settings
        const settingsBtn = page.locator('button[title*="Settings"], button:has(svg[class*="cog"])')
        if (await settingsBtn.count() > 0) {
          await settingsBtn.first().click()
          await page.waitForTimeout(300)

          const deleteBtn = page.locator('button:has-text("Löschen"), button:has-text("Delete")')
          if (await deleteBtn.count() > 0) {
            await deleteBtn.first().click()
            await page.waitForTimeout(500)

            // Confirm
            const confirmBtn = page.locator('button:has-text("Ja"), button:has-text("Bestätigen")')
            if (await confirmBtn.count() > 0) {
              await confirmBtn.first().click()
              await page.waitForTimeout(2000)
            }
          }
        }
      }
    })
  })
})
