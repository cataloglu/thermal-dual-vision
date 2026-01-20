import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  // StrictMode disabled to prevent WebSocket double-mount in development
  // Re-enable for production builds
  <App />
)
