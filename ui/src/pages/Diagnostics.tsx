import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { MdContentCopy, MdCheckCircle } from 'react-icons/md'

export function Diagnostics() {
  const [health, setHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await api.getHealth()
        setHealth(data)
      } catch (error) {
        console.error('Failed to fetch health:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchHealth()
  }, [])

  const handleCopy = () => {
    if (health) {
      navigator.clipboard.writeText(JSON.stringify(health, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-surface1 rounded w-48" />
          <div className="h-96 bg-surface1 rounded-lg" />
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text mb-2">Diagnostics</h1>
          <p className="text-muted">Sistem durumu ve debug bilgileri</p>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
        >
          {copied ? (
            <>
              <MdCheckCircle />
              Kopyalandı
            </>
          ) : (
            <>
              <MdContentCopy />
              JSON Kopyala
            </>
          )}
        </button>
      </div>

      {/* Health JSON */}
      <div className="bg-surface1 border border-border rounded-lg p-6">
        <h2 className="text-lg font-semibold text-text mb-4">System Health</h2>
        <pre className="bg-background border border-border rounded-lg p-4 overflow-auto max-h-[600px] text-sm text-text font-mono">
          {JSON.stringify(health, null, 2)}
        </pre>
      </div>

      {/* Additional Info */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <h3 className="text-sm font-semibold text-muted mb-2">API Base URL</h3>
          <p className="text-text font-mono text-sm">{window.location.origin}/api</p>
        </div>

        <div className="bg-surface1 border border-border rounded-lg p-6">
          <h3 className="text-sm font-semibold text-muted mb-2">Frontend Version</h3>
          <p className="text-text font-mono text-sm">2.0.0</p>
        </div>

        <div className="bg-surface1 border border-border rounded-lg p-6">
          <h3 className="text-sm font-semibold text-muted mb-2">Build Time</h3>
          <p className="text-text font-mono text-sm">{new Date().toISOString()}</p>
        </div>
      </div>
    </div>
  )
}
