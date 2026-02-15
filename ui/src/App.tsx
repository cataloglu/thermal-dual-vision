import { HashRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { lazy, Suspense } from 'react'
import { Layout } from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { LoadingState } from './components/LoadingState'
import { useTheme } from './hooks/useTheme'
import './i18n'

// Lazy load pages for better performance
const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })))
const Live = lazy(() => import('./pages/Live').then(m => ({ default: m.Live })))
const Events = lazy(() => import('./pages/Events').then(m => ({ default: m.Events })))
const Settings = lazy(() => import('./pages/Settings').then(m => ({ default: m.Settings })))
const Diagnostics = lazy(() => import('./pages/Diagnostics').then(m => ({ default: m.Diagnostics })))
const Logs = lazy(() => import('./pages/Logs').then(m => ({ default: m.Logs })))
const VideoAnalysis = lazy(() => import('./pages/VideoAnalysis').then(m => ({ default: m.VideoAnalysis })))
const MqttMonitoring = lazy(() => import('./pages/MqttMonitoring').then(m => ({ default: m.MqttMonitoring })))

function App() {
  // Apply theme
  useTheme()

  return (
    <HashRouter>
      <ErrorBoundary>
        <Layout>
          <Suspense fallback={<LoadingState />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/live" element={<Live />} />
              <Route path="/events" element={<Events />} />
              <Route path="/diagnostics" element={<Diagnostics />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/video-analysis" element={<VideoAnalysis />} />
              <Route path="/mqtt" element={<MqttMonitoring />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Suspense>
        </Layout>
      </ErrorBoundary>
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#1A1A1A',  // Pure Black surface1
            color: '#FFFFFF',       // Pure Black text
            border: '1px solid #3A3A3A',  // Pure Black border
          },
          success: {
            iconTheme: {
              primary: '#51CF66',  // Pure Black success
              secondary: '#1A1A1A',
            },
          },
          error: {
            iconTheme: {
              primary: '#FF6B6B',  // Pure Black error
              secondary: '#1A1A1A',
            },
          },
        }}
      />
    </HashRouter>
  )
}

export default App
