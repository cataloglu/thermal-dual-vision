import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import apiClient, { api } from '../services/api'
import { MdContentCopy, MdCheckCircle, MdRefresh, MdDownload, MdDelete } from 'react-icons/md'
import { LoadingState } from '../components/LoadingState'

const LOG_LINE_OPTIONS = [200, 500, 1000]

export function Diagnostics() {
  const { t } = useTranslation()
  const [systemInfo, setSystemInfo] = useState<any>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [logLineLimit, setLogLineLimit] = useState(1000)
  const [loading, setLoading] = useState(true)
  const [logsLoading, setLogsLoading] = useState(false)
  const [copiedLogs, setCopiedLogs] = useState(false)
  const [clearingLogs, setClearingLogs] = useState(false)
  const [clearedLogs, setClearedLogs] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [appLogFilter, setAppLogFilter] = useState('')
  const [cameraLogFilter, setCameraLogFilter] = useState('')
  const [mediaLogFilter, setMediaLogFilter] = useState('')
  const isRefreshingRef = useRef(false)

  const fetchSystemInfo = useCallback(async () => {
    try {
      const data = await api.getSystemInfo()
      setSystemInfo(data)
    } catch (error) {
      console.error('Failed to fetch system info:', error)
    }
  }, [])

  const fetchLogs = useCallback(async () => {
    try {
      setLogsLoading(true)
      const data = await api.getLogs(logLineLimit)
      setLogs(data.lines || [])
    } catch (error) {
      console.error('Failed to fetch logs:', error)
    } finally {
      setLogsLoading(false)
    }
  }, [logLineLimit])

  useEffect(() => {
    const fetchData = async () => {
      await fetchSystemInfo()
      await fetchLogs()
      setLoading(false)
    }

    fetchData()
  }, [])

  useEffect(() => {
    if (!loading) {
      fetchLogs()
    }
  }, [logLineLimit, fetchLogs])

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(async () => {
      if (isRefreshingRef.current) return
      isRefreshingRef.current = true
      await fetchSystemInfo()
      await fetchLogs()
      isRefreshingRef.current = false
    }, 5000)

    return () => clearInterval(interval)
  }, [autoRefresh, fetchSystemInfo, fetchLogs])

  const handleCopyLogs = () => {
    if (logs.length > 0) {
      navigator.clipboard.writeText(logs.join('\n'))
      setCopiedLogs(true)
      setTimeout(() => setCopiedLogs(false), 2000)
    }
  }

  const handleClearLogs = async () => {
    if (clearingLogs) return
    if (!window.confirm(t('clearLogsConfirm'))) return
    try {
      setClearingLogs(true)
      await api.clearLogs()
      await fetchLogs()
      setClearedLogs(true)
      setTimeout(() => setClearedLogs(false), 2000)
    } catch (error) {
      console.error('Failed to clear logs:', error)
    } finally {
      setClearingLogs(false)
    }
  }

  const handleRefresh = async () => {
    setLoading(true)
    await fetchSystemInfo()
    await fetchLogs()
    setLoading(false)
  }

  // Kamera, hareket algılama, event: burada görünsün
  const cameraLogPatterns = [
    'camera=',
    'detector.',
    'Camera detection',
    'Camera opened',
    'Camera opened successfully',
    'Event created',
    'persons, conf=',
    'Attached to shared frame',
    'Detection parameters',
    'Event gate',
    'Starting detection',
    'Opened camera',
    'Released camera',
    'Frame read',
    'codec',
    'Detections',
    'motion',
    'MOG2',
    'rejected by AI',
    'Live stream',
    'Opening live stream',
  ]
  const isCameraLog = (line: string) =>
    cameraLogPatterns.some((pattern) => line.toLowerCase().includes(pattern.toLowerCase()))

  // Medya: collage, mp4, kayıt, extract, segment
  const mediaLogPatterns = [
    'Media generated',
    'Collage created',
    'Event MP4',
    'recording',
    'extract',
    'segment',
    'Collected',
    'frames from buffer',
    'moov',
    'replaced from recording',
    'buffer MP4',
    'delayed extract',
    'no recording',
  ]
  const isMediaLog = (line: string) =>
    mediaLogPatterns.some((pattern) => line.toLowerCase().includes(pattern.toLowerCase()))

  const { cameraLogs, mediaLogs, applicationLogs, filteredAppLogs, filteredCameraLogs, filteredMediaLogs } = useMemo(() => {
    const cameraLogs = logs.filter((line) => isCameraLog(line) && !isMediaLog(line))
    const mediaLogs = logs.filter((line) => isMediaLog(line))
    const applicationLogs = logs.filter((line) => !isCameraLog(line) && !isMediaLog(line))
    const filteredAppLogs = applicationLogs.filter((line) =>
      appLogFilter ? line.toLowerCase().includes(appLogFilter.toLowerCase()) : true
    )
    const filteredCameraLogs = cameraLogs.filter((line) =>
      cameraLogFilter ? line.toLowerCase().includes(cameraLogFilter.toLowerCase()) : true
    )
    const filteredMediaLogs = mediaLogs.filter((line) =>
      mediaLogFilter ? line.toLowerCase().includes(mediaLogFilter.toLowerCase()) : true
    )
    return { cameraLogs, mediaLogs, applicationLogs, filteredAppLogs, filteredCameraLogs, filteredMediaLogs }
  }, [logs, appLogFilter, cameraLogFilter, mediaLogFilter])

  const parseLogLine = (line: string) => {
    const pipeMatch = line.match(
      /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:,\d{3})?\s+\|\s+(\w+)\s+\|\s+([^|]+)\|\s+(.*)$/
    )
    if (pipeMatch) {
      return {
        time: pipeMatch[1],
        logger: pipeMatch[3].trim(),
        level: pipeMatch[2].trim(),
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

  const handleDownloadLogs = () => {
    const content = filteredAppLogs.join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `logs-${new Date().toISOString().slice(0, 10)}.txt`
    link.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return <LoadingState variant="panel" />
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text mb-2">{t('diagnostics')}</h1>
          <p className="text-muted">{t('diagnosticsSummary')}</p>
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
            <span className="text-sm text-text">{t('autoRefresh')} (5s)</span>
          </label>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            <MdRefresh className={loading ? 'animate-spin' : ''} />
            {t('refresh')}
          </button>
        </div>
      </div>

      {/* 1) Kamera & hareket algılama logları – önce bu ekran */}
      <div className="bg-surface1 border border-border rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-text">
            {t('cameraLogs')} ({cameraLogs.length} / {logLineLimit})
          </h2>
        </div>
        <p className="text-muted text-sm mb-4">
          {t('cameraLogsDesc')}
        </p>
        <div className="mb-4">
          <input
            type="text"
            value={cameraLogFilter}
            onChange={(e) => setCameraLogFilter(e.target.value)}
            placeholder={t('filter')}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent text-sm"
          />
        </div>
        {logsLoading ? (
          <div className="bg-background border border-border rounded-lg p-4 flex items-center justify-center h-80">
            <div className="text-muted">{t('loading')}...</div>
          </div>
        ) : (
          <div className="bg-background border border-border rounded-lg p-4 overflow-auto max-h-80">
            {filteredCameraLogs.length > 0 ? (
              <div className="space-y-2 text-xs font-mono">
                {filteredCameraLogs.map((line, idx) => {
                  const parsed = parseLogLine(line)
                  return (
                    <div key={`cam-${line}-${idx}`} className="flex flex-col gap-1">
                      <div className="flex flex-wrap gap-2">
                        {parsed.time && (
                          <span className="text-muted">{parsed.time}</span>
                        )}
                        {parsed.level && (
                          <span className={`font-semibold ${levelClass(parsed.level)}`}>
                            {parsed.level}
                          </span>
                        )}
                        {parsed.logger && (
                          <span className="text-muted">{parsed.logger}</span>
                        )}
                      </div>
                      <div className="text-text">{parsed.message}</div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-muted">{t('noData')}</div>
            )}
          </div>
        )}
      </div>

      {/* 2) Medya logları */}
      <div className="bg-surface1 border border-border rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-text">
            {t('mediaLogs')} ({mediaLogs.length} / {logLineLimit})
          </h2>
        </div>
        <p className="text-muted text-sm mb-4">
          {t('mediaLogsDesc')}
        </p>
        <div className="mb-4">
          <input
            type="text"
            value={mediaLogFilter}
            onChange={(e) => setMediaLogFilter(e.target.value)}
            placeholder={t('filter')}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent text-sm"
          />
        </div>
        {logsLoading ? (
          <div className="bg-background border border-border rounded-lg p-4 flex items-center justify-center h-80">
            <div className="text-muted">{t('loading')}...</div>
          </div>
        ) : (
          <div className="bg-background border border-border rounded-lg p-4 overflow-auto max-h-80">
            {filteredMediaLogs.length > 0 ? (
              <div className="space-y-2 text-xs font-mono">
                {filteredMediaLogs.map((line, idx) => {
                  const parsed = parseLogLine(line)
                  return (
                    <div key={`med-${line}-${idx}`} className="flex flex-col gap-1">
                      <div className="flex flex-wrap gap-2">
                        {parsed.time && (
                          <span className="text-muted">{parsed.time}</span>
                        )}
                        {parsed.level && (
                          <span className={`font-semibold ${levelClass(parsed.level)}`}>
                            {parsed.level}
                          </span>
                        )}
                        {parsed.logger && (
                          <span className="text-muted">{parsed.logger}</span>
                        )}
                      </div>
                      <div className="text-text">{parsed.message}</div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-muted">{t('noData')}</div>
            )}
          </div>
        )}
      </div>

      {/* 3) Sistem / uygulama logları */}
      <div className="bg-surface1 border border-border rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-text">
            {t('applicationLogs')} ({applicationLogs.length} / {logLineLimit})
          </h2>
          <div className="flex items-center gap-2">
            <label className="text-xs text-muted">{t('logLines')}</label>
            <select
              value={logLineLimit}
              onChange={(e) => setLogLineLimit(Number(e.target.value))}
              className="px-2 py-1 bg-surface2 border border-border text-text rounded-lg text-xs"
            >
              {LOG_LINE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <button
              onClick={handleClearLogs}
              disabled={logsLoading || clearingLogs}
              className="flex items-center gap-2 px-3 py-1.5 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm disabled:opacity-50"
            >
              {clearedLogs ? (
                <>
                  <MdCheckCircle className="text-green-500" />
                  {t('cleared')}
                </>
              ) : (
                <>
                  <MdDelete />
                  {t('clearLogs')}
                </>
              )}
            </button>
            <button
              onClick={handleDownloadLogs}
              className="flex items-center gap-2 px-3 py-1.5 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm"
            >
              <MdDownload />
              {t('download')}
            </button>
            <button
              onClick={handleCopyLogs}
              disabled={logsLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm disabled:opacity-50"
            >
              {copiedLogs ? (
                <>
                  <MdCheckCircle className="text-green-500" />
                  {t('copied')}
                </>
              ) : (
                <>
                  <MdContentCopy />
                  {t('copy')}
                </>
              )}
            </button>
          </div>
        </div>
        <p className="text-muted text-sm mb-4">
          {t('applicationLogsDesc')}
        </p>
        <div className="mb-4">
          <input
            type="text"
            value={appLogFilter}
            onChange={(e) => setAppLogFilter(e.target.value)}
            placeholder={t('filter')}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent text-sm"
          />
        </div>
        {logsLoading ? (
          <div className="bg-background border border-border rounded-lg p-4 flex items-center justify-center h-96">
            <div className="text-muted">{t('loading')}...</div>
          </div>
        ) : (
          <div className="bg-background border border-border rounded-lg p-4 overflow-auto max-h-96">
            {filteredAppLogs.length > 0 ? (
              <div className="space-y-2 text-xs font-mono">
                {filteredAppLogs.map((line, idx) => {
                  const parsed = parseLogLine(line)
                  return (
                    <div key={`${line}-${idx}`} className="flex flex-col gap-1">
                      <div className="flex flex-wrap gap-2">
                        {parsed.time && (
                          <span className="text-muted">{parsed.time}</span>
                        )}
                        {parsed.level && (
                          <span className={`font-semibold ${levelClass(parsed.level)}`}>
                            {parsed.level}
                          </span>
                        )}
                        {parsed.logger && (
                          <span className="text-muted">{parsed.logger}</span>
                        )}
                      </div>
                      <div className="text-text">{parsed.message}</div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-muted">{t('noData')}</div>
            )}
          </div>
        )}
      </div>

      {/* System Info */}
      {systemInfo && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-surface1 border border-border rounded-lg p-6">
            <h3 className="text-sm font-semibold text-muted mb-2">{t('cpuUsage')}</h3>
            <p className="text-text text-2xl font-bold">{systemInfo.cpu?.percent ?? '-' }%</p>
          </div>

          <div className="bg-surface1 border border-border rounded-lg p-6">
            <h3 className="text-sm font-semibold text-muted mb-2">{t('memoryUsage')}</h3>
            <p className="text-text text-2xl font-bold">
              {systemInfo.memory?.used_gb ?? '-'} / {systemInfo.memory?.total_gb ?? '-'} GB
            </p>
            <p className="text-muted text-sm mt-1">{systemInfo.memory?.percent ?? '-'}%</p>
          </div>

          <div className="bg-surface1 border border-border rounded-lg p-6">
            <h3 className="text-sm font-semibold text-muted mb-2">{t('systemDisk')}</h3>
            <p className="text-text text-2xl font-bold">
              {systemInfo.disk?.used_gb ?? '-'} / {systemInfo.disk?.total_gb ?? '-'} GB
            </p>
            <p className="text-muted text-sm mt-1">{systemInfo.disk?.percent ?? '-'}%</p>
            <p className="text-muted text-xs mt-2">{t('diagnosticsDiskNote')}</p>
          </div>

          <div className="bg-surface1 border border-border rounded-lg p-6">
            <h3 className="text-sm font-semibold text-muted mb-2">{t('diagnosticsAddonData')}</h3>
            <p className="text-text text-2xl font-bold">{systemInfo.addon_data_gb ?? '-'} GB</p>
            <p className="text-muted text-xs mt-2">{t('diagnosticsAddonDataDesc')}</p>
          </div>
        </div>
      )}

      {/* Additional Info */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <h3 className="text-sm font-semibold text-muted mb-2">{t('apiBaseUrl')}</h3>
          <p className="text-text font-mono text-sm break-all">
            {(() => {
              const base = apiClient.defaults.baseURL || '/api'
              return base.startsWith('http') ? base : new URL(base, window.location.origin).toString()
            })()}
          </p>
        </div>

        <div className="bg-surface1 border border-border rounded-lg p-6">
          <h3 className="text-sm font-semibold text-muted mb-2">{t('addonVersion')}</h3>
          <p className="text-text font-mono text-sm">{systemInfo?.version ?? '-'}</p>
        </div>

        <div className="bg-surface1 border border-border rounded-lg p-6">
          <h3 className="text-sm font-semibold text-muted mb-2">{t('logLines')}</h3>
          <p className="text-text font-mono text-sm">{logs.length} / {logLineLimit}</p>
        </div>

        {/* Worker mode (threading vs multiprocessing) - confirms multiprocessing is active */}
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <h3 className="text-sm font-semibold text-muted mb-2">{t('diagnosticsWorker')}</h3>
          {systemInfo?.worker ? (
            <div className="text-text text-sm space-y-1">
              <p>
                <span className="text-muted">{t('diagnosticsWorkerMode')}:</span>{' '}
                <span className="font-mono">{systemInfo.worker.mode ?? '-'}</span>
              </p>
              {systemInfo.worker.process_count != null && (
                <p>
                  <span className="text-muted">{t('diagnosticsWorkerProcesses')}:</span>{' '}
                  <span className="font-mono">{systemInfo.worker.process_count}</span>
                </p>
              )}
              {Array.isArray(systemInfo.worker.pids) && systemInfo.worker.pids.length > 0 && (
                <p className="text-muted text-xs font-mono mt-1">
                  PIDs: {systemInfo.worker.pids.join(', ')}
                </p>
              )}
            </div>
          ) : (
            <p className="text-muted text-sm">-</p>
          )}
        </div>
      </div>
    </div>
  )
}
