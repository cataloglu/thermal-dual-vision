import { h, ComponentChildren } from 'preact';

/**
 * Button component - A reusable button with multiple variants.
 *
 * Supports:
 * - Multiple variants: primary, secondary, danger
 * - Multiple sizes: sm, md, lg
 * - Disabled state
 * - Loading state
 * - Full width option
 * - Icon support
 *
 * Styled using Tailwind CSS with dark mode support.
 */

interface ButtonProps {
  /** Button variant determines color scheme */
  variant?: 'primary' | 'secondary' | 'danger';
  /** Button size */
  size?: 'sm' | 'md' | 'lg';
  /** Whether button is disabled */
  disabled?: boolean;
  /** Whether button shows loading state */
  loading?: boolean;
  /** Whether button takes full width */
  fullWidth?: boolean;
  /** Button type attribute */
  type?: 'button' | 'submit' | 'reset';
  /** Click handler */
  onClick?: (e: MouseEvent) => void;
  /** Child components to render inside button */
  children: ComponentChildren;
  /** Additional CSS classes to apply */
  className?: string;
  /** Optional icon element to display before text */
  icon?: ComponentChildren;
}

export function Button({
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  fullWidth = false,
  type = 'button',
  onClick,
  children,
  className = '',
  icon
}: ButtonProps) {
  // Base button classes
  const baseClasses = `
    inline-flex items-center justify-center gap-2
    font-medium rounded-md
    transition-colors duration-150
    focus:outline-none focus:ring-2 focus:ring-offset-0
    disabled:opacity-50 disabled:cursor-not-allowed
  `;

  // Size classes
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  };

  // Variant classes
  const variantClasses = {
    primary: `
      bg-[#111827] hover:bg-[#161B22] text-gray-200
      border border-[#1F2937]
      focus:ring-[#1F2937]
    `,
    secondary: `
      bg-transparent hover:bg-[#161B22] text-gray-400
      border border-[#1F2937]
      focus:ring-[#1F2937]
    `,
    danger: `
      bg-[#111827] hover:bg-[#161B22] text-[#EF4444]
      border border-[#1F2937]
      focus:ring-[#EF4444]
    `
  };

  // Width class
  const widthClass = fullWidth ? 'w-full' : '';

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      class={`
        ${baseClasses}
        ${sizeClasses[size]}
        ${variantClasses[variant]}
        ${widthClass}
        ${className}
      `}
    >
      {/* Loading spinner */}
      {loading && (
        <span class="animate-spin">⟳</span>
      )}

      {/* Optional icon */}
      {!loading && icon && (
        <span>{icon}</span>
      )}

      {/* Button content */}
      <span>{children}</span>
    </button>
  );
}
