/**
 * Camera settings tab - Global camera tuning
 */
import React from 'react'
import { useTranslation } from 'react-i18next'
import type { Settings } from '../../types/api'

interface CameraSettingsTabProps {
  settings: Settings
  onChange: (settings: Settings) => void
  onSave: (updates: Partial<Settings>) => Promise<void>
}

export const CameraSettingsTab: React.FC<CameraSettingsTabProps> = ({ settings, onChange, onSave }) => {
  const { t } = useTranslation()

  const applyPreset = async (preset: 'eco' | 'balanced' | 'quality' | 'frigate') => {
    const baseDetection = settings.detection
    const baseMotion = settings.motion
    const baseThermal = settings.thermal
    const baseStream = settings.stream
    const baseEvent = settings.event

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
      if (preset === 'frigate') {
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
          stream: {
            ...baseStream,
            protocol: 'tcp',
            capture_backend: 'auto',
            buffer_size: 1,
            reconnect_delay_seconds: 5,
            max_reconnect_attempts: 10,
            read_failure_threshold: 3,
            read_failure_timeout_seconds: 12,
          },
          event: {
            ...baseEvent,
            prebuffer_seconds: 5,
            postbuffer_seconds: 5,
            frame_interval: 2,
            min_event_duration: 1.0,
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
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
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
            onClick={() => applyPreset('frigate')}
            className="p-4 rounded-lg border border-border bg-surface1 text-left hover:bg-surface1/80 transition-colors"
          >
            <div className="font-semibold text-text">{t('perfPresetFrigateTitle')}</div>
            <div className="text-xs text-muted mt-1">{t('perfPresetFrigateDesc')}</div>
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
            <p className="text-xs text-muted">{t('detectionModelHint')}</p>
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
            <div>
              <label className="text-xs text-muted">
                {t('perfThermalConfidenceLabel')} {settings.detection.thermal_confidence_threshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.detection.thermal_confidence_threshold}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    detection: { ...settings.detection, thermal_confidence_threshold: parseFloat(e.target.value) },
                  })
                }
                className="w-full"
              />
              <p className="text-xs text-muted mt-1">{t('perfThermalConfidenceHint')}</p>
            </div>

            <div>
              <label className="text-xs text-muted">
                {t('detectionNmsLabel', { value: settings.detection.nms_iou_threshold.toFixed(2) })}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.detection.nms_iou_threshold}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    detection: { ...settings.detection, nms_iou_threshold: parseFloat(e.target.value) },
                  })
                }
                className="w-full"
              />
              <p className="text-xs text-muted mt-1">{t('detectionNmsHint')}</p>
            </div>

            <div>
              <label className="text-xs text-muted">
                {t('detectionAspectRatioMinLabel', {
                  value: settings.detection.aspect_ratio_min?.toFixed(2) || 0.3,
                })}
              </label>
              <input
                type="range"
                min="0.05"
                max="1.0"
                step="0.05"
                value={settings.detection.aspect_ratio_min || 0.3}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    detection: { ...settings.detection, aspect_ratio_min: parseFloat(e.target.value) },
                  })
                }
                className="w-full"
              />
              <p className="text-xs text-muted mt-1">{t('detectionAspectRatioMinHint')}</p>
            </div>

            <div>
              <label className="text-xs text-muted">
                {t('detectionAspectRatioMaxLabel', {
                  value: settings.detection.aspect_ratio_max?.toFixed(2) || 3.0,
                })}
              </label>
              <input
                type="range"
                min="1.0"
                max="5.0"
                step="0.1"
                value={settings.detection.aspect_ratio_max || 3.0}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    detection: { ...settings.detection, aspect_ratio_max: parseFloat(e.target.value) },
                  })
                }
                className="w-full"
              />
              <p className="text-xs text-muted mt-1">{t('detectionAspectRatioMaxHint')}</p>
            </div>

            <label className="flex items-center gap-2 text-sm text-text">
              <input
                type="checkbox"
                checked={settings.detection.enable_tracking}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    detection: { ...settings.detection, enable_tracking: e.target.checked },
                  })
                }
              />
              {t('detectionEnableTracking')}
            </label>
          </div>

          <div className="space-y-3">
            <h5 className="text-sm font-semibold text-text">{t('perfSectionMotion')}</h5>
            <label className="text-xs text-muted">{t('motionAlgorithmLabel')}</label>
            <select
              value={settings.motion.algorithm ?? 'mog2'}
              onChange={(e) =>
                onChange({
                  ...settings,
                  motion: { ...settings.motion, algorithm: e.target.value as 'frame_diff' | 'mog2' | 'knn' },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            >
              <option value="frame_diff">{t('motionAlgorithmFrameDiff')}</option>
              <option value="mog2">{t('motionAlgorithmMOG2')}</option>
              <option value="knn">{t('motionAlgorithmKNN')}</option>
            </select>
            <label className="text-xs text-muted">{t('motionSensitivityLabel', { value: settings.motion.sensitivity })}</label>
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
            <label className="text-xs text-muted">{t('motionMinAreaLabel')}</label>
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
            <label className="text-xs text-muted">{t('motionCooldownLabel')}</label>
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
              <option value="clahe">CLAHE ({t('recommended')})</option>
              <option value="histogram">{t('histogram')}</option>
              <option value="none">{t('none')}</option>
            </select>

            {settings.thermal.enable_enhancement && settings.thermal.enhancement_method === 'clahe' && (
              <>
                <div>
                  <label className="text-xs text-muted">
                    {t('claheClipLimit')}: {settings.thermal.clahe_clip_limit.toFixed(1)}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="0.5"
                    value={settings.thermal.clahe_clip_limit}
                    onChange={(e) =>
                      onChange({
                        ...settings,
                        thermal: { ...settings.thermal, clahe_clip_limit: parseFloat(e.target.value) },
                      })
                    }
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="text-xs text-muted">{t('claheGridSize')}</label>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="number"
                      min="4"
                      max="16"
                      value={settings.thermal.clahe_tile_size[0]}
                      onChange={(e) =>
                        onChange({
                          ...settings,
                          thermal: {
                            ...settings.thermal,
                            clahe_tile_size: [parseInt(e.target.value) || 8, settings.thermal.clahe_tile_size[1]],
                          },
                        })
                      }
                      className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
                    />
                    <input
                      type="number"
                      min="4"
                      max="16"
                      value={settings.thermal.clahe_tile_size[1]}
                      onChange={(e) =>
                        onChange({
                          ...settings,
                          thermal: {
                            ...settings.thermal,
                            clahe_tile_size: [settings.thermal.clahe_tile_size[0], parseInt(e.target.value) || 8],
                          },
                        })
                      }
                      className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
                    />
                  </div>
                </div>
              </>
            )}

            {settings.thermal.enable_enhancement && (
              <div>
                <label className="text-xs text-muted">{t('gaussianBlur')}</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    min="1"
                    max="9"
                    step="2"
                    value={settings.thermal.gaussian_blur_kernel[0]}
                    onChange={(e) =>
                      onChange({
                        ...settings,
                        thermal: {
                          ...settings.thermal,
                          gaussian_blur_kernel: [parseInt(e.target.value) || 3, settings.thermal.gaussian_blur_kernel[1]],
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
                  />
                  <input
                    type="number"
                    min="1"
                    max="9"
                    step="2"
                    value={settings.thermal.gaussian_blur_kernel[1]}
                    onChange={(e) =>
                      onChange({
                        ...settings,
                        thermal: {
                          ...settings.thermal,
                          gaussian_blur_kernel: [settings.thermal.gaussian_blur_kernel[0], parseInt(e.target.value) || 3],
                        },
                      })
                    }
                    className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
                  />
                </div>
              </div>
            )}

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
            <label className="text-xs text-muted">{t('streamBackend')}</label>
            <select
              value={settings.stream.capture_backend || 'auto'}
              onChange={(e) =>
                onChange({
                  ...settings,
                  stream: { ...settings.stream, capture_backend: e.target.value as Settings['stream']['capture_backend'] },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            >
              <option value="auto">{t('streamBackendAuto')}</option>
              <option value="opencv">{t('streamBackendOpenCV')}</option>
              <option value="ffmpeg">{t('streamBackendFFmpeg')}</option>
            </select>
            <label className="text-xs text-muted">{t('bufferSize')}</label>
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
            <label className="text-xs text-muted">{t('reconnectDelay')} ({t('seconds')})</label>
            <input
              type="number"
              min="1"
              value={settings.stream.reconnect_delay_seconds}
              onChange={(e) =>
                onChange({
                  ...settings,
                  stream: { ...settings.stream, reconnect_delay_seconds: parseInt(e.target.value) || 1 },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            />
            <label className="text-xs text-muted">{t('maxReconnectAttempts')}</label>
            <input
              type="number"
              min="1"
              value={settings.stream.max_reconnect_attempts}
              onChange={(e) =>
                onChange({
                  ...settings,
                  stream: { ...settings.stream, max_reconnect_attempts: parseInt(e.target.value) || 1 },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            />
            <label className="text-xs text-muted">{t('readFailureThreshold')}</label>
            <input
              type="number"
              min="1"
              value={settings.stream.read_failure_threshold}
              onChange={(e) =>
                onChange({
                  ...settings,
                  stream: { ...settings.stream, read_failure_threshold: parseInt(e.target.value) || 1 },
                })
              }
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text"
            />
            <label className="text-xs text-muted">{t('readFailureTimeout')} ({t('seconds')})</label>
            <input
              type="number"
              min="1"
              step="0.5"
              value={settings.stream.read_failure_timeout_seconds}
              onChange={(e) =>
                onChange({
                  ...settings,
                  stream: { ...settings.stream, read_failure_timeout_seconds: parseFloat(e.target.value) || 1 },
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
