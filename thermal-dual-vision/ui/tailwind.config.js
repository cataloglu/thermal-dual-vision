/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-background, #0F172A)',
        surface1: 'var(--color-surface1, #1E293B)',
        surface2: 'var(--color-surface2, #334155)',
        border: 'var(--color-border, #475569)',
        text: 'var(--color-text, #F1F5F9)',
        muted: 'var(--color-muted, #94A3B8)',
        accent: 'var(--color-accent, #10B981)',
        success: 'var(--color-success, #10B981)',
        warning: 'var(--color-warning, #F59E0B)',
        error: 'var(--color-error, #EF4444)',
        info: 'var(--color-info, #3B82F6)',
      },
    },
  },
  plugins: [],
}
