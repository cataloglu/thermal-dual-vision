import { h, ComponentChildren } from 'preact';
import { useState } from 'preact/hooks';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

/**
 * Main layout component that wraps the entire application.
 *
 * Provides the structural layout including:
 * - Responsive sidebar navigation
 * - Top header with menu toggle button
 * - Main content area
 *
 * The sidebar is:
 * - Always visible on desktop (lg breakpoint and above)
 * - Toggleable on mobile/tablet
 * - Closes automatically when navigating on mobile
 */

interface LayoutProps {
  /** Child components to render in the main content area */
  children: ComponentChildren;
}

export function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  return (
      <div class="min-h-screen bg-[#0B0E14] text-gray-200">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={closeSidebar} />

      {/* Main content wrapper */}
      <div class="lg:pl-64">
        {/* Top header */}
        <header class="h-14 bg-[#0F141D] border-b border-[#1F2937]">
          <div class="flex items-center justify-between h-full px-4">
            {/* Menu toggle button (mobile only) */}
            <button
              onClick={toggleSidebar}
              class="lg:hidden p-2 rounded-md hover:bg-[#1F2937]"
              aria-label="Toggle sidebar"
            >
              <span class="text-xl text-gray-200">☰</span>
            </button>

            {/* Spacer for desktop */}
            <div class="hidden lg:block" />

            {/* Right side - header with theme toggle */}
            <Header />
          </div>
        </header>

        {/* Main content area */}
        <main class="p-4 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
