import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { MdContentCopy, MdCheckCircle, MdRefresh } from 'react-icons/md'

export function Diagnostics() {
  const [health, setHealth] = useState<any>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [logsLoading, setLogsLoading] = useState(false)
  const [copiedHealth, setCopiedHealth] = useState(false)
  const [copiedLogs, setCopiedLogs] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)

  const fetchHealth = async () => {
    try {
      const data = await api.getHealth()
      setHealth(data)
    } catch (error) {
      console.error('Failed to fetch health:', error)
    }
  }

  const fetchLogs = async () => {
    try {
      setLogsLoading(true)
      const response = await fetch('/api/logs?lines=200')
      const data = await response.json()
      setLogs(data.lines || [])
    } catch (error) {
      console.error('Failed to fetch logs:', error)
    } finally {
      setLogsLoading(false)
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      await Promise.all([fetchHealth(), fetchLogs()])
      setLoading(false)
    }

    fetchData()
  }, [])

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchHealth()
      fetchLogs()
    }, 5000)

    return () => clearInterval(interval)
  }, [autoRefresh])

  const handleCopyHealth = () => {
    if (health) {
      navigator.clipboard.writeText(JSON.stringify(health, null, 2))
      setCopiedHealth(true)
      setTimeout(() => setCopiedHealth(false), 2000)
    }
  }

  const handleCopyLogs = () => {
    if (logs.length > 0) {
      navigator.clipboard.writeText(logs.join('\n'))
      setCopiedLogs(true)
      setTimeout(() => setCopiedLogs(false), 2000)
    }
  }

  const handleRefresh = async () => {
    setLoading(true)
    await Promise.all([fetchHealth(), fetchLogs()])
    setLoading(false)
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

        <div className="flex items-center gap-3">
          {/* Auto-refresh Toggle */}
          <label className="flex items-center gap-2 px-4 py-2 bg-surface1 border border-border rounded-lg cursor-pointer hover:bg-surface2 transition-colors">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 accent-accent"
            />
            <span className="text-sm text-text">Auto-refresh (5s)</span>
          </label>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            <MdRefresh className={loading ? 'animate-spin' : ''} />
            Yenile
          </button>
        </div>
      </div>

      {/* Health JSON */}
      <div className="bg-surface1 border border-border rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text">System Health</h2>
          <button
            onClick={handleCopyHealth}
            className="flex items-center gap-2 px-3 py-1.5 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm"
          >
            {copiedHealth ? (
              <>
                <MdCheckCircle className="text-green-500" />
                Kopyalandı
              </>
            ) : (
              <>
                <MdContentCopy />
                Kopyala
              </>
            )}
          </button>
        </div>
        <pre className="bg-background border border-border rounded-lg p-4 overflow-auto max-h-[400px] text-sm text-text font-mono">
          {JSON.stringify(health, null, 2)}
        </pre>
      </div>

      {/* Logs */}
      <div className="bg-surface1 border border-border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text">Application Logs (Last 200 lines)</h2>
          <button
            onClick={handleCopyLogs}
            disabled={logsLoading}
            className="flex items-center gap-2 px-3 py-1.5 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm disabled:opacity-50"
          >
            {copiedLogs ? (
              <>
                <MdCheckCircle className="text-green-500" />
                Kopyalandı
              </>
            ) : (
              <>
                <MdContentCopy />
                Kopyala
              </>
            )}
          </button>
        </div>
        
        {logsLoading ? (
          <div className="bg-background border border-border rounded-lg p-4 flex items-center justify-center h-96">
            <div className="text-muted">Loglar yükleniyor...</div>
          </div>
        ) : (
          <div className="bg-background border border-border rounded-lg p-4 overflow-auto max-h-96">
            <pre className="text-xs text-text font-mono whitespace-pre-wrap">
              {logs.length > 0 ? logs.join('\n') : 'Log bulunamadı'}
            </pre>
          </div>
        )}
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
          <h3 className="text-sm font-semibold text-muted mb-2">Log Lines</h3>
          <p className="text-text font-mono text-sm">{logs.length} / 200</p>
        </div>
      </div>
    </div>
  )
}
