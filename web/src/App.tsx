import { h } from 'preact';
import Router from 'preact-router';
import { Layout } from './components/Layout';
import { ThemeProvider } from './components/ThemeProvider';
import { Dashboard } from './pages/Dashboard';

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
 * Live View page - MJPEG camera stream
 */
function LiveView() {
  return (
    <div>
      <h1 class="text-3xl font-bold mb-4">Live View</h1>
      <p class="text-gray-600 dark:text-gray-400">
        Live camera stream
      </p>
    </div>
  );
}

/**
 * Gallery page - Grid view of saved screenshots
 */
function Gallery() {
  return (
    <div>
      <h1 class="text-3xl font-bold mb-4">Gallery</h1>
      <p class="text-gray-600 dark:text-gray-400">
        Screenshot gallery
      </p>
    </div>
  );
}

/**
 * Events page - Detection history table
 */
function Events() {
  return (
    <div>
      <h1 class="text-3xl font-bold mb-4">Events</h1>
      <p class="text-gray-600 dark:text-gray-400">
        Motion detection event history
      </p>
    </div>
  );
}

/**
 * Settings page - Configuration form
 */
function Settings() {
  return (
    <div>
      <h1 class="text-3xl font-bold mb-4">Settings</h1>
      <p class="text-gray-600 dark:text-gray-400">
        System configuration
      </p>
    </div>
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
