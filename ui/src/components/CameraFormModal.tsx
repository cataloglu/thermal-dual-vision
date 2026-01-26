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
        // Fix: Use default values to prevent undefined type errors
        channel_color: camera.channel_color ?? 102,
        channel_thermal: camera.channel_thermal ?? 202,
        detection_source: camera.detection_source,
        stream_roles: camera.stream_roles?.filter((role) => role !== 'record')?.length
          ? camera.stream_roles.filter((role) => role !== 'record')
          : ['detect', 'live'],
      })
    }
  }, [camera])

  const handleTest = async () => {
    const validationErrors = validate()
    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      toast.error(t('cameraTestFillRequired'))
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
        toast.success(t('cameraTestSuccess', { latency: response.latency_ms }))
      } else {
        toast.error(response.error_reason || t('cameraTestFailed'))
      }
    } catch (error) {
      toast.error(t('cameraTestConnectionFailed'))
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    const validationErrors = validate()
    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      toast.error(t('cameraFormInvalid'))
      return
    }

    setSaving(true)

    try {
      const payload = {
        ...formData,
        stream_roles: ['detect', 'live'],
        channel_color: undefined,
        channel_thermal: undefined,
      }
      if (camera) {
        await api.updateCamera(camera.id as string, payload)
      } else {
        await api.createCamera(payload)
      }

      toast.success(camera ? t('cameraUpdated') : t('cameraAdded'))
      onSave()
      onClose()
    } catch (error) {
      console.error('Failed to save camera:', error)
      toast.error(t('cameraSaveFailed'))
    } finally {
      setSaving(false)
    }
  }

  const validate = () => {
    const nextErrors: string[] = []
    if (!formData.name.trim()) {
      nextErrors.push(t('cameraNameRequired'))
    }
    const isRtsp = (value: string) => value.trim().startsWith('rtsp://')
    if (formData.type === 'thermal' || formData.type === 'dual') {
      if (!formData.rtsp_url_thermal.trim()) {
        nextErrors.push(t('thermalRtspRequired'))
      } else if (!isRtsp(formData.rtsp_url_thermal)) {
        nextErrors.push(t('thermalRtspInvalid'))
      }
    }
    if (formData.type === 'color' || formData.type === 'dual') {
      if (!formData.rtsp_url_color.trim()) {
        nextErrors.push(t('colorRtspRequired'))
      } else if (!isRtsp(formData.rtsp_url_color)) {
        nextErrors.push(t('colorRtspInvalid'))
      }
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
              {t('cameraNameLabel')} *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder={t('cameraNamePlaceholder')}
              className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>

          {/* Type */}
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              {t('cameraTypeLabel')} *
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="thermal">{t('cameraTypeThermal')}</option>
              <option value="color">{t('cameraTypeColor')}</option>
              <option value="dual">{t('cameraTypeDual')}</option>
            </select>
          </div>

          {/* Thermal URL */}
          {(formData.type === 'thermal' || formData.type === 'dual') && (
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('thermalRtspLabel')} *
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
                {t('colorRtspLabel')} *
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

          {/* Detection Source */}
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              {t('detectionSourceLabel')}
            </label>
            <select
              value={formData.detection_source}
              onChange={(e) => setFormData({ ...formData, detection_source: e.target.value })}
              className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="auto">{t('detectionSourceAuto')}</option>
              <option value="thermal">{t('cameraTypeThermal')}</option>
              <option value="color">{t('cameraTypeColor')}</option>
            </select>
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
              <span className="text-sm text-text">{t('cameraEnableLabel')}</span>
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
              {testing ? t('cameraTestRunning') : t('cameraTestButton')}
            </button>
          </div>

          {/* Test Result */}
          {testResult && testResult.success && testResult.snapshot_base64 && (
            <div className="pt-4">
              <h4 className="text-sm font-medium text-text mb-2">{t('cameraTestPreview')}</h4>
              <div className="border border-border rounded-lg overflow-hidden">
                <img src={testResult.snapshot_base64} alt={t('cameraTestImageAlt')} className="w-full h-auto" />
              </div>
              <p className="text-sm text-muted mt-2">{t('cameraTestLatency', { latency: testResult.latency_ms })}</p>
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
