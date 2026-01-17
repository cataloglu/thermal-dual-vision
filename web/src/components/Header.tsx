import { h } from 'preact';
import { useTheme } from './ThemeProvider';

/**
 * Header component for the top navigation bar.
 *
 * Displays:
 * - Application title
 * - Theme toggle button (dark/light mode)
 *
 * The theme toggle uses the ThemeProvider context to switch between
 * light and dark modes. Theme state is managed centrally and persisted
 * to localStorage via the ThemeProvider.
 */

interface HeaderProps {
  /** Optional title to display (defaults to "Motion Detector") */
  title?: string;
}

export function Header({ title = 'Motion Detector' }: HeaderProps) {
  const { isDark, toggleTheme } = useTheme();

  return (
    <div class="flex items-center gap-4">
      {/* App title */}
      <h2 class="hidden sm:block text-lg font-semibold text-gray-900 dark:text-gray-100">
        {title}
      </h2>

      {/* Theme toggle button */}
      <button
        onClick={toggleTheme}
        class="
          p-2 rounded-lg
          bg-gray-100 dark:bg-gray-700
          hover:bg-gray-200 dark:hover:bg-gray-600
          transition-colors duration-200
        "
        aria-label="Toggle theme"
        title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        <span class="text-xl">
          {isDark ? '☀️' : '🌙'}
        </span>
      </button>
    </div>
  );
}
