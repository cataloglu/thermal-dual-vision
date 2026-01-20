import { useState, useEffect } from 'react'

function App() {
  const [health, setHealth] = useState<any>(null)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(err => console.error(err))
  }, [])

  return (
    <div className="min-h-screen bg-background text-text p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-4 text-accent">
          Smart Motion Detector v2
        </h1>
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">System Health</h2>
          {health ? (
            <pre className="text-sm text-muted">
              {JSON.stringify(health, null, 2)}
            </pre>
          ) : (
            <p className="text-muted">Loading...</p>
          )}
        </div>
        <div className="mt-6 text-muted text-sm">
          <p>🎯 Person detection only</p>
          <p>🌡️ Thermal + Color camera support</p>
          <p>📹 Event-based recording (collage/gif/mp4)</p>
        </div>
      </div>
    </div>
  )
}

export default App
