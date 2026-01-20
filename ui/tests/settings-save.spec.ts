import { test, expect, Page } from '@playwright/test'

type Settings = {
  detection: {
    model: string
    confidence_threshold: number
    nms_iou_threshold: number
    inference_resolution: [number, number]
    inference_fps: number
    enable_tracking: boolean
  }
  motion: {
    sensitivity: number
    min_area: number
    cooldown_seconds: number
    presets: {
      thermal_recommended: {
        sensitivity: number
        min_area: number
        cooldown_seconds: number
      }
    }
  }
  thermal: {
    enable_enhancement: boolean
    enhancement_method: 'clahe' | 'histogram' | 'none'
    clahe_clip_limit: number
    clahe_tile_size: [number, number]
    gaussian_blur_kernel: [number, number]
  }
  stream: {
    protocol: 'tcp' | 'udp'
    buffer_size: number
    reconnect_delay_seconds: number
    max_reconnect_attempts: number
  }
  live: {
    output_mode: 'mjpeg' | 'webrtc'
    webrtc: { enabled: boolean; go2rtc_url: string }
  }
  record: {
    enabled: boolean
    retention_days: number
    record_segments_seconds: number
    disk_limit_percent: number
    cleanup_policy: string
    delete_order: string[]
  }
  event: {
    cooldown_seconds: number
    frame_buffer_size: number
    frame_interval: number
    min_event_duration: number
  }
  media: {
    retention_days: number
    cleanup_interval_hours: number
    disk_limit_percent: number
  }
  ai: {
    enabled: boolean
    api_key: string
    model: string
    max_tokens: number
    timeout: number
  }
  telegram: {
    enabled: boolean
    bot_token: string
    chat_ids: string[]
    rate_limit_seconds: number
    send_images: boolean
    video_speed: number
    event_types: string[]
    cooldown_seconds: number
    max_messages_per_min: number
    snapshot_quality: number
  }
  appearance: {
    theme: 'slate' | 'carbon' | 'pure-black' | 'matrix'
    language: 'tr' | 'en'
  }
}

const baseSettings: Settings = {
  detection: {
    model: 'yolov8n-person',
    confidence_threshold: 0.25,
    nms_iou_threshold: 0.45,
    inference_resolution: [640, 640],
    inference_fps: 5,
    enable_tracking: false,
  },
  motion: {
    sensitivity: 7,
    min_area: 500,
    cooldown_seconds: 5,
    presets: {
      thermal_recommended: { sensitivity: 8, min_area: 450, cooldown_seconds: 4 },
    },
  },
  thermal: {
    enable_enhancement: true,
    enhancement_method: 'clahe',
    clahe_clip_limit: 2.0,
    clahe_tile_size: [8, 8],
    gaussian_blur_kernel: [3, 3],
  },
  stream: {
    protocol: 'tcp',
    buffer_size: 1,
    reconnect_delay_seconds: 5,
    max_reconnect_attempts: 10,
  },
  live: {
    output_mode: 'mjpeg',
    webrtc: { enabled: false, go2rtc_url: '' },
  },
  record: {
    enabled: false,
    retention_days: 7,
    record_segments_seconds: 10,
    disk_limit_percent: 80,
    cleanup_policy: 'oldest_first',
    delete_order: ['mp4', 'gif', 'collage'],
  },
  event: {
    cooldown_seconds: 5,
    frame_buffer_size: 10,
    frame_interval: 2,
    min_event_duration: 1.0,
  },
  media: {
    retention_days: 7,
    cleanup_interval_hours: 24,
    disk_limit_percent: 80,
  },
  ai: {
    enabled: false,
    api_key: '',
    model: 'gpt-4o',
    max_tokens: 200,
    timeout: 30,
  },
  telegram: {
    enabled: false,
    bot_token: '',
    chat_ids: [],
    rate_limit_seconds: 5,
    send_images: true,
    video_speed: 4,
    event_types: ['person'],
    cooldown_seconds: 5,
    max_messages_per_min: 20,
    snapshot_quality: 85,
  },
  appearance: {
    theme: 'slate',
    language: 'tr',
  },
}

const mergeDeep = (base: any, update: any): any => {
  if (Array.isArray(base) || Array.isArray(update)) {
    return update ?? base
  }
  if (typeof base !== 'object' || typeof update !== 'object' || !base || !update) {
    return update ?? base
  }
  const result = { ...base }
  for (const key of Object.keys(update)) {
    result[key] = key in result ? mergeDeep(result[key], update[key]) : update[key]
  }
  return result
}

const mockSettingsApi = async (page: Page) => {
  let current = JSON.parse(JSON.stringify(baseSettings))

  await page.route('**/api/health', async route => {
    await route.fulfill({
      json: {
        status: 'ok',
        version: '2.0.0',
        uptime_s: 10,
        ai: { enabled: false, reason: 'not_configured' },
        cameras: { online: 0, retrying: 0, down: 0 },
        components: { pipeline: 'ok', telegram: 'disabled', mqtt: 'disabled' },
      },
    })
  })

  await page.route('**/api/settings', async route => {
    const method = route.request().method()
    if (method === 'GET') {
      await route.fulfill({ json: current })
      return
    }
    if (method === 'PUT') {
      const body = route.request().postData()
      const update = body ? JSON.parse(body) : {}
      current = mergeDeep(current, update)
      await route.fulfill({ json: current })
      return
    }
    await route.fulfill({ status: 405 })
  })
}

