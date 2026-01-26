import { useEffect, useState } from 'react'
import { THEMES, ThemeName, DEFAULT_THEME } from '../themes/themes'

export function useTheme() {
  const [currentTheme] = useState<ThemeName>(DEFAULT_THEME)

  useEffect(() => {
    const theme = THEMES[currentTheme]
    const root = document.documentElement

    // Apply theme colors as CSS variables
    Object.entries(theme.colors).forEach(([key, value]) => {
      root.style.setProperty(`--color-${key}`, value)
    })

  }, [currentTheme])

  const changeTheme = (_themeName: ThemeName) => {}

  return {
    currentTheme,
    changeTheme,
    theme: THEMES[currentTheme],
  }
}
