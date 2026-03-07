/**
 * Camera Settings tab — simplified to two quick-pick modes.
 * All advanced controls hidden behind "Expert" toggle.
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
    desc: 'Az yanlış alarm. Hırsız alarm sistemi için önerilen.',
    updates: (s) => ({
      detection: { ...s.detection, model: 'yolov8s-person', inference_fps: 5, inference_resolution: [640, 640], confidence_threshold: 0.50, thermal_confidence_threshold: 0.44 },
      motion:    { ...s.motion,    mode: 'auto', auto_profile: 'normal', algorithm: 'mog2', sensitivity: 6, min_area: 450, cooldown_seconds: 6, thermal_suppression_enabled: true, thermal_suppression_streak: 12, thermal_suppression_duration: 20, thermal_suppression_wakeup_ratio: 2.0 },
      thermal:   { ...s.thermal,   enable_enhancement: true, enhancement_method: 'clahe', clahe_clip_limit: 2.0, clahe_tile_size: [32, 32], gaussian_blur_kernel: [3, 3] },
      stream:    { ...s.stream,    protocol: 'tcp', capture_backend: 'ffmpeg', buffer_size: 1, reconnect_delay_seconds: 5, max_reconnect_attempts: 20, read_failure_threshold: 5, read_failure_timeout_seconds: 15 },
    }),
  },
  sensitive: {
    icon: '🚨',
    label: 'Hassas',
    desc: 'Daha az kaçırma. Bazı yanlış alarm olabilir.',
    updates: (s) => ({
      detection: { ...s.detection, model: 'yolov8s-person', inference_fps: 8, inference_resolution: [640, 640], confidence_threshold: 0.45, thermal_confidence_threshold: 0.38 },
      motion:    { ...s.motion,    mode: 'auto', auto_profile: 'high', algorithm: 'mog2', sensitivity: 6, min_area: 260, cooldown_seconds: 4, thermal_suppression_enabled: true, thermal_suppression_streak: 15, thermal_suppression_duration: 12, thermal_suppression_wakeup_ratio: 1.8 },
      thermal:   { ...s.thermal,   enable_enhancement: true, enhancement_method: 'clahe', clahe_clip_limit: 2.2, clahe_tile_size: [32, 32], gaussian_blur_kernel: [3, 3] },
      stream:    { ...s.stream,    protocol: 'tcp', capture_backend: 'ffmpeg', buffer_size: 1, reconnect_delay_seconds: 3, max_reconnect_attempts: 20, read_failure_threshold: 3, read_failure_timeout_seconds: 10 },
    }),
  },
}

const ALGORITHM_HINTS: Record<string, string> = {
  frame_diff: 'Basit, hızlı. Rüzgarlı ortamda fazla alarm.',
  mog2: 'Arka plan öğrenir, gölge azaltır. Önerilen.',
  knn: 'MOG2 alternatifi, daha dayanıklı.',
}

export const CameraSettingsTab: React.FC<CameraSettingsTabProps> = ({ settings, onChange, onSave }) => {
  const [showExpert, setShowExpert] = useState(false)
  const [showStreamAdvanced, setShowStreamAdvanced] = useState(false)

  const apply = async (mode: QuickMode) => {
    const updates = QUICK_MODES[mode].updates(settings)
    onChange({ ...settings, ...updates })
    await onSave(updates)
  }

  const saveExpert = async () => {
    await onSave({ detection: settings.detection, motion: settings.motion, thermal: settings.thermal, stream: settings.stream, performance: settings.performance })
  }

  return (
    <div className="space-y-6">

      {/* ── Quick pick ── */}
      <div className="bg-surface2 border border-border rounded-lg p-5">
        <h3 className="text-base font-semibold text-text mb-1">Hızlı Mod</h3>
        <p className="text-xs text-muted mb-4">Seç ve uygula. Tüm kameralara aynı anda geçer.</p>
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

      {/* ── Inference backend (always visible, most impactful) ── */}
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
        <p className="text-xs text-muted mt-2">Değişiklik addon yeniden başlatıldıktan sonra etkinleşir.</p>
      </div>

      {/* ── Expert toggle ── */}
      <div className="bg-surface2 border border-border rounded-lg">
        <button
          type="button"
          onClick={() => setShowExpert(!showExpert)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-text"
        >
          <span>Uzman Ayarlar</span>
          {showExpert ? <MdExpandLess /> : <MdExpandMore />}
        </button>

        {showExpert && (
          <div className="px-4 pb-4 pt-1 border-t border-border space-y-5">
            <p className="text-xs text-muted">Bu ayarları yalnızca hızlı modları fine-tune etmek için kullan.</p>

            <div className="grid gap-5 md:grid-cols-3">

              {/* Detection */}
              <div className="space-y-3 p-3 rounded-lg bg-surface1/50">
                <h5 className="text-xs font-semibold text-text border-b border-border pb-1 uppercase tracking-wide">Detection</h5>
                <select
                  value={settings.detection.model}
                  onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, model: e.target.value as Settings['detection']['model'] } })}
                  className="w-full px-3 py-2 bg-surface1 border border-border rounded text-text text-sm"
                >
                  <option value="yolov8n-person">YOLOv8n (hızlı)</option>
                  <option value="yolov8s-person">YOLOv8s (dengeli)</option>
                  <option value="yolov9t">YOLOv9t</option>
                  <option value="yolov9s">YOLOv9s (en doğru)</option>
                </select>
                <div className="flex gap-2 items-center">
                  <input
                    type="number" min={1} max={30}
                    value={settings.detection.inference_fps}
                    onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, inference_fps: parseInt(e.target.value) || 1 } })}
                    className="w-16 px-2 py-1.5 bg-surface1 border border-border rounded text-text text-sm"
                  />
                  <span className="text-xs text-muted">FPS</span>
                </div>
                <div>
                  <label className="text-xs text-muted">Termal eşik: {settings.detection.thermal_confidence_threshold.toFixed(2)}</label>
                  <input
                    type="range" min={0.25} max={0.70} step={0.01}
                    value={settings.detection.thermal_confidence_threshold}
                    onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, thermal_confidence_threshold: parseFloat(e.target.value) } })}
                    className="w-full"
                  />
                  <p className="text-xs text-muted mt-0.5">Düşür = daha fazla tespit, yükselt = daha az yanlış alarm</p>
                </div>
                <div>
                  <label className="text-xs text-muted">Color eşik: {settings.detection.confidence_threshold.toFixed(2)}</label>
                  <input
                    type="range" min={0.25} max={0.80} step={0.01}
                    value={settings.detection.confidence_threshold}
                    onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, confidence_threshold: parseFloat(e.target.value) } })}
                    className="w-full"
                  />
                </div>
                <div className="flex gap-2 items-center">
                  <input
                    type="number" min={320} max={1280}
                    value={settings.detection.inference_resolution[0]}
                    onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, inference_resolution: [parseInt(e.target.value) || 640, settings.detection.inference_resolution[1]] } })}
                    className="flex-1 px-2 py-1.5 bg-surface1 border border-border rounded text-text text-xs"
                  />
                  <span className="text-muted text-xs">×</span>
                  <input
                    type="number" min={320} max={1280}
                    value={settings.detection.inference_resolution[1]}
                    onChange={(e) => onChange({ ...settings, detection: { ...settings.detection, inference_resolution: [settings.detection.inference_resolution[0], parseInt(e.target.value) || 640] } })}
                    className="flex-1 px-2 py-1.5 bg-surface1 border border-border rounded text-text text-xs"
                  />
                </div>
              </div>

              {/* Motion */}
              <div className="space-y-3 p-3 rounded-lg bg-surface1/50">
                <h5 className="text-xs font-semibold text-text border-b border-border pb-1 uppercase tracking-wide">Motion</h5>
                <select
                  value={settings.motion.auto_profile ?? 'normal'}
                  onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, mode: 'auto', auto_profile: e.target.value as 'low' | 'normal' | 'high' } })}
                  className="w-full px-3 py-2 bg-surface1 border border-border rounded text-text text-sm"
                >
                  <option value="low">Low — en az alarm</option>
                  <option value="normal">Normal</option>
                  <option value="high">High — daha hassas</option>
                </select>
                <select
                  value={settings.motion.algorithm ?? 'mog2'}
                  onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, algorithm: e.target.value as 'frame_diff' | 'mog2' | 'knn' } })}
                  className="w-full px-3 py-2 bg-surface1 border border-border rounded text-text text-sm"
                >
                  <option value="frame_diff">Frame Diff</option>
                  <option value="mog2">MOG2</option>
                  <option value="knn">KNN</option>
                </select>
                <p className="text-xs text-muted">{ALGORITHM_HINTS[settings.motion.algorithm ?? 'mog2']}</p>
                <label className="flex items-center gap-2 text-sm text-text mt-2">
                  <input
                    type="checkbox"
                    checked={settings.motion.thermal_suppression_enabled ?? true}
                    onChange={(e) => onChange({ ...settings, motion: { ...settings.motion, thermal_suppression_enabled: e.target.checked } })}
                  />
                  Termal baskılama etkin
                </label>
                <p className="text-xs text-muted">Termal kameralarda tekrarlayan boş tespitleri baskılar.</p>
                {/* Thermal enhancement */}
                <label className="flex items-center gap-2 text-sm text-text mt-2">
                  <input
                    type="checkbox"
                    checked={settings.thermal.enable_enhancement}
                    onChange={(e) => onChange({ ...settings, thermal: { ...settings.thermal, enable_enhancement: e.target.checked } })}
                  />
                  CLAHE iyileştirme
                </label>
                {settings.thermal.enable_enhancement && (
                  <div>
                    <label className="text-xs text-muted">CLAHE limit: {settings.thermal.clahe_clip_limit.toFixed(1)}</label>
                    <input
                      type="range" min={1} max={5} step={0.5}
                      value={settings.thermal.clahe_clip_limit}
                      onChange={(e) => onChange({ ...settings, thermal: { ...settings.thermal, clahe_clip_limit: parseFloat(e.target.value) } })}
                      className="w-full"
                    />
                  </div>
                )}
              </div>

              {/* Stream */}
              <div className="space-y-3 p-3 rounded-lg bg-surface1/50">
                <h5 className="text-xs font-semibold text-text border-b border-border pb-1 uppercase tracking-wide">Stream</h5>
                <select
                  value={settings.stream.protocol}
                  onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, protocol: e.target.value as 'tcp' | 'udp' } })}
                  className="w-full px-3 py-2 bg-surface1 border border-border rounded text-text text-sm"
                >
                  <option value="tcp">TCP</option>
                  <option value="udp">UDP</option>
                </select>
                <select
                  value={settings.stream.capture_backend || 'auto'}
                  onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, capture_backend: e.target.value as Settings['stream']['capture_backend'] } })}
                  className="w-full px-3 py-2 bg-surface1 border border-border rounded text-text text-sm"
                >
                  <option value="auto">Auto</option>
                  <option value="ffmpeg">FFmpeg</option>
                  <option value="opencv">OpenCV</option>
                </select>
                <div>
                  <label className="text-xs text-muted">Buffer Size</label>
                  <input
                    type="number" min={1}
                    value={settings.stream.buffer_size}
                    onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, buffer_size: parseInt(e.target.value) || 1 } })}
                    className="w-full px-3 py-1.5 bg-surface1 border border-border rounded text-text text-sm"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => setShowStreamAdvanced(!showStreamAdvanced)}
                  className="flex items-center gap-1 text-xs text-muted hover:text-text"
                >
                  {showStreamAdvanced ? <MdExpandLess /> : <MdExpandMore />} Reconnect ayarları
                </button>
                {showStreamAdvanced && (
                  <div className="space-y-2">
                    <div>
                      <label className="text-xs text-muted">Reconnect delay (s)</label>
                      <input type="number" min={1} value={settings.stream.reconnect_delay_seconds} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, reconnect_delay_seconds: parseInt(e.target.value) || 1 } })} className="w-full px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                    </div>
                    <div>
                      <label className="text-xs text-muted">Max reconnect attempts</label>
                      <input type="number" min={1} value={settings.stream.max_reconnect_attempts} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, max_reconnect_attempts: parseInt(e.target.value) || 1 } })} className="w-full px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                    </div>
                    <div>
                      <label className="text-xs text-muted">Read failure threshold</label>
                      <input type="number" min={1} value={settings.stream.read_failure_threshold} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, read_failure_threshold: parseInt(e.target.value) || 1 } })} className="w-full px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                    </div>
                    <div>
                      <label className="text-xs text-muted">Read failure timeout (s)</label>
                      <input type="number" min={1} step={0.5} value={settings.stream.read_failure_timeout_seconds} onChange={(e) => onChange({ ...settings, stream: { ...settings.stream, read_failure_timeout_seconds: parseFloat(e.target.value) || 1 } })} className="w-full px-2 py-1 bg-surface1 border border-border rounded text-sm" />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Worker & Metrics */}
            <div className="border-t border-border pt-4 space-y-3">
              <h5 className="text-xs font-semibold text-text uppercase tracking-wide">Worker & Metrics</h5>
              <select
                value={settings.performance?.worker_mode || 'threading'}
                onChange={(e) => onChange({ ...settings, performance: { ...(settings.performance || { enable_metrics: false, metrics_port: 9090 }), worker_mode: e.target.value as 'threading' | 'multiprocessing' } })}
                className="w-full px-3 py-2 bg-surface1 border border-border rounded text-text text-sm"
              >
                <option value="threading">Threading (önerilen)</option>
                <option value="multiprocessing">Multiprocessing (deneysel)</option>
              </select>
              {settings.performance?.worker_mode === 'multiprocessing' && (
                <p className="text-xs text-warning">⚠️ Multiprocessing deneyseldir, kararlılık sorunları olabilir.</p>
              )}
              <label className="flex items-center gap-2 text-sm text-text">
                <input
                  type="checkbox"
                  checked={settings.performance?.enable_metrics || false}
                  onChange={(e) => onChange({ ...settings, performance: { ...(settings.performance || { worker_mode: 'threading', metrics_port: 9090 }), enable_metrics: e.target.checked } })}
                />
                Prometheus Metrics
              </label>
            </div>

            <div className="flex justify-end pt-2 border-t border-border">
              <button
                onClick={saveExpert}
                className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors text-sm"
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
