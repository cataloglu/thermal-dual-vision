import { useEffect, useState } from 'react'
import { THEMES, ThemeName, DEFAULT_THEME } from '../themes/themes'

const THEME_STORAGE_KEY = 'motion-detector-theme'

export function useTheme() {
  const [currentTheme, setCurrentTheme] = useState<ThemeName>(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    return (saved as ThemeName) || DEFAULT_THEME
  })

  useEffect(() => {
    const theme = THEMES[currentTheme]
    const root = document.documentElement

    // Apply theme colors as CSS variables
    Object.entries(theme.colors).forEach(([key, value]) => {
      root.style.setProperty(`--color-${key}`, value)
    })

    // Save to localStorage
    localStorage.setItem(THEME_STORAGE_KEY, currentTheme)
  }, [currentTheme])

  const changeTheme = (themeName: ThemeName) => {
    setCurrentTheme(themeName)
  }

  return {
    currentTheme,
    changeTheme,
    theme: THEMES[currentTheme],
  }
}
