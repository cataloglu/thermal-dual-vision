/**
 * Live tab - Live stream (MJPEG backend)
 */
import React from 'react'
import { useTranslation } from 'react-i18next'
import type { LiveConfig } from '../../types/api'

interface LiveTabProps {
  config: LiveConfig
  onChange: (config: LiveConfig) => void
  onSave: () => void
}

export const LiveTab: React.FC<LiveTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('liveViewSettings')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('liveViewDesc')}
        </p>
      </div>

      <p className="text-sm text-muted mb-4">
        {t('liveMjpegOnly') || 'Live View kamera akışlarını backend MJPEG ile gösterir.'}
      </p>

      <div>
        <label className="block text-sm text-muted mb-2">{t('mjpegQuality') || 'MJPEG kalitesi'}</label>
        <input
          type="number"
          min={50}
          max={100}
          value={config.mjpeg_quality ?? 92}
          onChange={(e) => onChange({ ...config, mjpeg_quality: parseInt(e.target.value, 10) || 92 })}
          className="w-24 px-3 py-2 bg-surface2 border border-border rounded-lg text-text"
        />
        <p className="text-xs text-muted mt-1">{t('mjpegQualityDesc') || 'Yüksek = daha iyi görüntü, daha fazla bant genişliği (varsayılan: 92)'}</p>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveLiveSettings')}
      </button>
    </div>
  )
}
