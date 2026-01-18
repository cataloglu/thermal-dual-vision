import { h } from 'preact';
import Router from 'preact-router';
import { Layout } from './components/Layout';
import { ThemeProvider } from './components/ThemeProvider';
import { Dashboard } from './pages/Dashboard';
import { Cameras } from './pages/Cameras';
import { Diagnostics } from './pages/Diagnostics';
import { Events } from './pages/Events';
import { Settings } from './pages/Settings';

/**
 * Root application component with routing.
 *
 * This component sets up the application routing using preact-router.
 * The entire app is wrapped in:
 * - ThemeProvider: Forces dark-only mode
 * - Layout: Provides navigation sidebar and header structure
 *
 * Routes:
 * - / : Status overview
 * - /events : Event history and detail
 * - /cameras : Camera health and setup
 * - /settings : Configuration tabs
 * - /diagnostics : Health/metrics/logs
 */
export function App() {
  return (
    <ThemeProvider>
      <Layout>
        <Router>
          <Dashboard path="/" />
          <Events path="/events" />
          <Cameras path="/cameras" />
          <Settings path="/settings" />
          <Diagnostics path="/diagnostics" />
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
    <div class="space-y-2">
      <h1 class="text-lg font-semibold text-gray-200">404</h1>
      <p class="text-sm text-muted">Requested page not found.</p>
      <a href="/" class="text-sm text-[#38BDF8]">
        Return to Status
      </a>
    </div>
  );
}
