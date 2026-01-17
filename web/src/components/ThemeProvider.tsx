import { h, createContext, ComponentChildren } from 'preact';
import { useState, useEffect, useContext } from 'preact/hooks';

/**
 * ThemeProvider component for managing dark/light mode across the application.
 *
 * Features:
 * - Context-based theme state management
 * - Persists theme preference to localStorage
 * - Detects and respects system dark mode preference
 * - Applies theme via Tailwind CSS 'dark' class on document root
 * - Provides useTheme hook for accessing theme state and toggle function
 *
 * Usage:
 * ```tsx
 * // Wrap your app with ThemeProvider
 * <ThemeProvider>
 *   <App />
 * </ThemeProvider>
 *
 * // Use the hook in any component
 * function MyComponent() {
 *   const { theme, isDark, toggleTheme } = useTheme();
 *   return <button onClick={toggleTheme}>Toggle</button>;
 * }
 * ```
 */

/** Theme mode type */
export type Theme = 'light' | 'dark';

/** Theme context value interface */
interface ThemeContextValue {
  /** Current theme ('light' or 'dark') */
  theme: Theme;
  /** Convenience boolean for checking if dark mode is active */
  isDark: boolean;
  /** Function to toggle between light and dark modes */
  toggleTheme: () => void;
  /** Function to set a specific theme */
  setTheme: (theme: Theme) => void;
}

/** Theme context - provides theme state to all children */
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

/** ThemeProvider props */
interface ThemeProviderProps {
  /** Child components that will have access to theme context */
  children: ComponentChildren;
  /** Optional default theme (defaults to system preference or 'light') */
  defaultTheme?: Theme;
}

/**
 * ThemeProvider component that manages theme state and provides it via context.
 *
 * Initialization order:
 * 1. Check localStorage for saved theme preference
 * 2. Fall back to system preference (prefers-color-scheme)
 * 3. Fall back to defaultTheme prop or 'light'
 *
 * The theme is applied by adding/removing the 'dark' class on document.documentElement,
 * which activates Tailwind's dark: variant classes.
 */
export function ThemeProvider({ children, defaultTheme = 'light' }: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Initialize theme from localStorage or system preference
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('theme') as Theme | null;
      if (savedTheme === 'light' || savedTheme === 'dark') {
        return savedTheme;
      }

      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      return prefersDark ? 'dark' : defaultTheme;
    }
    return defaultTheme;
  });

  // Apply theme to document root whenever it changes
  useEffect(() => {
    const root = document.documentElement;

    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    // Persist to localStorage
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      // Only update if user hasn't explicitly set a preference
      const savedTheme = localStorage.getItem('theme');
      if (!savedTheme) {
        setThemeState(e.matches ? 'dark' : 'light');
      }
    };

    // Modern browsers support addEventListener on MediaQueryList
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } else {
      // Fallback for older browsers
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, []);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  const value: ThemeContextValue = {
    theme,
    isDark: theme === 'dark',
    toggleTheme,
    setTheme,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Custom hook to access theme context.
 *
 * Must be used within a ThemeProvider.
 *
 * @returns Theme context value with current theme, isDark flag, and toggle/set functions
 * @throws Error if used outside ThemeProvider
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { theme, isDark, toggleTheme } = useTheme();
 *
 *   return (
 *     <button onClick={toggleTheme}>
 *       Current theme: {theme}
 *     </button>
 *   );
 * }
 * ```
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);

  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }

  return context;
}
