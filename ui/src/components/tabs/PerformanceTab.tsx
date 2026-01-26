/**
 * Performance tab - Presets + quick manual tuning
 */
import React from 'react'
import { useTranslation } from 'react-i18next'
import type { Settings } from '../../types/api'

interface PerformanceTabProps {
  settings: Settings
  onChange: (settings: Settings) => void
  onSave: (updates: Partial<Settings>) => Promise<void>
}

export const PerformanceTab: React.FC<PerformanceTabProps> = ({ settings, onChange, onSave }) => {
  const { t } = useTranslation()

  const applyPreset = async (preset: 'eco' | 'balanced' | 'quality') => {
    const baseDetection = settings.detection
    const baseMotion = settings.motion
    const baseThermal = settings.thermal

    const updates: Partial<Settings> = (() => {
      if (preset === 'eco') {
        return {
          detection: {
            ...baseDetection,
            model: 'yolov8n-person',
            inference_fps: 3,
            inference_resolution: [512, 512],
            confidence_threshold: 0.35,
          },
          motion: {
            ...baseMotion,
            sensitivity: 6,
            min_area: 700,
            cooldown_seconds: 5,
          },
          thermal: {
            ...baseThermal,
            enable_enhancement: false,
          },
        }
      }
      if (preset === 'quality') {
        return {
          detection: {
            ...baseDetection,
            model: 'yolov9t',
            inference_fps: 7,
            inference_resolution: [640, 640],
            confidence_threshold: 0.25,
          },
          motion: {
            ...baseMotion,
            sensitivity: 8,
            min_area: 450,
            cooldown_seconds: 4,
          },
          thermal: {
            ...baseThermal,
            enable_enhancement: true,
            enhancement_method: 'clahe',
            clahe_clip_limit: 2.0,
          },
        }
      }
      return {
        detection: {
          ...baseDetection,
          model: 'yolov8s-person',
          inference_fps: 5,
          inference_resolution: [640, 640],
          confidence_threshold: 0.3,
        },
        motion: {
          ...baseMotion,
          sensitivity: 7,
          min_area: 500,
          cooldown_seconds: 5,
        },
        thermal: {
          ...baseThermal,
          enable_enhancement: true,
          enhancement_method: 'clahe',
          clahe_clip_limit: 2.0,
        },
      }
    })()

    const nextSettings = {
      ...settings,
      ...updates,
    } as Settings

    onChange(nextSettings)
    await onSave(updates)
  }

  const handleManualSave = async () => {
    await onSave({
      detection: settings.detection,
      motion: settings.motion,
      thermal: settings.thermal,
      stream: settings.stream,
    })
  }

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-medium text-text mb-2">{t('perfPageTitle')}</h3>
        <p className="text-sm text-muted">{t('perfPageDesc')}</p>
      </div>

      <div className="bg-surface2 border border-border rounded-lg p-6">
        <div className="flex flex-col gap-2 mb-4">
          <h4 className="text-base font-semibold text-text">{t('perfPresetsTitle')}</h4>
          <p className="text-sm text-muted">{t('perfPresetsDesc')}</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            onClick={() => applyPreset('eco')}
            className="p-4 rounded-lg border border-border bg-surface1 text-left hover:bg-surface1/80 transition-colors"
          >
            <div className="font-semibold text-text">{t('perfPresetEcoTitle')}</div>
            <div className="text-xs text-muted mt-1">{t('perfPresetEcoDesc')}</div>
          </button>
          <button
            onClick={() => applyPreset('balanced')}
            className="p-4 rounded-lg border border-border bg-surface1 text-left hover:bg-surface1/80 transition-colors"
          >
            <div className="font-semibold text-text">{t('perfPresetBalancedTitle')}</div>
            <div className="text-xs text-muted mt-1">{t('perfPresetBalancedDesc')}</div>
          </button>
          <button
            onClick={() => applyPreset('quality')}
            className="p-4 rounded-lg border border-border bg-surface1 text-left hover:bg-surface1/80 transition-colors"
          >
            <div className="font-semibold text-text">{t('perfPresetQualityTitle')}</div>
            <div className="text-xs text-muted mt-1">{t('perfPresetQualityDesc')}</div>
          </button>
        </div>
        <p className="text-xs text-muted mt-3">{t('perfPresetNote')}</p>
      </div>

      <div className="bg-surface2 border-l-4 border-warning p-4 rounded-lg">
        <h4 className="font-semibold text-text mb-2">⚡ {t('perfTipsTitle')}</h4>
        <ul className="text-sm text-muted space-y-1">
          <li>{t('perfTipDetectionModel')}</li>
          <li>{t('perfTipDetectionFps')}</li>
          <li>{t('perfTipDetectionResolution')}</li>
          <li>{t('perfTipMotion')}</li>
          <li>{t('perfTipThermal')}</li>
          <li>{t('perfTipStream')}</li>
        </ul>
      </div>

      <div className="bg-surface2 border border-border rounded-lg p-6 space-y-6">
        <div>
          <h4 className="text-base font-semibold text-text">{t('perfManualTitle')}</h4>
          <p className="text-sm text-muted">{t('perfManualDesc')}</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-text">{t('perfSectionDetection')}</h5>
            <select
              value={settings.detection.model}
              onChange={(e) =>
                onChange({
                  ...settings,
                  detection: { ...settings.detection, model: e.target.value as Settings['detection']['model'] },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            >
              <option value="yolov8n-person">YOLOv8n-person</option>
              <option value="yolov8s-person">YOLOv8s-person</option>
              <option value="yolov9t">YOLOv9t</option>
              <option value="yolov9s">YOLOv9s</option>
            </select>
            <div className="flex gap-3">
              <input
                type="number"
                min="1"
                max="30"
                value={settings.detection.inference_fps}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    detection: { ...settings.detection, inference_fps: parseInt(e.target.value) || 1 },
                  })
                }
                className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
              />
              <span className="text-xs text-muted self-center">{t('perfFpsLabel')}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                min="320"
                max="1920"
                value={settings.detection.inference_resolution[0]}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    detection: {
                      ...settings.detection,
                      inference_resolution: [parseInt(e.target.value) || 640, settings.detection.inference_resolution[1]],
                    },
                  })
                }
                className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
              />
              <input
                type="number"
                min="320"
                max="1920"
                value={settings.detection.inference_resolution[1]}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    detection: {
                      ...settings.detection,
                      inference_resolution: [settings.detection.inference_resolution[0], parseInt(e.target.value) || 640],
                    },
                  })
                }
                className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
              />
            </div>
            <div>
              <label className="text-xs text-muted">{t('perfConfidenceLabel')} {settings.detection.confidence_threshold.toFixed(2)}</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.detection.confidence_threshold}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    detection: { ...settings.detection, confidence_threshold: parseFloat(e.target.value) },
                  })
                }
                className="w-full"
              />
            </div>
          </div>

          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-text">{t('perfSectionMotion')}</h5>
            <input
              type="number"
              min="1"
              max="10"
              value={settings.motion.sensitivity}
              onChange={(e) =>
                onChange({
                  ...settings,
                  motion: { ...settings.motion, sensitivity: parseInt(e.target.value) || 1 },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            />
            <input
              type="number"
              min="0"
              value={settings.motion.min_area}
              onChange={(e) =>
                onChange({
                  ...settings,
                  motion: { ...settings.motion, min_area: parseInt(e.target.value) || 0 },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            />
            <input
              type="number"
              min="0"
              value={settings.motion.cooldown_seconds}
              onChange={(e) =>
                onChange({
                  ...settings,
                  motion: { ...settings.motion, cooldown_seconds: parseInt(e.target.value) || 0 },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            />

            <h5 className="text-sm font-semibold text-text mt-4">{t('perfSectionThermal')}</h5>
            <label className="flex items-center gap-2 text-sm text-text">
              <input
                type="checkbox"
                checked={settings.thermal.enable_enhancement}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    thermal: { ...settings.thermal, enable_enhancement: e.target.checked },
                  })
                }
              />
              {t('perfThermalEnhance')}
            </label>
            <select
              value={settings.thermal.enhancement_method}
              onChange={(e) =>
                onChange({
                  ...settings,
                  thermal: { ...settings.thermal, enhancement_method: e.target.value as Settings['thermal']['enhancement_method'] },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            >
              <option value="clahe">CLAHE</option>
              <option value="histogram">Histogram</option>
              <option value="none">None</option>
            </select>

            <h5 className="text-sm font-semibold text-text mt-4">{t('perfSectionStream')}</h5>
            <select
              value={settings.stream.protocol}
              onChange={(e) =>
                onChange({
                  ...settings,
                  stream: { ...settings.stream, protocol: e.target.value as Settings['stream']['protocol'] },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            >
              <option value="tcp">TCP ({t('stable')})</option>
              <option value="udp">UDP ({t('lowLatency')})</option>
            </select>
            <input
              type="number"
              min="1"
              value={settings.stream.buffer_size}
              onChange={(e) =>
                onChange({
                  ...settings,
                  stream: { ...settings.stream, buffer_size: parseInt(e.target.value) || 1 },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <p className="text-xs text-muted">{t('perfManualHint')}</p>
          <button
            onClick={handleManualSave}
            className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
          >
            {t('perfManualSave')}
          </button>
        </div>
      </div>
    </div>
  )
}
