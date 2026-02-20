import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { MdContentCopy, MdRefresh, MdDownload, MdDelete, MdPause, MdPlayArrow } from 'react-icons/md'
import { LoadingState } from '../components/LoadingState'

const LOG_LINE_OPTIONS = [200, 500, 1000]
const AUTO_REFRESH_INTERVAL_MS = 3000

export function Logs() {
  const { t } = useTranslation()
  const [logs, setLogs] = useState<string[]>([])
  const [logLineLimit, setLogLineLimit] = useState(1000)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [copied, setCopied] = useState(false)
  const [clearing, setClearing] = useState(false)
  const logEndRef = useRef<HTMLDivElement>(null)
  const logContainerRef = useRef<HTMLDivElement>(null)
  const userScrolledRef = useRef(false)

  const handleScroll = useCallback(() => {
    const el = logContainerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    userScrolledRef.current = !atBottom
  }, [])

  const fetchLogs = async () => {
    try {
      const data: { lines?: string[] } = await api.getLogs(logLineLimit)
      setLogs(data.lines || [])
    } catch (error) {
      console.error('Failed to fetch logs:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [logLineLimit])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(fetchLogs, AUTO_REFRESH_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [autoRefresh, logLineLimit])

  useEffect(() => {
    if (!userScrolledRef.current) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs])

  const filteredLogs = filter
    ? logs.filter((line) => line.toLowerCase().includes(filter.toLowerCase()))
    : logs

  const parseLogLine = (line: string) => {
    const pipeMatch = line.match(
      /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:,\d{3})?\s+\|\s+(\w+)\s+\|\s+([^|]+)\|\s+(.*)$/
    )
    if (pipeMatch) {
      return {
        time: pipeMatch[1],
        level: pipeMatch[2].trim(),
        logger: pipeMatch[3].trim(),
        message: pipeMatch[4],
      }
    }
    const dashMatch = line.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.*)$/)
    if (dashMatch) {
      return {
        time: dashMatch[1],
        logger: dashMatch[2].trim(),
        level: dashMatch[3],
        message: dashMatch[4],
      }
    }
    return { time: '', logger: '', level: '', message: line }
  }

  const levelClass = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'text-error'
      case 'WARNING':
        return 'text-warning'
      case 'INFO':
        return 'text-success'
      case 'DEBUG':
        return 'text-muted'
      default:
        return 'text-text'
    }
  }

  const handleCopy = () => {
    if (filteredLogs.length > 0) {
      navigator.clipboard.writeText(filteredLogs.join('\n'))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDownload = () => {
    const content = filteredLogs.join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `logs-${new Date().toISOString().slice(0, 10)}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  const handleClear = async () => {
    if (clearing) return
    if (!window.confirm(t('clearLogsConfirm'))) return
    try {
      setClearing(true)
      await api.clearLogs()
      await fetchLogs()
    } catch (error) {
      console.error('Failed to clear logs:', error)
    } finally {
      setClearing(false)
    }
  }

  if (loading && logs.length === 0) {
    return <LoadingState variant="panel" />
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-text">{t('logs')}</h1>
          <p className="text-sm text-muted">{t('logsDesc')}</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Auto-refresh */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
              autoRefresh ? 'bg-accent text-white' : 'bg-surface1 border border-border text-muted hover:text-text'
            }`}
            title={autoRefresh ? t('pauseRefresh') : t('startRefresh')}
          >
            {autoRefresh ? <MdPause className="text-lg" /> : <MdPlayArrow className="text-lg" />}
            <span className="text-sm">{autoRefresh ? t('liveRefresh') : t('paused')}</span>
          </button>
          {/* Line limit */}
          <select
            value={logLineLimit}
            onChange={(e) => setLogLineLimit(Number(e.target.value))}
            className="px-3 py-2 bg-surface1 border border-border rounded-lg text-text text-sm"
          >
            {LOG_LINE_OPTIONS.map((n) => (
              <option key={n} value={n}>
                {n} {t('lines')}
              </option>
            ))}
          </select>
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-surface1 border border-border rounded-lg text-text hover:bg-surface2 transition-colors disabled:opacity-50"
          >
            <MdRefresh className={loading ? 'animate-spin' : ''} />
            {t('refresh')}
          </button>
          <button
            onClick={handleCopy}
            disabled={filteredLogs.length === 0}
            className="flex items-center gap-2 px-3 py-2 bg-surface1 border border-border rounded-lg text-text hover:bg-surface2 transition-colors disabled:opacity-50"
          >
            <MdContentCopy />
            {copied ? t('copied') : t('copy')}
          </button>
          <button
            onClick={handleDownload}
            disabled={filteredLogs.length === 0}
            className="flex items-center gap-2 px-3 py-2 bg-surface1 border border-border rounded-lg text-text hover:bg-surface2 transition-colors disabled:opacity-50"
          >
            <MdDownload />
            {t('download')}
          </button>
          <button
            onClick={handleClear}
            disabled={clearing}
            className="flex items-center gap-2 px-3 py-2 bg-error/20 text-error border border-error/50 rounded-lg hover:bg-error/30 transition-colors disabled:opacity-50"
          >
            <MdDelete />
            {t('clearLogs')}
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="mb-4 shrink-0">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder={t('filter')}
          className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
        />
      </div>

      {/* Log content - full height */}
      <div className="flex-1 min-h-0 bg-surface1 border border-border rounded-lg overflow-hidden">
        <div ref={logContainerRef} onScroll={handleScroll} className="h-full overflow-auto p-4 font-mono text-xs">
          {filteredLogs.length > 0 ? (
            <div className="space-y-1">
              {filteredLogs.map((line, idx) => {
                const parsed = parseLogLine(line)
                return (
                  <div key={`${idx}-${line.slice(0, 50)}`} className="flex flex-wrap gap-2">
                    {parsed.time && <span className="text-muted shrink-0">{parsed.time}</span>}
                    {parsed.level && (
                      <span className={`font-semibold shrink-0 ${levelClass(parsed.level)}`}>
                        {parsed.level}
                      </span>
                    )}
                    {parsed.logger && <span className="text-muted shrink-0">{parsed.logger}</span>}
                    <span className="text-text break-all">{parsed.message}</span>
                  </div>
                )
              })}
              <div ref={logEndRef} />
            </div>
          ) : (
            <div className="text-muted">{t('noData')}</div>
          )}
        </div>
      </div>
      <p className="mt-2 text-xs text-muted shrink-0">
        {filteredLogs.length} / {logs.length} {t('lines')}
        {autoRefresh && ` • ${t('autoRefresh')} ${AUTO_REFRESH_INTERVAL_MS / 1000}s`}
      </p>
    </div>
  )
}
