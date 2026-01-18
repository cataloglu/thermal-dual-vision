import { h } from 'preact';

/**
 * Header component for the top navigation bar.
 *
 * Displays:
 * - Application title
 */

interface HeaderProps {
  /** Optional title to display (defaults to "Motion Detector") */
  title?: string;
}

export function Header({ title = 'Smart Motion' }: HeaderProps) {
  return (
    <div class="flex items-center gap-3">
      <h2 class="text-sm font-semibold text-gray-200 tracking-wide">
        {title}
      </h2>
    </div>
  );
}
