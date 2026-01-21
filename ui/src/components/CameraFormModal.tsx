import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { MdClose } from 'react-icons/md'
import { api, testCamera } from '../services/api'
import type { CameraTestResponse } from '../types/api'
import toast from 'react-hot-toast'

interface Camera {
  id?: string
  name: string
  type: string
  enabled: boolean
  rtsp_url_thermal?: string
  rtsp_url_color?: string
  channel_color?: number
  channel_thermal?: number
  detection_source: string
  stream_roles: string[]
}

interface CameraFormModalProps {
  camera?: Camera | null
  onClose: () => void
  onSave: () => void
}

export function CameraFormModal({ camera, onClose, onSave }: CameraFormModalProps) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    name: '',
    type: 'thermal',
    enabled: true,
    rtsp_url_thermal: '',
    rtsp_url_color: '',
    channel_color: 102,
    channel_thermal: 202,
    detection_source: 'thermal',
    stream_roles: ['detect', 'live'] as string[],
  })
  
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<CameraTestResponse | null>(null)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  useEffect(() => {
    if (camera) {
      setFormData({
        name: camera.name,
        type: camera.type,
        enabled: camera.enabled,
        rtsp_url_thermal: camera.rtsp_url_thermal || '',
        rtsp_url_color: camera.rtsp_url_color || '',
        channel_color: camera.channel_color || 102,
        channel_thermal: camera.channel_thermal || 202,
        detection_source: camera.detection_source,
        stream_roles: camera.stream_roles,
      })
    }
  }, [camera])

  const handleTest = async () => {
    const validationErrors = validate()
    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      toast.error('Test için gerekli alanları doldurun')
      return
    }
    setTesting(true)
    setTestResult(null)
    setErrors([])

    try {
      const response = await testCamera({
        type: formData.type as 'color' | 'thermal' | 'dual',
        rtsp_url_thermal: formData.rtsp_url_thermal || undefined,
        rtsp_url_color: formData.rtsp_url_color || undefined,
      })
      
      setTestResult(response)
      if (response.success) {
        toast.success(`Test başarılı! Gecikme: ${response.latency_ms}ms`)
      } else {
        toast.error(response.error_reason || 'Test başarısız')
      }
    } catch (error) {
      toast.error('Bağlantı test edilemedi')
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    const validationErrors = validate()
    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      toast.error('Eksik veya hatalı alanlar var')
      return
    }

    setSaving(true)

    try {
      if (camera) {
        await api.updateCamera(camera.id as string, formData)
      } else {
        await api.createCamera(formData)
      }

      toast.success(camera ? 'Kamera güncellendi' : 'Kamera eklendi')
      onSave()
      onClose()
    } catch (error) {
      console.error('Failed to save camera:', error)
      toast.error('Kamera kaydedilemedi')
    } finally {
      setSaving(false)
    }
  }

  const toggleRole = (role: string) => {
    setFormData(prev => ({
      ...prev,
      stream_roles: prev.stream_roles.includes(role)
        ? prev.stream_roles.filter(r => r !== role)
        : [...prev.stream_roles, role]
    }))
  }

  const validate = () => {
    const nextErrors: string[] = []
    if (!formData.name.trim()) {
      nextErrors.push('Kamera adı gerekli')
    }
    const isRtsp = (value: string) => value.trim().startsWith('rtsp://')
    if (formData.type === 'thermal' || formData.type === 'dual') {
      if (!formData.rtsp_url_thermal.trim()) {
        nextErrors.push('Termal RTSP adresi gerekli')
      } else if (!isRtsp(formData.rtsp_url_thermal)) {
        nextErrors.push('Termal RTSP adresi rtsp:// ile başlamalı')
      }
    }
    if (formData.type === 'color' || formData.type === 'dual') {
      if (!formData.rtsp_url_color.trim()) {
        nextErrors.push('Renkli RTSP adresi gerekli')
      } else if (!isRtsp(formData.rtsp_url_color)) {
        nextErrors.push('Renkli RTSP adresi rtsp:// ile başlamalı')
      }
    }
    if (formData.channel_color && formData.channel_color < 1) {
      nextErrors.push('Renkli kanal numarası geçersiz')
    }
    if (formData.channel_thermal && formData.channel_thermal < 1) {
      nextErrors.push('Termal kanal numarası geçersiz')
    }
    return nextErrors
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-surface1 border border-border rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-surface1 border-b border-border p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-text">
            {camera ? t('edit') : t('add')} {t('camera')}
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-surface2 rounded-lg transition-colors">
            <MdClose className="text-2xl text-muted" />
          </button>
        </div>

        {/* Form */}
        <div className="p-6 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              Kamera Adı *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ön Kapı"
              className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>

          {/* Type */}
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              Kamera Tipi *
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="thermal">Termal</option>
              <option value="color">Renkli</option>
              <option value="dual">İkili (Termal + Renkli)</option>
            </select>
          </div>

          {/* Thermal URL */}
          {(formData.type === 'thermal' || formData.type === 'dual') && (
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Termal RTSP Adresi *
              </label>
              <input
                type="text"
                value={formData.rtsp_url_thermal}
                onChange={(e) => setFormData({ ...formData, rtsp_url_thermal: e.target.value })}
                placeholder="rtsp://192.168.1.100:554/Streaming/Channels/201"
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent font-mono text-sm"
              />
            </div>
          )}

          {/* Color URL */}
          {(formData.type === 'color' || formData.type === 'dual') && (
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Renkli RTSP Adresi *
              </label>
              <input
                type="text"
                value={formData.rtsp_url_color}
                onChange={(e) => setFormData({ ...formData, rtsp_url_color: e.target.value })}
                placeholder="rtsp://192.168.1.100:554/Streaming/Channels/101"
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent font-mono text-sm"
              />
            </div>
          )}

          {/* Channel Numbers */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Renkli Kanal
              </label>
              <input
                type="number"
                min={1}
                value={formData.channel_color ?? 102}
                onChange={(e) => setFormData({ ...formData, channel_color: Number(e.target.value) })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Termal Kanal
              </label>
              <input
                type="number"
                min={1}
                value={formData.channel_thermal ?? 202}
                onChange={(e) => setFormData({ ...formData, channel_thermal: Number(e.target.value) })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
          </div>

          {/* Detection Source */}
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              Algılama Kaynağı
            </label>
            <select
              value={formData.detection_source}
              onChange={(e) => setFormData({ ...formData, detection_source: e.target.value })}
              className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="auto">Otomatik</option>
              <option value="thermal">Termal</option>
              <option value="color">Renkli</option>
            </select>
          </div>

          {/* Stream Roles */}
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              Stream Rolleri
            </label>
            <div className="flex gap-3">
              {['detect', 'live', 'record'].map((role) => (
                <label key={role} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.stream_roles.includes(role)}
                    onChange={() => toggleRole(role)}
                    className="w-4 h-4 accent-accent"
                  />
                  <span className="text-sm text-text capitalize">{role}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Enabled */}
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                className="w-4 h-4 accent-accent"
              />
              <span className="text-sm text-text">Kamerayı Etkinleştir</span>
            </label>
          </div>

          {/* Validation Errors */}
          {errors.length > 0 && (
            <div className="bg-error/10 border border-error/50 rounded-lg p-4">
              <ul className="text-sm text-error space-y-1">
                {errors.map((err) => (
                  <li key={err}>• {err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Test Button */}
          <div className="pt-4 border-t border-border">
            <button
              onClick={handleTest}
              disabled={testing || validate().length > 0}
              className="w-full px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors disabled:opacity-50"
            >
              {testing ? 'Test Ediliyor...' : 'Bağlantıyı Test Et'}
            </button>
          </div>

          {/* Test Result */}
          {testResult && testResult.success && testResult.snapshot_base64 && (
            <div className="pt-4">
              <h4 className="text-sm font-medium text-text mb-2">Görüntü</h4>
              <div className="border border-border rounded-lg overflow-hidden">
                <img src={testResult.snapshot_base64} alt="Snapshot" className="w-full h-auto" />
              </div>
              <p className="text-sm text-muted mt-2">Gecikme: {testResult.latency_ms}ms</p>
            </div>
          )}

          {testResult && !testResult.success && (
            <div className="mt-4 p-4 bg-error/10 border border-error/50 rounded-lg">
              <p className="text-sm text-error">{testResult.error_reason}</p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="sticky bottom-0 bg-surface1 border-t border-border p-6 flex gap-3">
          <button
            onClick={handleSave}
            disabled={saving || !formData.name}
            className="flex-1 px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {saving ? t('loading') + '...' : t('save')}
          </button>
          <button
            onClick={onClose}
            className="px-6 py-3 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors"
          >
            {t('cancel')}
          </button>
        </div>
      </div>
    </div>
  )
}