const setLanguage = async (page: Page, language: 'tr' | 'en') => {
  await page.addInitScript(() => {
    localStorage.setItem('language', (window as any).__lang || 'tr')
  }, { __lang: language })
}

const expectSavedToast = async (page: Page) => {
  const toast = page.locator('[role="status"]').filter({ hasText: /Settings saved successfully/i }).last()
  await expect(toast).toBeVisible()
}

const inputByLabel = (page: Page, label: RegExp) =>
  page.locator('label', { hasText: label }).locator('..').locator('input')

const selectByLabel = (page: Page, label: RegExp) =>
  page.locator('label', { hasText: label }).locator('..').locator('select')

const runSaveTests = (language: 'tr' | 'en') => {
  test.describe(`${language.toUpperCase()} settings save`, () => {
    test.beforeEach(async ({ page }) => {
      await mockSettingsApi(page)
      await setLanguage(page, language)
    })

    test('Detection settings save', async ({ page }) => {
      await page.goto('/settings?tab=detection')
      await inputByLabel(page, /Çıkarım FPS|Inference FPS/i).fill('6')
      await page.getByRole('button', { name: /Algılama Ayarlarını Kaydet|Save Detection Settings/i }).click()
      await expectSavedToast(page)
    })

    test('Thermal settings save', async ({ page }) => {
      await page.goto('/settings?tab=thermal')
      await selectByLabel(page, /İyileştirme Yöntemi|Enhancement Method/i).selectOption('histogram')
      await page.getByRole('button', { name: /Termal Ayarları Kaydet|Save Thermal Settings/i }).click()
      await expectSavedToast(page)
    })

    test('Stream settings save', async ({ page }) => {
      await page.goto('/settings?tab=stream')
      await inputByLabel(page, /Buffer Size|Buffer Boyutu/i).fill('2')
      await page.getByRole('button', { name: /Yayın Ayarlarını Kaydet|Save Stream Settings/i }).click()
      await expectSavedToast(page)
    })

    test('Live settings save', async ({ page }) => {
      await page.goto('/settings?tab=live')
      await selectByLabel(page, /Çıkış Modu|Output Mode/i).selectOption('webrtc')
      await page.getByRole('button', { name: /Canlı Görüntü Ayarlarını Kaydet|Save Live Settings/i }).click()
      await expectSavedToast(page)
    })

    test('Recording settings save', async ({ page }) => {
      await page.goto('/settings?tab=recording')
      await page.locator('#recording-enabled').check()
      await inputByLabel(page, /Saklama Süresi/i).fill('14')
      await page.getByRole('button', { name: /Kayıt Ayarlarını Kaydet|Save Recording Settings/i }).click()
      await expectSavedToast(page)
    })

    test('Events settings save', async ({ page }) => {
      await page.goto('/settings?tab=events')
      await inputByLabel(page, /Bekleme Süresi|Cooldown/i).fill('3')
      await page.getByRole('button', { name: /Olay Ayarlarını Kaydet|Save Event Settings/i }).click()
      await expectSavedToast(page)
    })

    test('AI settings save', async ({ page }) => {
      await page.goto('/settings?tab=ai')
      await page.locator('#ai-enabled').check()
      await selectByLabel(page, /Model/i).selectOption('gpt-4o-mini')
      await page.getByRole('button', { name: /AI Ayarlarını Kaydet|Save AI Settings/i }).click()
      await expectSavedToast(page)
    })

    test('AI settings invalid key blocked', async ({ page }) => {
      await page.goto('/settings?tab=ai')
      await page.locator('#ai-enabled').check()
      await page.locator('input[type="password"], input[type="text"]').first().fill('api')
      await page.getByRole('button', { name: /AI Ayarlarını Kaydet|Save AI Settings/i }).click()
      const errorToast = page.locator('[role="status"]').filter({ hasText: /sk-/i }).last()
      await expect(errorToast).toBeVisible()
    })

    test('Telegram settings save', async ({ page }) => {
      await page.goto('/settings?tab=telegram')
      await page.locator('#telegram-enabled').check()
      await page.getByPlaceholder('Enter chat ID and press Enter').fill('123456789')
      await page.getByRole('button', { name: /Add|Ekle/i }).click()
      await page.getByRole('button', { name: /Telegram Ayarlarını Kaydet|Save Telegram Settings/i }).click()
      await expectSavedToast(page)
    })

    test('Telegram invalid bot token blocked', async ({ page }) => {
      await page.goto('/settings?tab=telegram')
      await page.locator('#telegram-enabled').check()
      await page.locator('input[type="password"]').first().fill('invalid-token')
      await page.getByRole('button', { name: /Telegram Ayarlarını Kaydet|Save Telegram Settings/i }).click()
      const errorToast = page.locator('[role="status"]').filter({ hasText: /token/i }).last()
      await expect(errorToast).toBeVisible()
    })

    test('Telegram invalid chat id blocked', async ({ page }) => {
      await page.goto('/settings?tab=telegram')
      await page.locator('#telegram-enabled').check()
      await page.getByPlaceholder('Enter chat ID and press Enter').fill('abc123')
      await page.getByRole('button', { name: /Add|Ekle/i }).click()
      const errorToast = page.locator('[role="status"]').filter({ hasText: /chat id|sayısal/i }).last()
      await expect(errorToast).toBeVisible()
    })
  })
}

runSaveTests('tr')
runSaveTests('en')
