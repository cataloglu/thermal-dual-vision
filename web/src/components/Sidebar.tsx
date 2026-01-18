import { h } from 'preact';
import { Link } from 'preact-router/match';

/**
 * Sidebar navigation component.
 *
 * Security-focused navigation with only the required sections.
 */

interface SidebarProps {
  /** Whether the sidebar is open (for mobile) */
  isOpen: boolean;
  /** Callback to close the sidebar */
  onClose: () => void;
}

interface NavItem {
  path: string;
  label: string;
  hint?: string;
}

const navItems: NavItem[] = [
  { path: '/status', label: 'Status', hint: 'Pipeline & AI' },
  { path: '/', label: 'Events', hint: 'Primary feed' },
  { path: '/cameras', label: 'Cameras', hint: 'Connectivity' },
  { path: '/settings', label: 'Settings', hint: 'Config' },
  { path: '/diagnostics', label: 'Diagnostics', hint: 'Health & logs' },
];

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          class="fixed inset-0 bg-black bg-opacity-50 z-20 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        class={`
          fixed top-0 left-0 z-30 h-full w-64
          bg-[#111827] border-r border-[#1F2937]
          transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Sidebar header */}
        <div class="flex items-center justify-between h-16 px-6 border-b border-[#1F2937]">
          <h1 class="text-base font-semibold text-gray-100 tracking-wide">
            Smart Motion
          </h1>
          {/* Close button (mobile only) */}
          <button
            onClick={onClose}
            class="lg:hidden p-2 rounded-md hover:bg-[#1F2937]"
            aria-label="Close sidebar"
          >
            <span class="text-xl text-gray-200">✕</span>
          </button>
        </div>

        {/* Navigation */}
        <nav class="p-4">
          <ul class="space-y-2">
            {navItems.map((item) => (
              <li key={item.path}>
                <Link
                  href={item.path}
                  activeClassName="bg-[#161B22] text-gray-100 border border-[#1F2937]"
                  class="
                    flex flex-col gap-1 px-4 py-3 rounded-lg
                    text-gray-300 border border-transparent
                    hover:bg-[#161B22] hover:text-gray-100
                    transition-colors duration-150
                  "
                  onClick={onClose}
                >
                  <span class="text-sm font-semibold tracking-wide">{item.label}</span>
                  {item.hint && (
                    <span class="text-xs text-gray-500">{item.hint}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* Footer */}
        <div class="absolute bottom-0 left-0 right-0 p-4 border-t border-[#1F2937]">
          <div class="text-xs text-gray-500 text-center">
            Monitoring Console
          </div>
        </div>
      </aside>
    </>
  );
}
