/**
 * Appearance tab - Theme and language settings
 */
import React from 'react'
import { useTheme } from '../../hooks/useTheme'
import { THEMES, ThemeName } from '../../themes/themes'
import { MdCheck } from 'react-icons/md'
import toast from 'react-hot-toast'

export const AppearanceTab: React.FC = () => {
  const { currentTheme, changeTheme } = useTheme()

  const handleThemeChange = (themeName: ThemeName) => {
    changeTheme(themeName)
    toast.success(`Tema değiştirildi: ${THEMES[themeName].label}`)
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Görünüm Ayarları</h3>
        <p className="text-sm text-muted mb-6">
          Tema ve dil tercihlerinizi yapılandırın
        </p>
      </div>

      {/* Theme Selection */}
      <div>
        <label className="block text-sm font-medium text-text mb-4">
          Tema Seçimi
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(THEMES).map(([key, theme]) => (
            <button
              key={key}
              onClick={() => handleThemeChange(key as ThemeName)}
              className={`p-4 rounded-lg border-2 transition-all text-left ${
                currentTheme === key
                  ? 'border-accent bg-accent/10'
                  : 'border-border bg-surface1 hover:border-accent/50'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-semibold text-text">{theme.label}</h4>
                {currentTheme === key && (
                  <MdCheck className="text-accent text-xl" />
                )}
              </div>
              <p className="text-sm text-muted mb-3">{theme.description}</p>
              
              {/* Color Preview */}
              <div className="flex gap-2">
                <div 
                  className="w-8 h-8 rounded border border-border"
                  style={{ backgroundColor: theme.colors.background }}
                  title="Background"
                />
                <div 
                  className="w-8 h-8 rounded border border-border"
                  style={{ backgroundColor: theme.colors.surface1 }}
                  title="Surface"
                />
                <div 
                  className="w-8 h-8 rounded border border-border"
                  style={{ backgroundColor: theme.colors.accent }}
                  title="Accent"
                />
                <div 
                  className="w-8 h-8 rounded border border-border"
                  style={{ backgroundColor: theme.colors.success }}
                  title="Success"
                />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Language Selection */}
      <div>
        <label className="block text-sm font-medium text-text mb-2">
          Dil / Language
        </label>
        <select
          defaultValue="tr"
          className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <option value="tr">Türkçe</option>
          <option value="en">English</option>
        </select>
        <p className="text-xs text-muted mt-1">
          Arayüz dili (Interface language)
        </p>
      </div>

      {/* Info */}
      <div className="bg-surface2 border-l-4 border-info p-4 rounded-lg">
        <p className="text-sm text-text">
          <strong>💡 İpucu:</strong> Tema değişiklikleri anında uygulanır. 
          Sayfa yenilemeye gerek yoktur.
        </p>
      </div>
    </div>
  )
}
