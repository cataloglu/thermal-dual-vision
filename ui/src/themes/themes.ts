/**
 * Theme definitions for Smart Motion Detector v2
 */

export interface Theme {
  name: string
  label: string
  description: string
  colors: {
    background: string
    surface1: string
    surface2: string
    border: string
    text: string
    muted: string
    accent: string
    success: string
    warning: string
    error: string
    info: string
  }
}

export const SLATE_THEME: Theme = {
  name: 'slate',
  label: 'Slate Professional',
  description: 'Modern, profesyonel, yeşil accent (önerilen)',
  colors: {
    background: '#0F172A',
    surface1: '#1E293B',
    surface2: '#334155',
    border: '#475569',
    text: '#F1F5F9',
    muted: '#94A3B8',
    accent: '#10B981',  // Yeşil!
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',
  }
}

export const CARBON_THEME: Theme = {
  name: 'carbon',
  label: 'Carbon Dark',
  description: 'Minimal, developer tools, turkuaz accent',
  colors: {
    background: '#18181B',
    surface1: '#27272A',
    surface2: '#3F3F46',
    border: '#52525B',
    text: '#FAFAFA',
    muted: '#A1A1AA',
    accent: '#22D3EE',  // Turkuaz!
    success: '#34D399',
    warning: '#FBBF24',
    error: '#F87171',
    info: '#60A5FA',
  }
}

export const PURE_BLACK_THEME: Theme = {
  name: 'pure-black',
  label: 'Pure Black',
  description: 'OLED friendly, minimal, kırmızı accent',
  colors: {
    background: '#000000',
    surface1: '#1A1A1A',
    surface2: '#2A2A2A',
    border: '#3A3A3A',
    text: '#FFFFFF',
    muted: '#888888',
    accent: '#FF6B6B',  // Kırmızı-pembe!
    success: '#51CF66',
    warning: '#FFD93D',
    error: '#FF6B6B',
    info: '#4DABF7',
  }
}

export const MATRIX_THEME: Theme = {
  name: 'matrix',
  label: 'Matrix Hacker',
  description: 'Cyberpunk, neon yeşil, gösterişli',
  colors: {
    background: '#000000',
    surface1: '#0A0E0A',
    surface2: '#1A1E1A',
    border: '#00FF00',
    text: '#00FF00',
    muted: '#00AA00',
    accent: '#00FF00',  // Neon yeşil!
    success: '#00FF00',
    warning: '#FFFF00',
    error: '#FF0000',
    info: '#00FFFF',
  }
}

export const THEMES = {
  slate: SLATE_THEME,
  carbon: CARBON_THEME,
  'pure-black': PURE_BLACK_THEME,
  matrix: MATRIX_THEME,
}

export type ThemeName = keyof typeof THEMES

export const DEFAULT_THEME: ThemeName = 'slate'
