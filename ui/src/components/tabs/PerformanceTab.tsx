/**
 * Camera settings tab - Global camera tuning
 * Gruplu, kompakt layout. Kullanılmayan ayarlar kaldırıldı.
 */
import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { MdExpandMore, MdExpandLess } from 'react-icons/md'
import type { Settings } from '../../types/api'

interface CameraSettingsTabProps {
  settings: Settings
  onChange: (settings: Settings) => void
  onSave: (updates: Partial<Settings>) => Promise<void>
}

const ALGORITHM_HINTS: Record<string, { tr: string; en: string }> = {
  frame_diff: { tr: 'Basit, hızlı. Rüzgarlı ortamda yanlış alarm fazla.', en: 'Simple, fast. More false alarms in windy areas.' },
  mog2: { tr: 'Arka plan öğrenir, gölge/gürültü azaltır. Önerilen.', en: 'Learns background, reduces shadows. Recommended.' },
  knn: { tr: 'MOG2 alternatifi, daha dayanıklı.', en: 'Alternative to MOG2, more resilient.' },
}

export const CameraSettingsTab: React.FC<CameraSettingsTabProps> = ({ settings, onChange, onSave }) => {
  const { t } = useTranslation()
  const lang = (localStorage.getItem('language') || 'tr') as 'tr' | 'en'
  const [showAdvancedStream, setShowAdvancedStream] = useState(false)
  const [showAdvancedThermal, setShowAdvancedThermal] = useState(false)
  const [showAdvancedPerf, setShowAdvancedPerf] = useState(false)
  const [showThermalQuickProfiles, setShowThermalQuickProfiles] = useState(false)
  const [showExpertControls, setShowExpertControls] = useState(false)

  const preset = settings.detection.aspect_ratio_preset ?? 'person'
  const isCustomAspect = preset === 'custom'

  const applyPreset = async (presetId: 'eco' | 'balanced' | 'quality' | 'frigate') => {
    const base = { detection: settings.detection, motion: settings.motion, thermal: settings.thermal, stream: settings.stream }
    const presets: Record<string, Partial<Settings>> = {
      eco: {
        detection: {
          ...base.detection,
          model: 'yolov8n-person',
          inference_fps: 2,
          inference_resolution: [416, 416],
          confidence_threshold: 0.50,
          thermal_confidence_threshold: 0.55,
        },
        motion: {
          ...base.motion,
          mode: 'auto',
          auto_profile: 'low',
          algorithm: 'frame_diff',
          sensitivity: 7,
          min_area: 600,
          cooldown_seconds: 8,
          thermal_suppression_enabled: true,
          thermal_suppression_streak: 8,
          thermal_suppression_duration: 20,
          thermal_suppression_wakeup_ratio: 1.8,
        },
        thermal: {
          ...base.thermal,
          enable_enhancement: false,
          enhancement_method: 'none',
          clahe_clip_limit: 2.0,
          clahe_tile_size: [32, 32],
          gaussian_blur_kernel: [3, 3],
        },
        stream: {
          ...base.stream,
          protocol: 'tcp',
          capture_backend: 'opencv',
          buffer_size: 1,
          reconnect_delay_seconds: 10,
          max_reconnect_attempts: 10,
          read_failure_threshold: 5,
          read_failure_timeout_seconds: 20,
        },
      },
      balanced: {
        detection: {
          ...base.detection,
          model: 'yolov8s-person',
          inference_fps: 5,
          inference_resolution: [640, 640],
          confidence_threshold: 0.50,
          thermal_confidence_threshold: 0.55,
        },
        motion: {
          ...base.motion,
          mode: 'auto',
          auto_profile: 'normal',
          algorithm: 'mog2',
          sensitivity: 8,
          min_area: 450,
          cooldown_seconds: 6,
          thermal_suppression_enabled: true,
          thermal_suppression_streak: 12,
          thermal_suppression_duration: 18,
          thermal_suppression_wakeup_ratio: 1.7,
        },
        thermal: {
          ...base.thermal,
          enable_enhancement: true,
          enhancement_method: 'clahe',
          clahe_clip_limit: 2.0,
          clahe_tile_size: [32, 32],
          gaussian_blur_kernel: [3, 3],
        },
        stream: {
          ...base.stream,
          protocol: 'tcp',
          capture_backend: 'auto',
          buffer_size: 1,
          reconnect_delay_seconds: 8,
          max_reconnect_attempts: 15,
          read_failure_threshold: 5,
          read_failure_timeout_seconds: 15,
        },
      },
      frigate: {
        detection: {
          ...base.detection,
          model: 'yolov8s-person',
          inference_fps: 8,
          inference_resolution: [640, 640],
          confidence_threshold: 0.45,
          thermal_confidence_threshold: 0.50,
        },
        motion: {
          ...base.motion,
          mode: 'auto',
          auto_profile: 'high',
          algorithm: 'mog2',
          sensitivity: 6,
          min_area: 250,
          cooldown_seconds: 4,
          thermal_suppression_enabled: false,
          thermal_suppression_streak: 10,
          thermal_suppression_duration: 12,
          thermal_suppression_wakeup_ratio: 1.6,
        },
        thermal: {
          ...base.thermal,
          enable_enhancement: true,
          enhancement_method: 'clahe',
          clahe_clip_limit: 2.3,
          clahe_tile_size: [32, 32],
          gaussian_blur_kernel: [3, 3],
        },
        stream: {
          ...base.stream,
          protocol: 'tcp',
          capture_backend: 'ffmpeg',
          buffer_size: 1,
          reconnect_delay_seconds: 3,
          max_reconnect_attempts: 20,
          read_failure_threshold: 3,
          read_failure_timeout_seconds: 10,
        },
      },
      quality: {
        detection: {
          ...base.detection,
          model: 'yolov9s',
          inference_fps: 7,
          inference_resolution: [640, 640],
          confidence_threshold: 0.55,
          thermal_confidence_threshold: 0.60,
        },
        motion: {
          ...base.motion,
          mode: 'auto',
          auto_profile: 'normal',
          algorithm: 'mog2',
          sensitivity: 9,
          min_area: 350,
          cooldown_seconds: 5,
          thermal_suppression_enabled: false,
          thermal_suppression_streak: 12,
          thermal_suppression_duration: 10,
          thermal_suppression_wakeup_ratio: 1.5,
        },
        thermal: {
          ...base.thermal,
          enable_enhancement: true,
          enhancement_method: 'clahe',
          clahe_clip_limit: 2.5,
          clahe_tile_size: [32, 32],
          gaussian_blur_kernel: [3, 3],
        },
        stream: {
          ...base.stream,
          protocol: 'tcp',
          capture_backend: 'ffmpeg',
          buffer_size: 2,
          reconnect_delay_seconds: 6,
          max_reconnect_attempts: 15,
          read_failure_threshold: 4,
          read_failure_timeout_seconds: 15,
        },
      },
    }
    const updates = presets[presetId] || presets.balanced
    const next = { ...settings, ...updates } as Settings
    onChange(next)
    await onSave(updates)
  }

  const applyThermalQuickProfile = async (profile: 'stable' | 'balanced' | 'detect') => {
    const base = { detection: settings.detection, motion: settings.motion, thermal: settings.thermal }
    const profiles: Record<string, Partial<Settings>> = {
      stable: {
        detection: {
          ...base.detection,
          thermal_confidence_threshold: 0.62,
        },
        motion: {
          ...base.motion,
          thermal_suppression_enabled: true,
          thermal_suppression_streak: 10,
          thermal_suppression_duration: 30,
          thermal_suppression_wakeup_ratio: 2.0,
        },
        thermal: {
          ...base.thermal,
          enable_enhancement: true,
          enhancement_method: 'clahe',
          clahe_clip_limit: 2.5,
        },
      },
      balanced: {
        detection: {
          ...base.detection,
          thermal_confidence_threshold: 0.55,
        },
        motion: {
          ...base.motion,
          thermal_suppression_enabled: true,
          thermal_suppression_streak: 12,
          thermal_suppression_duration: 18,
          thermal_suppression_wakeup_ratio: 1.7,
        },
        thermal: {
          ...base.thermal,
          enable_enhancement: true,
          enhancement_method: 'clahe',
          clahe_clip_limit: 2.2,
        },
      },
      detect: {
        detection: {
          ...base.detection,
          thermal_confidence_threshold: 0.50,
        },
        motion: {
          ...base.motion,
          thermal_suppression_enabled: false,
        },
        thermal: {
          ...base.thermal,
          enable_enhancement: true,
          enhancement_method: 'clahe',
          clahe_clip_limit: 2.0,
        },
      },
    }
    const updates = profiles[profile] || profiles.balanced
    const next = { ...settings, ...updates } as Settings
    onChange(next)
    await onSave(updates)
  }

  const handleManualSave = async () => {
    await onSave({
      detection: settings.detection,
      motion: settings.motion,
      thermal: settings.thermal,
      stream: settings.stream,
      performance: settings.performance,
    })
  }

  const algHint = ALGORITHM_HINTS[settings.motion.algorithm ?? 'mog2']?.[lang] ?? ALGORITHM_HINTS.mog2.en

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-1">{t('perfPageTitle')}</h3>
        <p className="text-sm text-muted">{t('perfPageDesc')}</p>
      </div>

      {/* Presets - compact */}
      <div className="bg-surface2 border border-border rounded-lg p-4">
        <h4 className="text-sm font-semibold text-text mb-1">{t('perfPresetsStepTitle')}</h4>
        <p className="text-xs text-muted mb-1">{t('perfPresetsDesc')}</p>
        <p className="text-xs text-muted mb-3">{t('perfPresetsScope')}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {(['eco', 'balanced', 'frigate', 'quality'] as const).map((id) => (
            <button
              key={id}
              onClick={() => applyPreset(id)}
              className="p-3 rounded-lg border border-border bg-surface1 text-left hover:bg-surface1/80 transition-colors text-sm"
            >
              <span className="font-medium text-text">
                {id === 'eco' && `⚡ ${t('perfPresetEcoTitle')}`}
                {id === 'balanced' && `⚖️ ${t('perfPresetBalancedTitle')}`}
                {id === 'frigate' && `🛡️ ${t('perfPresetFrigateTitle')}`}
                {id === 'quality' && `🎯 ${t('perfPresetQualityTitle')}`}
              </span>
              <p className="text-xs text-muted mt-0.5">
                {id === 'eco' && t('perfPresetEcoDesc')}
                {id === 'balanced' && t('perfPresetBalancedDesc')}
                {id === 'frigate' && t('perfPresetFrigateDesc')}
                {id === 'quality' && t('perfPresetQualityDesc')}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Thermal quick profiles - optional fine tuning */}
      <div className="bg-surface2 border border-border rounded-lg p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h4 className="text-sm font-semibold text-text mb-1">{t('thermalQuickProfilesStepTitle')}</h4>
            <p className="text-xs text-muted mb-1">{t('thermalQuickProfilesDesc')}</p>
            <p className="text-xs text-muted">{t('thermalQuickProfilesScope')}</p>
            <p className="text-xs text-muted mt-1">{t('thermalQuickProfilesOrderHint')}</p>
          </div>
          <button
            type="button"
            onClick={() => setShowThermalQuickProfiles(!showThermalQuickProfiles)}
            className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-border text-muted hover:text-text hover:bg-surface1/70 whitespace-nowrap"
          >
            {showThermalQuickProfiles ? <MdExpandLess /> : <MdExpandMore />}
            {showThermalQuickProfiles ? t('thermalQuickProfilesHide') : t('thermalQuickProfilesShow')}
          </button>
        </div>
        <div className={`grid grid-cols-1 md:grid-cols-3 gap-2 mt-3 ${showThermalQuickProfiles ? '' : 'hidden'}`}>
          <button
            type="button"
            onClick={() => applyThermalQuickProfile('stable')}
            className="p-3 rounded-lg border border-border bg-surface1 text-left hover:bg-surface1/80 transition-colors text-sm"
          >
            <span className="font-medium text-text">🧱 {t('thermalQuickProfileStable')}</span>
            <p className="text-xs text-muted mt-0.5">{t('thermalQuickProfileStableDesc')}</p>
          </button>
          <button
            type="button"
            onClick={() => applyThermalQuickProfile('balanced')}
            className="p-3 rounded-lg border border-border bg-surface1 text-left hover:bg-surface1/80 transition-colors text-sm"
          >
            <span className="font-medium text-text">⚖️ {t('thermalQuickProfileBalanced')}</span>
            <p className="text-xs text-muted mt-0.5">{t('thermalQuickProfileBalancedDesc')}</p>
          </button>
          <button
            type="button"
            onClick={() => applyThermalQuickProfile('detect')}
            className="p-3 rounded-lg border border-border bg-surface1 text-left hover:bg-surface1/80 transition-colors text-sm"
          >
            <span className="font-medium text-text">🚶 {t('thermalQuickProfileDetect')}</span>
            <p className="text-xs text-muted mt-0.5">{t('thermalQuickProfileDetectDesc')}</p>
          </button>
        </div>
      </div>

      {/* Manual - 3 columns */}
      <div className="bg-surface2 border border-border rounded-lg p-6 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h4 className="text-base font-semibold text-text">{t('perfManualTitle')}</h4>
          <button
            type="button"
            onClick={() => setShowExpertControls(!showExpertControls)}
            className="text-xs px-3 py-1.5 rounded-lg border border-border text-muted hover:text-text hover:bg-surface1/70"
          >
            {showExpertControls ? t('perfExpertToggleHide') : t('perfExpertToggleShow')}
          </button>
        </div>
        <div className="p-4 rounded-lg bg-surface1/50 border border-border">
          <label className="text-sm font-semibold text-text block mb-2">{t('perfInferenceBackend')}</label>
          <select
            value={settings.detection.inference_backend || 'auto'}
            onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, inference_backend: e.target.value as Settings['detection']['inference_backend'] } })}
            className="w-full px-3 py-2.5 bg-surface1 border border-border rounded-lg text-text text-sm"
          >
            <option value="auto">{t('perfBackendAuto')}</option>
            <option value="openvino">{t('perfBackendOpenVINO')}</option>
            <option value="tensorrt">{t('perfBackendTensorRT')}</option>
            <option value="onnx">{t('perfBackendONNX')}</option>
            <option value="cpu">{t('perfBackendCPU')}</option>
          </select>
          <div className="mt-2 rounded-lg bg-surface1/70 border border-border p-3 text-xs text-muted space-y-1">
            <div className="text-text font-medium">{t('perfBackendHelpTitle')}</div>
            <ul className="list-disc pl-4 space-y-0.5">
              <li>{t('perfBackendHelpAuto')}</li>
              <li>{t('perfBackendHelpOpenVINO')}</li>
              <li>{t('perfBackendHelpTensorRT')}</li>
              <li>{t('perfBackendHelpONNX')}</li>
              <li>{t('perfBackendHelpVerify')}</li>
              <li>{t('perfBackendHelpRestart')}</li>
            </ul>
          </div>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {/* Detection */}
          <div className="space-y-3 p-4 rounded-lg bg-surface1/50">
            <h5 className="text-sm font-semibold text-text border-b border-border pb-1">{t('perfSectionDetection')}</h5>
            <select
              value={settings.detection.model}
              onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, model: e.target.value as Settings['detection']['model'] } })}
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text text-sm"
            >
              <option value="yolov8n-person">YOLOv8n</option>
              <option value="yolov8s-person">YOLOv8s</option>
              <option value="yolov9t">YOLOv9t</option>
              <option value="yolov9s">YOLOv9s</option>
            </select>
            <div className="flex gap-2 items-center">
              <input type="number" min={1} max={30} value={settings.detection.inference_fps} onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, inference_fps: parseInt(e.target.value) || 1 } })} className="w-16 px-2 py-1.5 bg-surface1 border border-border rounded text-text text-sm" />
              <span className="text-xs text-muted">FPS (1 = en düşük CPU)</span>
            </div>
            <div>
              <label className="text-xs text-muted">{t('perfThermalConfidenceLabel')} {settings.detection.thermal_confidence_threshold.toFixed(2)}</label>
              <input type="range" min={0} max={1} step={0.05} value={settings.detection.thermal_confidence_threshold} onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, thermal_confidence_threshold: parseFloat(e.target.value) } })} className="w-full" />
              <p className="text-xs text-muted mt-1">{t('perfThermalConfidenceHint')}</p>
            </div>

            {showExpertControls ? (
              <>
                <div className="flex gap-2">
                  <input type="number" min={320} max={1920} value={settings.detection.inference_resolution[0]} onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, inference_resolution: [parseInt(e.target.value) || 640, settings.detection.inference_resolution[1]] } })} className="flex-1 px-2 py-1.5 bg-surface1 border border-border rounded text-text text-sm" />
                  <span className="text-muted self-center">×</span>
                  <input type="number" min={320} max={1920} value={settings.detection.inference_resolution[1]} onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, inference_resolution: [settings.detection.inference_resolution[0], parseInt(e.target.value) || 640] } })} className="flex-1 px-2 py-1.5 bg-surface1 border border-border rounded text-text text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted">Confidence {settings.detection.confidence_threshold.toFixed(2)}</label>
                  <input type="range" min={0} max={1} step={0.05} value={settings.detection.confidence_threshold} onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, confidence_threshold: parseFloat(e.target.value) } })} className="w-full" />
                </div>
                <div>
                  <label className="text-xs text-muted">NMS {settings.detection.nms_iou_threshold.toFixed(2)}</label>
                  <input type="range" min={0} max={1} step={0.05} value={settings.detection.nms_iou_threshold} onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, nms_iou_threshold: parseFloat(e.target.value) } })} className="w-full" />
                </div>
                <select
                  value={preset}
                  onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, aspect_ratio_preset: e.target.value as 'person' | 'thermal_person' | 'custom' } })}
                  className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm"
                >
                  <option value="person">{t('aspectRatioPresetPerson')}</option>
                  <option value="thermal_person">{t('aspectRatioPresetThermalPerson')}</option>
                  <option value="custom">{t('aspectRatioPresetCustom')}</option>
                </select>
                {isCustomAspect && (
                  <>
                    <div>
                      <label className="text-xs text-muted">Aspect min {settings.detection.aspect_ratio_min?.toFixed(2) || 0.3}</label>
                      <input type="range" min={0.05} max={1} step={0.05} value={settings.detection.aspect_ratio_min || 0.3} onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, aspect_ratio_min: parseFloat(e.target.value) } })} className="w-full" />
                    </div>
                    <div>
                      <label className="text-xs text-muted">Aspect max {settings.detection.aspect_ratio_max?.toFixed(2) || 3}</label>
                      <input type="range" min={1} max={5} step={0.1} value={settings.detection.aspect_ratio_max || 3} onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, aspect_ratio_max: parseFloat(e.target.value) } })} className="w-full" />
                    </div>
                  </>
                )}
              </>
            ) : (
              <p className="text-xs text-muted">{t('perfDetectionAdvancedHint')}</p>
            )}
          </div>

          {/* Motion */}
          <div className="space-y-3 p-4 rounded-lg bg-surface1/50">
            <h5 className="text-sm font-semibold text-text border-b border-border pb-1">{t('perfSectionMotion')}</h5>
            <div>
              <label className="text-xs text-muted block mb-1">Mode</label>
              <div className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text text-sm">
                Auto (global adaptive)
              </div>
            </div>
            <div>
              <label className="text-xs text-muted block mb-1">Auto Profile</label>
              <select
                value={settings.motion.auto_profile ?? 'low'}
                onChange={(e) =>
                  onChange({
                    ...settings,
                    motion: { ...settings.motion, mode: 'auto', auto_profile: e.target.value as 'low' | 'normal' | 'high' },
                  })
                }
                className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text text-sm"
              >
                <option value="low">Low (en az fake alarm)</option>
                <option value="normal">Normal</option>
                <option value="high">High (daha hassas)</option>
              </select>
            </div>
            <select
              value={settings.motion.algorithm ?? 'mog2'}
              onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, algorithm: e.target.value as 'frame_diff' | 'mog2' | 'knn' } })}
              className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text text-sm"
            >
              <option value="frame_diff">{t('motionAlgorithmFrameDiff')}</option>
              <option value="mog2">{t('motionAlgorithmMOG2')}</option>
              <option value="knn">{t('motionAlgorithmKNN')}</option>
            </select>
            <p className="text-xs text-muted">{algHint}</p>
            <div>
              <label className="text-xs text-muted">{t('motionSensitivityLabel', { value: settings.motion.sensitivity })}</label>
              <input
                type="number"
                min={1}
                max={10}
                value={settings.motion.sensitivity}
                onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, sensitivity: parseInt(e.target.value) || 1 } })}
                className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm disabled:opacity-60"
                disabled
              />
            </div>
            <div>
              <label className="text-xs text-muted">{t('motionMinAreaLabel')}</label>
              <input
                type="number"
                min={0}
                value={settings.motion.min_area}
                onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, min_area: parseInt(e.target.value) || 0 } })}
                className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm disabled:opacity-60"
                disabled
              />
            </div>
            <div>
              <label className="text-xs text-muted">{t('motionCooldownLabel')}</label>
              <input
                type="number"
                min={0}
                value={settings.motion.cooldown_seconds}
                onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, cooldown_seconds: parseInt(e.target.value) || 0 } })}
                className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm disabled:opacity-60"
                disabled
              />
            </div>
            <p className="text-xs text-muted">
              Product modunda manual motion kapali. Esikler kamera bazinda otomatik ogrenilir.
            </p>

            {/* Thermal Inference Suppression */}
            <h5 className="text-sm font-semibold text-text border-b border-border pb-1 mt-4">{t('thermalSuppressionTitle')}</h5>
            <p className="text-xs text-muted">{t('thermalSuppressionDesc')}</p>
            <label className="flex items-center gap-2 text-sm text-text">
              <input
                type="checkbox"
                checked={settings.motion.thermal_suppression_enabled ?? true}
                onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, thermal_suppression_enabled: e.target.checked } })}
              />
              {t('thermalSuppressionEnabled')}
            </label>
            {(settings.motion.thermal_suppression_enabled ?? true) && (
              showExpertControls ? (
                <div className="space-y-2 pl-2 border-l-2 border-border">
                  <div>
                    <label className="text-xs text-muted block mb-1">{t('thermalSuppressionStreak')}</label>
                    <input
                      type="number"
                      min={5}
                      max={100}
                      value={settings.motion.thermal_suppression_streak ?? 15}
                      onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, thermal_suppression_streak: parseInt(e.target.value) || 15 } })}
                      className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted block mb-1">{t('thermalSuppressionDuration')}</label>
                    <input
                      type="number"
                      min={5}
                      max={300}
                      value={settings.motion.thermal_suppression_duration ?? 30}
                      onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, thermal_suppression_duration: parseInt(e.target.value) || 30 } })}
                      className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted block mb-1">{t('thermalSuppressionWakeup')}</label>
                    <input
                      type="number"
                      min={1.5}
                      max={10}
                      step={0.5}
                      value={settings.motion.thermal_suppression_wakeup_ratio ?? 2.5}
                      onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, thermal_suppression_wakeup_ratio: parseFloat(e.target.value) || 2.5 } })}
                      className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm"
                    />
                  </div>
                </div>
              ) : (
                <p className="text-xs text-muted pl-1">
                  {t('thermalSuppressionSummary', {
                    streak: settings.motion.thermal_suppression_streak ?? 15,
                    duration: settings.motion.thermal_suppression_duration ?? 30,
                    ratio: (settings.motion.thermal_suppression_wakeup_ratio ?? 2.5).toFixed(1),
                  })}
                </p>
              )
            )}

            {/* Thermal - compact */}
            <h5 className="text-sm font-semibold text-text border-b border-border pb-1 mt-4">{t('perfSectionThermal')}</h5>
            <label className="flex items-center gap-2 text-sm text-text">
              <input type="checkbox" checked={settings.thermal.enable_enhancement} onChange={(e) => onChange({ ...settings, thermal: { ...settings.thermal, enable_enhancement: e.target.checked } })} />
              {t('perfThermalEnhance')}
            </label>
            {settings.thermal.enable_enhancement && (
              <>
                <select value={settings.thermal.enhancement_method} onChange={(e) => onChange({ ...settings, thermal: { ...settings.thermal, enhancement_method: e.target.value as Settings['thermal']['enhancement_method'] } })} className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm">
                  <option value="clahe">CLAHE</option>
                  <option value="histogram">{t('histogram')}</option>
                  <option value="none">{t('none')}</option>
                </select>
                {settings.thermal.enhancement_method === 'clahe' && (
                  <div>
                    <label className="text-xs text-muted">CLAHE limit {settings.thermal.clahe_clip_limit.toFixed(1)}</label>
                    <input type="range" min={1} max={5} step={0.5} value={settings.thermal.clahe_clip_limit} onChange={(e) => onChange({ ...settings, thermal: { ...settings.thermal, clahe_clip_limit: parseFloat(e.target.value) } })} className="w-full" />
                  </div>
                )}
                <button type="button" onClick={() => setShowAdvancedThermal(!showAdvancedThermal)} className="flex items-center gap-1 text-xs text-muted hover:text-text">
                  {showAdvancedThermal ? <MdExpandLess /> : <MdExpandMore />} {t('perfAdvanced')}
                </button>
                {showAdvancedThermal && settings.thermal.enhancement_method === 'clahe' && (
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <input type="number" min={4} max={16} value={settings.thermal.clahe_tile_size[0]} onChange={(e) => onChange({ ...settings, thermal: { ...settings.thermal, clahe_tile_size: [parseInt(e.target.value) || 8, settings.thermal.clahe_tile_size[1]] } })} className="px-2 py-1 bg-surface1 border border-border rounded text-sm" placeholder="Grid" />
                    <input type="number" min={4} max={16} value={settings.thermal.clahe_tile_size[1]} onChange={(e) => onChange({ ...settings, thermal: { ...settings.thermal, clahe_tile_size: [settings.thermal.clahe_tile_size[0], parseInt(e.target.value) || 8] } })} className="px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                  </div>
                )}
                {showAdvancedThermal && (
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <input type="number" min={1} max={9} step={2} value={settings.thermal.gaussian_blur_kernel[0]} onChange={(e) => onChange({ ...settings, thermal: { ...settings.thermal, gaussian_blur_kernel: [parseInt(e.target.value) || 3, settings.thermal.gaussian_blur_kernel[1]] } })} className="px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                    <input type="number" min={1} max={9} step={2} value={settings.thermal.gaussian_blur_kernel[1]} onChange={(e) => onChange({ ...settings, thermal: { ...settings.thermal, gaussian_blur_kernel: [settings.thermal.gaussian_blur_kernel[0], parseInt(e.target.value) || 3] } })} className="px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                  </div>
                )}
              </>
            )}
          </div>

          {/* Stream */}
          <div className="space-y-3 p-4 rounded-lg bg-surface1/50">
            <h5 className="text-sm font-semibold text-text border-b border-border pb-1">{t('perfSectionStream')}</h5>
            <select value={settings.stream.protocol} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, protocol: e.target.value as Settings['stream']['protocol'] } })} className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text text-sm">
              <option value="tcp">TCP</option>
              <option value="udp">UDP</option>
            </select>
            <select value={settings.stream.capture_backend || 'auto'} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, capture_backend: e.target.value as Settings['stream']['capture_backend'] } })} className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text text-sm">
              <option value="auto">{t('streamBackendAuto')}</option>
              <option value="opencv">{t('streamBackendOpenCV')}</option>
              <option value="ffmpeg">{t('streamBackendFFmpeg')}</option>
            </select>
            <div>
              <label className="text-xs text-muted">{t('bufferSize')}</label>
              <input type="number" min={1} value={settings.stream.buffer_size} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, buffer_size: parseInt(e.target.value) || 1 } })} className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm" />
            </div>
            <button type="button" onClick={() => setShowAdvancedStream(!showAdvancedStream)} className="flex items-center gap-1 text-xs text-muted hover:text-text">
              {showAdvancedStream ? <MdExpandLess /> : <MdExpandMore />} {t('perfConnectionReconnect')}
            </button>
            {showAdvancedStream && (
              <div className="space-y-2 mt-2">
                <div>
                  <label className="text-xs text-muted">{t('reconnectDelay')}</label>
                  <input type="number" min={1} value={settings.stream.reconnect_delay_seconds} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, reconnect_delay_seconds: parseInt(e.target.value) || 1 } })} className="w-full px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted">{t('maxReconnectAttempts')}</label>
                  <input type="number" min={1} value={settings.stream.max_reconnect_attempts} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, max_reconnect_attempts: parseInt(e.target.value) || 1 } })} className="w-full px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted">{t('readFailureThreshold')}</label>
                  <input type="number" min={1} value={settings.stream.read_failure_threshold} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, read_failure_threshold: parseInt(e.target.value) || 1 } })} className="w-full px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                </div>
                <div>
                  <label className="text-xs text-muted">{t('readFailureTimeout')}</label>
                  <input type="number" min={1} step={0.5} value={settings.stream.read_failure_timeout_seconds} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, read_failure_timeout_seconds: parseFloat(e.target.value) || 1 } })} className="w-full px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-between items-center mt-4 pt-4 border-t border-border">
          <p className="text-xs text-muted">{t('perfManualHint')}</p>
          <button onClick={handleManualSave} className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors text-sm">
            {t('perfManualSave')}
          </button>
        </div>
      </div>

      {/* Advanced Performance - collapsible */}
      <div className="bg-surface2 border border-border rounded-lg p-4">
        <button type="button" onClick={() => setShowAdvancedPerf(!showAdvancedPerf)} className="w-full flex items-center justify-between text-text font-medium">
          <span>🚀 Worker & Metrics</span>
          {showAdvancedPerf ? <MdExpandLess /> : <MdExpandMore />}
        </button>
        {showAdvancedPerf && (
          <div className="mt-4 space-y-4 pt-4 border-t border-border">
            <div>
              <label className="text-sm text-text block mb-1">Worker Mode</label>
              <select
                value={settings.performance?.worker_mode || 'threading'}
                onChange={(e) => onChange({ ...settings, performance: { ...(settings.performance || { enable_metrics: false, metrics_port: 9090 }), worker_mode: e.target.value as 'threading' | 'multiprocessing' } })}
                className="w-full px-3 py-2 bg-surface1 border border-border rounded text-text text-sm"
              >
                <option value="threading">{t('workerModeThreading')}</option>
                <option value="multiprocessing">{t('workerModeMultiprocessing')}</option>
              </select>
              {settings.performance?.worker_mode === 'multiprocessing' && (
                <p className="text-xs text-warning mt-1">⚠️ {t('perfMultiprocessingWarning')}</p>
              )}
              <p className="text-xs text-muted mt-1">{t('perfWorkerModeRestart')}</p>
            </div>
            <div className="p-3 bg-surface1 rounded text-xs text-muted">
              {t('perfYoloHint')}
            </div>
            <label className="flex items-center gap-2 text-sm text-text">
              <input type="checkbox" checked={settings.performance?.enable_metrics || false} onChange={(e) => onChange({ ...settings, performance: { ...(settings.performance || { worker_mode: 'threading', metrics_port: 9090 }), enable_metrics: e.target.checked } })} />
              Prometheus Metrics
            </label>
            {settings.performance?.enable_metrics && (
              <div>
                <label className="text-xs text-muted">Port</label>
                <input type="number" min={1024} max={65535} value={settings.performance?.metrics_port || 9090} onChange={(e) => onChange({ ...settings, performance: { ...(settings.performance || {}), metrics_port: parseInt(e.target.value) || 9090 } })} className="w-24 px-2 py-1 bg-surface1 border border-border rounded text-sm" />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tips - compact */}
      <div className="bg-surface2 border-l-4 border-warning p-3 rounded-lg">
        <h4 className="text-sm font-semibold text-text mb-1">⚡ {t('perfTipsTitle')}</h4>
        <ul className="text-xs text-muted space-y-0.5">
          <li>{t('perfTipDetectionModel')}</li>
          <li>{t('perfTipMotion')}</li>
          <li>{t('perfTipStream')}</li>
        </ul>
      </div>
    </div>
  )
}
