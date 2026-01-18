import { h, ComponentChildren } from 'preact';
import { useEffect } from 'preact/hooks';

/**
 * ThemeProvider enforces dark-only mode for the console UI.
 */
interface ThemeProviderProps {
  children: ComponentChildren;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  useEffect(() => {
    const root = document.documentElement;
    root.classList.add('dark');
  }, []);

  return <>{children}</>;
}
