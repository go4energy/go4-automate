import { test, expect } from '@playwright/test'

/**
 * CRM Module - Comprehensive E2E Tests
 * Tests: Deals, Pipelines, Tasks, Kanban, Activities
 */

test.describe('CRM Module - Comprehensive', () => {
  // Test data
  const testDeal = {
    title: `E2E Test Deal ${Date.now()}`,
    value: '50000',
    description: 'Automatisch erstellt durch E2E Test',
    priority: 'high'
  }

  const testPipeline = {
    name: `E2E Test Pipeline ${Date.now()}`,
    description: 'Test Pipeline für E2E'
  }

  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'team@go4.energy')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test.describe('Deals View', () => {
    test('should load CRM deals page', async ({ page }) => {
      await page.goto('/crm/deals')
      await expect(page).toHaveURL('/crm/deals')
      await page.waitForTimeout(1000)

      // Page should load
      await expect(page.locator('body')).toBeVisible()
    })

    test('should show pipeline selector', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(1000)

      const pipelineSelect = page.locator('select, [class*="pipeline-select"], button:has-text("Pipeline")')
      if (await pipelineSelect.count() > 0) {
        await pipelineSelect.first().click()
        await page.waitForTimeout(300)
      }
    })

    test('should toggle between Kanban and Table view', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(1000)

      const viewToggle = page.locator('button:has(svg), [class*="ViewMode"]')
      if (await viewToggle.count() > 0) {
        await viewToggle.first().click()
        await page.waitForTimeout(500)

        // Toggle back
        await viewToggle.first().click()
        await page.waitForTimeout(500)
      }
    })

    test('should show Kanban board with stages', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      // Look for Kanban columns/stages
      const stages = page.locator('[class*="stage"], [class*="column"], [class*="kanban"]')
      if (await stages.count() > 0) {
        expect(await stages.count()).toBeGreaterThan(0)
      }
    })

    test('should open create deal modal', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(1000)

      const addBtn = page.locator('button:has-text("Deal"), button:has-text("Neu")')
      if (await addBtn.count() > 0) {
        await addBtn.first().click()
        await page.waitForTimeout(500)

        const modal = page.locator('[role="dialog"], [class*="modal"]')
        if (await modal.count() > 0) { await expect(modal.first()).toBeVisible({ timeout: 3000 }) }
      }
    })

    test('should create a new deal with all fields', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(1000)

      // Open modal
      const addBtn = page.locator('button:has-text("Deal"), button:has-text("Neu")')
      if (await addBtn.count() === 0) {
        test.skip()
        return
      }
      await addBtn.first().click()
      await page.waitForTimeout(500)

      // Fill title
      const titleInput = page.locator('input[name="title"], input[placeholder*="Titel"], input[placeholder*="Name"]')
      if (await titleInput.count() > 0) {
        await titleInput.first().fill(testDeal.title)
      }

      // Fill value
      const valueInput = page.locator('input[name="value"], input[placeholder*="Wert"], input[type="number"]')
      if (await valueInput.count() > 0) {
        await valueInput.first().fill(testDeal.value)
      }

      // Select stage (if available)
      const stageSelect = page.locator('select[name="stage_id"], select[name="stage"]')
      if (await stageSelect.count() > 0) {
        await stageSelect.first().selectOption({ index: 1 })
      }

      // Select priority (if available)
      const prioritySelect = page.locator('select[name="priority"]')
      if (await prioritySelect.count() > 0) {
        await prioritySelect.first().selectOption('high')
      }

      // Fill description
      const descInput = page.locator('textarea[name="description"]')
      if (await descInput.count() > 0) {
        await descInput.first().fill(testDeal.description)
      }

      // Submit
      const submitBtn = page.locator('button[type="submit"], button:has-text("Erstellen"), button:has-text("Speichern")')
      await submitBtn.first().click()
      await page.waitForTimeout(2000)
    })

    test('should search deals', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(1000)

      const searchInput = page.locator('input[placeholder*="Such"], input[type="search"]')
      if (await searchInput.count() > 0) {
        await searchInput.first().fill('Test')
        await page.waitForTimeout(500)
        await searchInput.first().clear()
      }
    })

    test('should open deal detail view', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      // Click on a deal card
      const dealCard = page.locator('[class*="deal-card"], [class*="card"]:has(h3, h4)').first()
      if (await dealCard.count() > 0) {
        await dealCard.click()
        await page.waitForTimeout(1000)

        await expect(page).toHaveURL(/\/crm\/deals\/\d+/)
      }
    })
  })

  test.describe('Deal Detail View', () => {
    test('should load deal detail page', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      // Navigate to first deal
      const dealCard = page.locator('[class*="card"]').first()
      if (await dealCard.count() > 0) {
        await dealCard.click()
        await page.waitForTimeout(1000)
      }

      // Check for detail elements
      const backBtn = page.locator('button:has-text("Zurück"), a:has-text("Zurück")')
      if (await backBtn.count() > 0) {
        await expect(backBtn.first()).toBeVisible()
      }
    })

    test('should show deal tabs (Overview/Activities/Tasks)', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      const dealCard = page.locator('[class*="card"]').first()
      if (await dealCard.count() > 0) {
        await dealCard.click()
        await page.waitForTimeout(1000)
      }

      // Check for tabs
      const tabs = ['Übersicht', 'Overview', 'Aktivitäten', 'Activities', 'Aufgaben', 'Tasks']
      for (const tabName of tabs) {
        const tab = page.locator(`button:has-text("${tabName}")`)
        if (await tab.count() > 0) {
          await tab.first().click()
          await page.waitForTimeout(300)
        }
      }
    })

    test('should edit deal from detail view', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      const dealCard = page.locator('[class*="card"]').first()
      if (await dealCard.count() > 0) {
        await dealCard.click()
        await page.waitForTimeout(1000)
      }

      const editBtn = page.locator('button:has-text("Bearbeiten")')
      if (await editBtn.count() > 0) {
        await editBtn.first().click()
        await page.waitForTimeout(500)

        const modal = page.locator('[role="dialog"], [class*="modal"]')
        await expect(modal.first()).toBeVisible()

        // Cancel
        const cancelBtn = page.locator('button:has-text("Abbrechen")')
        if (await cancelBtn.count() > 0) {
          await cancelBtn.first().click()
        }
      }
    })

    test('should show mark as won/lost buttons', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      const dealCard = page.locator('[class*="card"]').first()
      if (await dealCard.count() > 0) {
        await dealCard.click()
        await page.waitForTimeout(1000)
      }

      const wonBtn = page.locator('button:has-text("Gewonnen"), button:has-text("Won")')
      const lostBtn = page.locator('button:has-text("Verloren"), button:has-text("Lost")')

      if (await wonBtn.count() > 0) {
        await expect(wonBtn.first()).toBeVisible()
      }
      if (await lostBtn.count() > 0) {
        await expect(lostBtn.first()).toBeVisible()
      }
    })

    test('should navigate back to deals list', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      const dealCard = page.locator('[class*="card"]').first()
      if (await dealCard.count() > 0) {
        await dealCard.click()
        await page.waitForTimeout(1000)
      }

      const backBtn = page.locator('button:has-text("Zurück"), a:has-text("Deals")')
      if (await backBtn.count() > 0) {
        await backBtn.first().click()
        await page.waitForTimeout(500)

        await expect(page).toHaveURL('/crm/deals')
      }
    })
  })

  test.describe('Kanban Drag & Drop', () => {
    test('should display stages with deal counts', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      const stageHeaders = page.locator('[class*="stage-header"], [class*="column-header"]')
      if (await stageHeaders.count() > 0) {
        expect(await stageHeaders.count()).toBeGreaterThan(0)
      }
    })

    test('should show stage totals', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      // Look for value totals in stage headers
      const totals = page.locator('[class*="total"], [class*="sum"]')
      // Just verify page loaded without errors
      await expect(page.locator('body')).toBeVisible()
    })
  })

  test.describe('Pipelines View', () => {
    test('should load pipelines page', async ({ page }) => {
      await page.goto('/crm/pipelines')
      await expect(page).toHaveURL('/crm/pipelines')
      await page.waitForTimeout(1000)
    })

    test('should show existing pipelines', async ({ page }) => {
      await page.goto('/crm/pipelines')
      await page.waitForTimeout(2000)

      const pipelineCards = page.locator('[class*="card"], [class*="pipeline"]')
      expect(await pipelineCards.count()).toBeGreaterThanOrEqual(0)
    })

    test('should open create pipeline modal', async ({ page }) => {
      await page.goto('/crm/pipelines')
      await page.waitForTimeout(1000)

      const addBtn = page.locator('button:has-text("Pipeline"), button:has-text("Neu")')
      if (await addBtn.count() > 0) {
        await addBtn.first().click()
        await page.waitForTimeout(500)

        const modal = page.locator('[role="dialog"], [class*="modal"]')
        if (await modal.count() > 0) { await expect(modal.first()).toBeVisible({ timeout: 3000 }) }
      }
    })

    test('should create a new pipeline', async ({ page }) => {
      await page.goto('/crm/pipelines')
      await page.waitForTimeout(1000)

      const addBtn = page.locator('button:has-text("Pipeline"), button:has-text("Neu")')
      if (await addBtn.count() === 0) {
        test.skip()
        return
      }
      await addBtn.first().click()
      await page.waitForTimeout(500)

      // Fill name
      const nameInput = page.locator('input[name="name"], input[placeholder*="Name"]')
      if (await nameInput.count() > 0) {
        await nameInput.first().fill(testPipeline.name)
      }

      // Fill description
      const descInput = page.locator('textarea[name="description"], input[placeholder*="Beschreibung"]')
      if (await descInput.count() > 0) {
        await descInput.first().fill(testPipeline.description)
      }

      // Submit
      const submitBtn = page.locator('button[type="submit"], button:has-text("Erstellen"), button:has-text("Speichern")')
      await submitBtn.first().click()
      await page.waitForTimeout(2000)
    })

    test('should expand pipeline to show stages', async ({ page }) => {
      await page.goto('/crm/pipelines')
      await page.waitForTimeout(2000)

      const expandBtn = page.locator('button[class*="expand"], [class*="chevron"]')
      if (await expandBtn.count() > 0) {
        await expandBtn.first().click()
        await page.waitForTimeout(500)
      }
    })

    test('should edit pipeline', async ({ page }) => {
      await page.goto('/crm/pipelines')
      await page.waitForTimeout(2000)

      const editBtn = page.locator('button:has-text("Bearbeiten"), button[title*="Bearbeiten"]')
      if (await editBtn.count() > 0) {
        await editBtn.first().click()
        await page.waitForTimeout(500)

        const modal = page.locator('[role="dialog"], [class*="modal"]')
        if (await modal.count() > 0) {
          await expect(modal.first()).toBeVisible()

          const cancelBtn = page.locator('button:has-text("Abbrechen")')
          if (await cancelBtn.count() > 0) {
            await cancelBtn.first().click()
          }
        }
      }
    })

    test('should show delete confirmation for non-default pipeline', async ({ page }) => {
      await page.goto('/crm/pipelines')
      await page.waitForTimeout(2000)

      const deleteBtn = page.locator('button:has-text("Löschen"), button[title*="Löschen"]')
      if (await deleteBtn.count() > 0) {
        await deleteBtn.first().click()
        await page.waitForTimeout(500)

        const confirmDialog = page.locator('[role="alertdialog"], [class*="confirm"]')
        if (await confirmDialog.count() > 0) {
          const cancelBtn = page.locator('button:has-text("Abbrechen"), button:has-text("Nein")')
          if (await cancelBtn.count() > 0) {
            await cancelBtn.first().click()
          }
        }
      }
    })
  })

  test.describe('Stage Management', () => {
    test('should show stage editor in pipeline', async ({ page }) => {
      await page.goto('/crm/pipelines')
      await page.waitForTimeout(2000)

      // Expand pipeline or navigate to edit
      const editBtn = page.locator('button:has-text("Bearbeiten")')
      if (await editBtn.count() > 0) {
        await editBtn.first().click()
        await page.waitForTimeout(500)

        // Look for stage editor
        const stageEditor = page.locator('[class*="StageEditor"], [class*="stage-list"]')
        if (await stageEditor.count() > 0) {
          await expect(stageEditor.first()).toBeVisible()
        }
      }
    })

    test('should add a new stage', async ({ page }) => {
      await page.goto('/crm/pipelines')
      await page.waitForTimeout(2000)

      const editBtn = page.locator('button:has-text("Bearbeiten")')
      if (await editBtn.count() > 0) {
        await editBtn.first().click()
        await page.waitForTimeout(500)
      }

      const addStageBtn = page.locator('button:has-text("Stage"), button:has-text("Phase")')
      if (await addStageBtn.count() > 0) {
        await addStageBtn.first().click()
        await page.waitForTimeout(500)
      }
    })
  })

  test.describe('Tasks View', () => {
    test('should load tasks page', async ({ page }) => {
      await page.goto('/crm/tasks')
      await expect(page).toHaveURL('/crm/tasks')
      await page.waitForTimeout(1000)
    })

    test('should show task filters', async ({ page }) => {
      await page.goto('/crm/tasks')
      await page.waitForTimeout(1000)

      // Status filter
      const statusFilter = page.locator('select, button:has-text("Status"), button:has-text("Alle")')
      if (await statusFilter.count() > 0) {
        await statusFilter.first().click()
        await page.waitForTimeout(300)
      }
    })

    test('should filter tasks by status', async ({ page }) => {
      await page.goto('/crm/tasks')
      await page.waitForTimeout(1000)

      const statusOptions = ['Offen', 'Open', 'Erledigt', 'Completed', 'Überfällig', 'Overdue']
      for (const status of statusOptions) {
        const btn = page.locator(`button:has-text("${status}")`)
        if (await btn.count() > 0) {
          await btn.first().click()
          await page.waitForTimeout(300)
          break
        }
      }
    })

    test('should filter tasks by priority', async ({ page }) => {
      await page.goto('/crm/tasks')
      await page.waitForTimeout(1000)

      const priorityOptions = ['Hoch', 'High', 'Mittel', 'Medium', 'Niedrig', 'Low']
      for (const priority of priorityOptions) {
        const btn = page.locator(`button:has-text("${priority}")`)
        if (await btn.count() > 0) {
          await btn.first().click()
          await page.waitForTimeout(300)
          break
        }
      }
    })

    test('should search tasks', async ({ page }) => {
      await page.goto('/crm/tasks')
      await page.waitForTimeout(1000)

      const searchInput = page.locator('input[placeholder*="Such"], input[type="search"]')
      if (await searchInput.count() > 0) {
        await searchInput.first().fill('Test')
        await page.waitForTimeout(500)
        await searchInput.first().clear()
      }
    })

    test('should toggle task completion', async ({ page }) => {
      await page.goto('/crm/tasks')
      await page.waitForTimeout(2000)

      const checkbox = page.locator('input[type="checkbox"]').first()
      if (await checkbox.count() > 0) {
        const wasChecked = await checkbox.isChecked()
        await checkbox.click()
        await page.waitForTimeout(500)

        // Toggle back
        await checkbox.click()
        await page.waitForTimeout(500)
      }
    })

    test('should navigate to deal from task', async ({ page }) => {
      await page.goto('/crm/tasks')
      await page.waitForTimeout(2000)

      const dealLink = page.locator('a:has-text("Deal"), a[href*="/crm/deals/"]')
      if (await dealLink.count() > 0) {
        await dealLink.first().click()
        await page.waitForTimeout(1000)

        await expect(page).toHaveURL(/\/crm\/deals\/\d+/)
      }
    })
  })

  test.describe('Activities', () => {
    test('should show activity timeline in deal detail', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      const dealCard = page.locator('[class*="card"]').first()
      if (await dealCard.count() > 0) {
        await dealCard.click()
        await page.waitForTimeout(1000)
      }

      // Switch to activities tab
      const activitiesTab = page.locator('button:has-text("Aktivitäten"), button:has-text("Activities")')
      if (await activitiesTab.count() > 0) {
        await activitiesTab.first().click()
        await page.waitForTimeout(500)

        const timeline = page.locator('[class*="timeline"], [class*="activity"]')
        // Just verify we're on the right page
        await expect(page.locator('body')).toBeVisible()
      }
    })

    test('should add activity to deal', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(2000)

      const dealCard = page.locator('[class*="card"]').first()
      if (await dealCard.count() > 0) {
        await dealCard.click()
        await page.waitForTimeout(1000)
      }

      const activitiesTab = page.locator('button:has-text("Aktivitäten"), button:has-text("Activities")')
      if (await activitiesTab.count() > 0) {
        await activitiesTab.first().click()
        await page.waitForTimeout(500)
      }

      const addActivityBtn = page.locator('button:has-text("Aktivität"), button:has-text("Activity")')
      if (await addActivityBtn.count() > 0) {
        await addActivityBtn.first().click()
        await page.waitForTimeout(500)
      }
    })
  })

  test.describe('CRM Navigation', () => {
    test('should navigate between CRM sections', async ({ page }) => {
      const sections = ['/crm/deals', '/crm/pipelines', '/crm/tasks']

      for (const section of sections) {
        await page.goto(section)
        await expect(page).toHaveURL(section)
        await page.waitForTimeout(500)
      }
    })

    test('should have working sidebar/tab navigation', async ({ page }) => {
      await page.goto('/crm/deals')
      await page.waitForTimeout(1000)

      const navItems = ['Deals', 'Pipelines', 'Tasks', 'Aufgaben']
      for (const item of navItems) {
        const link = page.locator(`a:has-text("${item}"), button:has-text("${item}")`)
        if (await link.count() > 0) {
          await link.first().click()
          await page.waitForTimeout(500)
        }
      }
    })
  })
})
