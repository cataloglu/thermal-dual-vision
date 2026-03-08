/**
 * Camera Settings tab.
 * Two quick-pick buttons + minimal expert section (5 controls only).
 * Everything else is fixed at sensible defaults via the quick modes.
 */
import React, { useState } from 'react'
import { MdExpandMore, MdExpandLess } from 'react-icons/md'
import type { Settings } from '../../types/api'

interface CameraSettingsTabProps {
  settings: Settings
  onChange: (settings: Settings) => void
  onSave: (updates: Partial<Settings>) => Promise<void>
}

type QuickMode = 'stable' | 'sensitive'

const QUICK_MODES: Record<QuickMode, { label: string; desc: string; icon: string; updates: (s: Settings) => Partial<Settings> }> = {
  stable: {
    icon: '🔒',
    label: 'Kararlı',
    desc: 'Az yanlış alarm. Hırsız alarm için önerilen.',
    updates: (s) => ({
      detection: { ...s.detection, model: 'yolov8s-thermal', inference_fps: 5, inference_resolution: [640, 640], confidence_threshold: 0.40 },
      motion:    { ...s.motion,    mode: 'auto', auto_profile: 'normal', algorithm: 'mog2', sensitivity: 6, min_area: 450, cooldown_seconds: 6 },
      thermal:   { ...s.thermal,   enable_enhancement: false, enhancement_method: 'clahe', clahe_clip_limit: 2.0, clahe_tile_size: [32, 32], gaussian_blur_kernel: [3, 3] },
      stream:    { ...s.stream,    protocol: 'tcp', capture_backend: 'ffmpeg', buffer_size: 1, reconnect_delay_seconds: 5, max_reconnect_attempts: 20, read_failure_threshold: 5, read_failure_timeout_seconds: 15 },
    }),
  },
  sensitive: {
    icon: '🚨',
    label: 'Hassas',
    desc: 'Daha az kaçırma. Bazı yanlış alarm olabilir.',
    updates: (s) => ({
      detection: { ...s.detection, model: 'yolov8s-thermal', inference_fps: 8, inference_resolution: [640, 640], confidence_threshold: 0.35 },
      motion:    { ...s.motion,    mode: 'auto', auto_profile: 'high', algorithm: 'mog2', sensitivity: 6, min_area: 260, cooldown_seconds: 4 },
      thermal:   { ...s.thermal,   enable_enhancement: false, enhancement_method: 'clahe', clahe_clip_limit: 2.0, clahe_tile_size: [32, 32], gaussian_blur_kernel: [3, 3] },
      stream:    { ...s.stream,    protocol: 'tcp', capture_backend: 'ffmpeg', buffer_size: 1, reconnect_delay_seconds: 3, max_reconnect_attempts: 20, read_failure_threshold: 3, read_failure_timeout_seconds: 10 },
    }),
  },
}

