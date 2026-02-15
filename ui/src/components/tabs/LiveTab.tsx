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

      <p className="text-sm text-muted">
        {t('liveMjpegOnly') || 'Live View kamera akışlarını backend MJPEG ile gösterir.'}
      </p>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveLiveSettings')}
      </button>
    </div>
  )
}
