import { HashRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Layout } from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Dashboard } from './pages/Dashboard'
import { Live } from './pages/Live'
import { Events } from './pages/Events'
import { Settings } from './pages/Settings'
import { Diagnostics } from './pages/Diagnostics'
import { useTheme } from './hooks/useTheme'
import './i18n'

function App() {
  // Apply theme
  useTheme()

  return (
    <HashRouter>
      <ErrorBoundary>
        <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/live" element={<Live />} />
          <Route path="/events" element={<Events />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/diagnostics" element={<Diagnostics />} />
        </Routes>
        </Layout>
      </ErrorBoundary>
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#111A2E',
            color: '#E6EAF2',
            border: '1px solid #22304A',
          },
        }}
      />
    </HashRouter>
  )
}

export default App
