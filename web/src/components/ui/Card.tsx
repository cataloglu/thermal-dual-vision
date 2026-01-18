import { h, ComponentChildren } from 'preact';

/**
 * Card component - A container component for content sections.
 *
 * Provides a consistent card-based layout with:
 * - Background color (light/dark mode support)
 * - Rounded corners and shadow
 * - Optional padding customization
 * - Optional title and actions
 *
 * Styled using Tailwind CSS with dark mode support.
 */

interface CardProps {
  /** Card title displayed at the top */
  title?: string;
  /** Child components to render in the card body */
  children: ComponentChildren;
  /** Additional CSS classes to apply */
  className?: string;
  /** Optional action buttons or elements in the card header */
  actions?: ComponentChildren;
  /** Custom padding (defaults to 'p-4') */
  padding?: string;
}

export function Card({
  title,
  children,
  className = '',
  actions,
  padding = 'p-4'
}: CardProps) {
  return (
    <div class={`card ${className}`}>
      {/* Card header with title and actions */}
      {(title || actions) && (
        <div class={`
          flex items-center justify-between
          px-4 py-3
          border-b border-[#1F2937]
        `}>
          {title && (
            <h3 class="text-sm font-semibold text-gray-200 tracking-wide">
              {title}
            </h3>
          )}
          {actions && (
            <div class="flex items-center gap-2">
              {actions}
            </div>
          )}
        </div>
      )}

      {/* Card body */}
      <div class={padding}>
        {children}
      </div>
    </div>
  );
}
