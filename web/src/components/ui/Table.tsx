import { h, ComponentChildren } from 'preact';

/**
 * Table component - A flexible table component for displaying tabular data.
 *
 * Provides:
 * - Responsive table layout
 * - Dark mode support
 * - Optional striped rows
 * - Optional hover effects
 * - Custom column definitions
 * - Empty state handling
 *
 * Styled using Tailwind CSS with dark mode support.
 */

export interface TableColumn<T = any> {
  /** Unique key for the column */
  key: string;
  /** Column header label */
  label: string;
  /** Custom render function for cell content */
  render?: (item: T) => ComponentChildren;
  /** CSS classes for the column */
  className?: string;
  /** Column width (e.g., 'w-32', 'w-1/4') */
  width?: string;
}

interface TableProps<T = any> {
  /** Column definitions */
  columns: TableColumn<T>[];
  /** Data array to display */
  data: T[];
  /** Custom key extractor (defaults to using 'id' field) */
  keyExtractor?: (item: T, index: number) => string | number;
  /** Whether to show striped rows */
  striped?: boolean;
  /** Whether to show hover effect on rows */
  hover?: boolean;
  /** Message to display when data is empty */
  emptyMessage?: string;
  /** Additional CSS classes for the table */
  className?: string;
  /** Whether the table is loading */
  loading?: boolean;
  /** Optional row click handler */
  onRowClick?: (item: T) => void;
}

export function Table<T = any>({
  columns,
  data,
  keyExtractor = (item: any, index: number) => item?.id ?? index,
  striped = true,
  hover = true,
  emptyMessage = 'No data available',
  className = '',
  loading = false,
  onRowClick
}: TableProps<T>) {
  return (
    <div class={`overflow-x-auto ${className}`}>
      <table class="w-full border-collapse">
        {/* Table header */}
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                class={`
                  px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide
                  bg-[#111827]
                  border-b border-[#1F2937]
                  text-gray-400
                  ${column.width || ''}
                  ${column.className || ''}
                `}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>

        {/* Table body */}
        <tbody>
          {/* Loading state */}
          {loading && (
            <tr>
              <td
                colSpan={columns.length}
                class="px-4 py-8 text-center text-gray-500"
              >
                <div class="flex items-center justify-center gap-2">
                  <span class="animate-spin text-2xl">⟳</span>
                  <span>Loading...</span>
                </div>
              </td>
            </tr>
          )}

          {/* Empty state */}
          {!loading && data.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                class="px-4 py-8 text-center text-gray-500"
              >
                {emptyMessage}
              </td>
            </tr>
          )}

          {/* Data rows */}
          {!loading && data.map((item, index) => {
            const key = keyExtractor(item, index);
            const rowClasses = `
              border-b border-[#1F2937]
              ${striped && index % 2 === 0 ? 'bg-[#0F141D]' : ''}
              ${hover ? 'hover:bg-[#161B22] transition-colors' : ''}
              ${onRowClick ? 'cursor-pointer' : ''}
            `;

            return (
              <tr
                key={key}
                class={rowClasses}
                onClick={onRowClick ? () => onRowClick(item) : undefined}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    class={`
                      px-4 py-3 text-sm text-gray-200
                      ${column.className || ''}
                    `}
                  >
                    {column.render
                      ? column.render(item)
                      : (item as any)[column.key]
                    }
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
