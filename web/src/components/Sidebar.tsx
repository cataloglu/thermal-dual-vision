import { h } from 'preact';
import { Link } from 'preact-router/match';

/**
 * Sidebar navigation component.
 *
 * Provides main navigation links for the application. The sidebar is responsive
 * and can be toggled on mobile devices. Active routes are highlighted.
 *
 * Navigation items:
 * - Dashboard: System overview and recent detections
 * - Live View: Real-time camera stream
 * - Gallery: Screenshot grid view
 * - Events: Detection history table
 * - Settings: Configuration form
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
  icon: string;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/cameras', label: 'Cameras', icon: '🎥' },
  { path: '/live', label: 'Live View', icon: '📹' },
  { path: '/gallery', label: 'Gallery', icon: '🖼️' },
  { path: '/events', label: 'Events', icon: '📋' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
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
          bg-white dark:bg-gray-800
          border-r border-gray-200 dark:border-gray-700
          transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Sidebar header */}
        <div class="flex items-center justify-between h-16 px-6 border-b border-gray-200 dark:border-gray-700">
          <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100">
            Motion Detector
          </h1>
          {/* Close button (mobile only) */}
          <button
            onClick={onClose}
            class="lg:hidden p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Close sidebar"
          >
            <span class="text-2xl">✕</span>
          </button>
        </div>

        {/* Navigation */}
        <nav class="p-4">
          <ul class="space-y-2">
            {navItems.map((item) => (
              <li key={item.path}>
                <Link
                  href={item.path}
                  activeClassName="bg-primary-600 text-white"
                  class="
                    flex items-center gap-3 px-4 py-3 rounded-lg
                    text-gray-700 dark:text-gray-300
                    hover:bg-gray-100 dark:hover:bg-gray-700
                    transition-colors duration-200
                  "
                  onClick={onClose}
                >
                  <span class="text-xl">{item.icon}</span>
                  <span class="font-medium">{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* Footer */}
        <div class="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700">
          <div class="text-xs text-gray-500 dark:text-gray-400 text-center">
            Motion Detector v1.0
          </div>
        </div>
      </aside>
    </>
  );
}
