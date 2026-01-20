import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Live } from './pages/Live'
import { Events } from './pages/Events'
import { Settings } from './pages/Settings'
import { Diagnostics } from './pages/Diagnostics'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/live" element={<Live />} />
          <Route path="/events" element={<Events />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/diagnostics" element={<Diagnostics />} />
        </Routes>
      </Layout>
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
    </BrowserRouter>
  )
}

export default App
