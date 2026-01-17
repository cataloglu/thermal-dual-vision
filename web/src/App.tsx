import { h } from 'preact';
import Router from 'preact-router';
import { Layout } from './components/Layout';
import { ThemeProvider } from './components/ThemeProvider';
import { Dashboard } from './pages/Dashboard';
import { LiveView } from './pages/LiveView';
import { Gallery } from './pages/Gallery';
import { Events } from './pages/Events';
import { Settings } from './pages/Settings';

/**
 * Root application component with routing.
 *
 * This component sets up the application routing using preact-router.
 * The entire app is wrapped in:
 * - ThemeProvider: Provides dark/light mode context to all components
 * - Layout: Provides navigation sidebar and header structure
 *
 * Routes:
 * - / : Dashboard (home page with stats and recent detections)
 * - /live : Live camera stream view
 * - /gallery : Screenshot gallery grid
 * - /events : Event history table
 * - /settings : Configuration settings
 */
export function App() {
  return (
    <ThemeProvider>
      <Layout>
        <Router>
          <Dashboard path="/" />
          <LiveView path="/live" />
          <Gallery path="/gallery" />
          <Events path="/events" />
          <Settings path="/settings" />
          <NotFound default />
        </Router>
      </Layout>
    </ThemeProvider>
  );
}

/**
 * 404 Not Found page
 */
function NotFound() {
  return (
    <div>
      <h1 class="text-3xl font-bold mb-4">404 - Page Not Found</h1>
      <p class="text-gray-600 dark:text-gray-400">
        The requested page could not be found.
      </p>
      <a href="/" class="text-primary-600 hover:text-primary-700 mt-4 inline-block">
        Return to Dashboard
      </a>
    </div>
  );
}
