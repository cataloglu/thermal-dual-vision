import { test, expect, Page } from '@playwright/test'

const mockRecordingsApi = async (page: Page, recordings: any[]) => {
  let current = recordings
  let deleteCalls = 0

  await page.route('**/api/recordings**', async route => {
    const method = route.request().method()
    if (method === 'GET') {
      await route.fulfill({
        json: {
          recordings: current,
          total: current.length,
          page: 1,
          page_size: 20,
        },
      })
      return
    }
    if (method === 'DELETE') {
      deleteCalls += 1
      await route.fulfill({
        json: { deleted: true, id: route.request().url().split('/').pop() },
      })
      return
    }
    await route.fulfill({ status: 405 })
  })

  await page.route('**/api/cameras**', async route => {
    await route.fulfill({
      json: {
        cameras: [
          { id: 'cam-1', name: 'Front Door', type: 'thermal' },
        ],
      },
    })
  })

  return () => deleteCalls
}

test.describe('Recordings page', () => {
  test('renders list and deletes recording', async ({ page }) => {
    const getDeleteCalls = await mockRecordingsApi(page, [
      {
        id: 'rec-1',
        camera_id: 'cam-1',
        start_time: new Date().toISOString(),
        end_time: new Date().toISOString(),
        duration_seconds: 12,
        file_size_mb: 1.2,
        file_path: '/recordings/rec-1.mp4',
      },
    ])

    await page.goto('/recordings')
    await expect(page.getByText('cam-1', { exact: false })).toBeVisible()
    page.once('dialog', dialog => dialog.accept())
    await page.getByRole('button', { name: /Delete|Sil/i }).click()
    await page.waitForTimeout(300)
    expect(getDeleteCalls()).toBeGreaterThan(0)
  })

  test('shows empty state', async ({ page }) => {
    await mockRecordingsApi(page, [])
    await page.goto('/recordings')
    await expect(page.getByText(/no data|veri yok/i).first()).toBeVisible()
  })
})
