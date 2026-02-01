import { useEffect } from 'react'
import { PURE_BLACK_THEME } from '../themes/themes'

/**
 * Apply Pure Black theme (single theme, optimized)
 */
export function useTheme() {
  useEffect(() => {
    const root = document.documentElement

    // Apply Pure Black theme colors as CSS variables
    Object.entries(PURE_BLACK_THEME.colors).forEach(([key, value]) => {
      root.style.setProperty(`--color-${key}`, value)
    })
  }, [])

  return {
    theme: PURE_BLACK_THEME,
  }
}
