import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  // StrictMode intentionally disabled: double-invocation in dev causes WebSocket
  // connection to be established twice, flooding the backend with connections.
  <App />
)
