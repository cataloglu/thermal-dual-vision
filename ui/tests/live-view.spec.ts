import { test, expect } from '@playwright/test'

const LIVE_URL = '/#/live'

test.describe('Live View', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/health**', (route) =>
      route.fulfill({
        json: {
          status: 'ok',
          version: '2.5.0',
          uptime_s: 10,
          ai: { enabled: false, reason: 'not_configured' },
          cameras: { online: 1, retrying: 0, down: 0 },
          components: { pipeline: 'ok', telegram: 'disabled', mqtt: 'disabled' },
        },
      })
    )
    await page.route('**/api/settings**', (route) =>
      route.fulfill({
        json: {
          live: { output_mode: 'mjpeg' },
          stream: { protocol: 'tcp', buffer_size: 1 },
        },
      })
    )
    await page.route('**/api/events**', (route) =>
      route.fulfill({ json: { events: [], total: 0, page: 1, page_size: 1 } })
    )
    await page.route('**/api/cameras**', (route) =>
      route.fulfill({
        json: {
          cameras: [
            {
              id: 'test_thermal',
              name: 'Test Thermal',
              type: 'thermal',
              enabled: true,
              status: 'connected',
              stream_roles: ['live', 'detect'],
            },
          ],
        },
      })
    )
    await page.route('**/api/live**', (route) =>
      route.fulfill({
        json: {
          streams: [
            {
              camera_id: 'test_thermal',
              name: 'Test Thermal',
              stream_url: '/api/live/test_thermal.mjpeg',
              output_mode: 'mjpeg',
            },
          ],
        },
      })
    )
    await page.route('**/api/live/test_thermal.mjpeg**', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'multipart/x-mixed-replace; boundary=frame' },
        body: '--frame\r\nContent-Type: image/jpeg\r\n\r\n\r\n--frame--',
      })
    )
  })

  test('Live page loads and shows cameras', async ({ page }) => {
    await page.goto(LIVE_URL, { waitUntil: 'networkidle' })
    await expect(page.getByText('Test Thermal')).toBeVisible({ timeout: 15000 })
  })

  test('Refresh button exists and triggers refetch', async ({ page }) => {
    await page.goto(LIVE_URL)
    const refreshBtn = page.getByRole('button', { name: /Refresh|Yenile/i })
    await expect(refreshBtn).toBeVisible({ timeout: 15000 })
    await refreshBtn.click()
    await expect(page.getByText('Test Thermal')).toBeVisible()
  })

  test('Grid mode toggle exists', async ({ page }) => {
    await page.goto(LIVE_URL)
    const mode2x2 = page.getByRole('button', { name: /2x2/ })
    await expect(mode2x2).toBeVisible({ timeout: 15000 })
    await mode2x2.click()
  })

  test('Shows no cameras message when empty', async ({ page }) => {
    await page.route('**/api/cameras**', (route) =>
      route.fulfill({ json: { cameras: [] } })
    )
    await page.route('**/api/live**', (route) =>
      route.fulfill({ json: { streams: [] } })
    )
    await page.goto(LIVE_URL)
    await expect(page.getByText(/no cameras|kamera yok|add camera|kamera ekle/i)).toBeVisible({ timeout: 15000 })
  })
})
