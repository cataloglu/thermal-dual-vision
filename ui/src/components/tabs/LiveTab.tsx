/**
 * Live tab - Live View sabit ayarlarla çalışır; ayar alanı yok (karışıklığı önlemek için).
 */
import React from 'react'
import { useTranslation } from 'react-i18next'
import type { LiveConfig } from '../../types/api'

interface LiveTabProps {
  config: LiveConfig
  onChange: (config: LiveConfig) => void
  onSave: () => void
}

export const LiveTab: React.FC<LiveTabProps> = () => {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('liveViewSettings')}</h3>
        <p className="text-sm text-muted">
          {t('liveViewFixedDesc')}
        </p>
      </div>
    </div>
  )
}
