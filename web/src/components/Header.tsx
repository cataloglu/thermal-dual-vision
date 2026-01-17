import { h } from 'preact';
import { useState, useEffect } from 'preact/hooks';

/**
 * Header component for the top navigation bar.
 *
 * Displays:
 * - Application title
 * - Theme toggle button (dark/light mode)
 *
 * The theme toggle switches between light and dark modes by:
 * - Adding/removing 'dark' class on document root element
 * - Persisting preference to localStorage
 * - Following Tailwind CSS dark mode strategy
 */

interface HeaderProps {
  /** Optional title to display (defaults to "Motion Detector") */
  title?: string;
}

export function Header({ title = 'Motion Detector' }: HeaderProps) {
  const [isDark, setIsDark] = useState(false);

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const shouldBeDark = savedTheme === 'dark' || (!savedTheme && prefersDark);

    setIsDark(shouldBeDark);
    if (shouldBeDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);

  // Toggle theme
  const toggleTheme = () => {
    const newIsDark = !isDark;
    setIsDark(newIsDark);

    if (newIsDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

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