export const CameraSettingsTab: React.FC<CameraSettingsTabProps> = ({ settings, onChange, onSave }) => {
  const [showExpert, setShowExpert] = useState(false)

  const apply = async (mode: QuickMode) => {
    const updates = QUICK_MODES[mode].updates(settings)
    onChange({ ...settings, ...updates })
    await onSave(updates)
  }

  const saveExpert = async () => {
    await onSave({ detection: settings.detection, motion: settings.motion, thermal: settings.thermal })
  }

  return (
    <div className="space-y-6">

      {/* ── Quick pick ── */}
      <div className="bg-surface2 border border-border rounded-lg p-5">
        <h3 className="text-base font-semibold text-text mb-1">Mod Seç</h3>
        <p className="text-xs text-muted mb-4">Tüm kameralara tek tıkla uygulanır.</p>
        <div className="grid grid-cols-2 gap-3">
          {(Object.entries(QUICK_MODES) as [QuickMode, typeof QUICK_MODES[QuickMode]][]).map(([id, mode]) => (
            <button
              key={id}
              type="button"
              onClick={() => apply(id)}
              className="p-4 rounded-xl border-2 border-border bg-surface1 text-left hover:border-accent hover:bg-surface1/80 transition-all"
            >
              <div className="text-2xl mb-2">{mode.icon}</div>
              <div className="font-semibold text-text text-sm">{mode.label}</div>
              <div className="text-xs text-muted mt-1">{mode.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Backend (always visible) ── */}
      <div className="bg-surface2 border border-border rounded-lg p-4">
        <label className="text-sm font-semibold text-text block mb-2">Inference Backend</label>
        <select
          value={settings.detection.inference_backend || 'auto'}
          onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, inference_backend: e.target.value as Settings['detection']['inference_backend'] } })}
          className="w-full px-3 py-2.5 bg-surface1 border border-border rounded-lg text-text text-sm"
        >
          <option value="auto">Auto (TensorRT → OpenVINO → ONNX → CPU)</option>
          <option value="openvino">OpenVINO (Intel iGPU/NPU)</option>
          <option value="tensorrt">TensorRT (NVIDIA GPU)</option>
          <option value="onnx">ONNX</option>
          <option value="cpu">CPU (PyTorch)</option>
        </select>
        <p className="text-xs text-muted mt-2">Addon yeniden başlatılınca etkinleşir.</p>
      </div>

      {/* ── Expert (5 controls only) ── */}
      <div className="bg-surface2 border border-border rounded-lg">
        <button
          type="button"
          onClick={() => setShowExpert(!showExpert)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-text"
        >
          <span>İnce Ayar</span>
          {showExpert ? <MdExpandLess /> : <MdExpandMore />}
        </button>

        {showExpert && (
          <div className="px-4 pb-5 pt-3 border-t border-border space-y-4">
            <p className="text-xs text-muted">Sadece hızlı modun üzerine küçük düzeltme yapmak için.</p>

            {/* Model */}
            <div>
              <label className="text-sm font-medium text-text block mb-1.5">Model</label>
              <select
                value={settings.detection.model}
                onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, model: e.target.value as Settings['detection']['model'] } })}
                className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text text-sm"
              >
                <option value="yolov8s-thermal">⭐ YOLOv8s Thermal — termal kameralar için özel</option>
                <option value="yolov8n-person">YOLOv8n — hızlı, düşük CPU</option>
                <option value="yolov8s-person">YOLOv8s — dengeli</option>
                <option value="yolov9t">YOLOv9t</option>
                <option value="yolov9s">YOLOv9s — en doğru, yüksek CPU</option>
              </select>
              {settings.detection.model === 'yolov8s-thermal' && (
                <p className="text-xs text-accent mt-1">
                  ⭐ Termal kameralar için fine-tune edilmiş model. İlk yüklemede HuggingFace'den otomatik indirilir (~6MB). v5.0+ motion-crop ile standart eşik yeterlidir.
                </p>
              )}
            </div>

            {/* FPS */}
            <div>
              <label className="text-sm font-medium text-text block mb-1.5">
                Inference FPS
                <span className="text-xs font-normal text-muted ml-2">— düşük = daha az CPU</span>
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range" min={1} max={15} step={1}
                  value={settings.detection.inference_fps}
                  onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, inference_fps: parseInt(e.target.value) } })}
                  className="flex-1"
                />
                <span className="text-sm font-mono text-text w-8 text-right">{settings.detection.inference_fps}</span>
              </div>
            </div>

            {/* Motion profile */}
            <div>
              <label className="text-sm font-medium text-text block mb-1.5">Hareket Hassasiyeti</label>
              <select
                value={settings.motion.auto_profile ?? 'normal'}
                onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, mode: 'auto', auto_profile: e.target.value as 'low' | 'normal' | 'high' } })}
                className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text text-sm"
              >
                <option value="low">Düşük — en az alarm, büyük hareket gerekir</option>
                <option value="normal">Normal — dengeli</option>
                <option value="high">Yüksek — küçük hareket yeterli</option>
              </select>
            </div>

            <div className="flex justify-end pt-1">
              <button
                onClick={saveExpert}
                className="px-5 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors text-sm font-medium"
              >
                Kaydet
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
