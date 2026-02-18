/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-background, #000000)',
        surface1: 'var(--color-surface1, #1A1A1A)',
        surface2: 'var(--color-surface2, #2A2A2A)',
        surface3: 'var(--color-surface3, #3A3A3A)',
        border: 'var(--color-border, #3A3A3A)',
        text: 'var(--color-text, #FFFFFF)',
        muted: 'var(--color-muted, #888888)',
        accent: 'var(--color-accent, #FF6B6B)',
        card: 'var(--color-surface1, #1A1A1A)',
        foreground: 'var(--color-text, #FFFFFF)',
        'muted-foreground': 'var(--color-muted, #888888)',
        primary: 'var(--color-accent, #FF6B6B)',
        success: 'var(--color-success, #51CF66)',
        warning: 'var(--color-warning, #FFD93D)',
        error: 'var(--color-error, #FF6B6B)',
        info: 'var(--color-info, #4DABF7)',
      },
    },
  },
  plugins: [],
}
