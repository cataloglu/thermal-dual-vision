/**
 * Appearance tab - Language settings (theme locked)
 */
import React from 'react'
import { useTranslation } from 'react-i18next'
import type { AppearanceConfig } from '../../types/api'

interface AppearanceTabProps {
  config: AppearanceConfig
  onChange: (config: AppearanceConfig) => void
  onSave: (updates?: { appearance: AppearanceConfig }) => void
}

export const AppearanceTab: React.FC<AppearanceTabProps> = ({ config, onChange, onSave }) => {
  const { t, i18n } = useTranslation()
  const lang = (config.language || i18n.language || 'tr') as 'tr' | 'en'

  const handleLanguageChange = (next: 'tr' | 'en') => {
    localStorage.setItem('language', next)
    i18n.changeLanguage(next)
    const nextAppearance = { ...config, language: next }
    onChange(nextAppearance)
    onSave({ appearance: nextAppearance })
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('languageSettingsTitle')}</h3>
        <p className="text-sm text-muted mb-6">{t('languageSettingsDesc')}</p>
      </div>

      {/* Language Selection */}
      <div>
        <label className="block text-sm font-medium text-text mb-2">{t('languageLabel')}</label>
        <select
          value={lang}
          onChange={(e) => handleLanguageChange(e.target.value as 'tr' | 'en')}
          className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <option value="tr">{t('languageTurkish')}</option>
          <option value="en">{t('languageEnglish')}</option>
        </select>
        <p className="text-xs text-muted mt-1">{t('languageHelp')}</p>
      </div>

      {/* Info */}
      <div className="bg-surface2 border-l-4 border-info p-4 rounded-lg">
        <p className="text-sm text-text">
          <strong>💡 {t('tipLabel')}:</strong> {t('themeLockedTip')}
        </p>
      </div>
    </div>
  )
}
