import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { MdRefresh, MdError, MdCheckCircle } from 'react-icons/md'
import { getLiveSnapshotUrl, getLiveStreamUrl, resolveApiPath } from '../services/api'

/** Max concurrent live streams (backend limit); only this many tiles load MJPEG. */
export const MAX_LIVE_STREAMS = 2

interface StreamViewerProps {
  cameraId: string
  cameraName: string
  streamUrl?: string
  status?: 'connected' | 'retrying' | 'down' | 'initializing'
  /** If false, show placeholder instead of loading stream (to respect backend limit). */
  loadStream?: boolean
}

interface LiveDebugInfo {
  ok?: boolean
  source?: string | null
  go2rtc_ok?: boolean
  go2rtc_error?: string | null
  rtsp_available?: boolean
  worker_frame?: boolean
  stream_name?: string | null
  status?: number
  error?: string
  reason?: string
}

export function StreamViewer({
  cameraId,
  cameraName,
  status,
  loadStream = true,
}: StreamViewerProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [isVisible, setIsVisible] = useState(true)
  const [snapshotMode, setSnapshotMode] = useState(false)
  const [snapshotTick, setSnapshotTick] = useState(0)
  const [debugInfo, setDebugInfo] = useState<LiveDebugInfo | null>(null)
  const [debugUpdatedAt, setDebugUpdatedAt] = useState('')

  const imgRef = useRef<HTMLImageElement>(null)
  const retryTimeoutRef = useRef<number | null>(null)
  const loadingTimeoutRef = useRef<number | null>(null)
  const stallTimeoutRef = useRef<number | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const lastDebugRef = useRef(0)
  const maxRetries = 15
  const RETRY_DELAYS = [1500, 2500, 4000, 6000, 8000, 10000, 12000, 15000, 18000, 20000]
  // Allow extra time for go2rtc probe + worker fallback startup before switching to snapshots.
  const STALL_SNAPSHOT_MS = 15000

  const effectiveUrl = resolveApiPath(getLiveStreamUrl(cameraId))
  const snapshotUrl = resolveApiPath(getLiveSnapshotUrl(cameraId))
  const probeUrl = `${effectiveUrl}${effectiveUrl.includes('?') ? '&' : '?'}probe=1`

  const updateDebug = useCallback(
    async (reason: string) => {
      const now = Date.now()
      if (now - lastDebugRef.current < 1000) return
      lastDebugRef.current = now
      try {
        const res = await fetch(`${probeUrl}&t=${now}`, { cache: 'no-store' })
        const data = await res.json().catch(() => null)
        setDebugInfo({
          ...(data ?? {}),
          status: res.status,
          reason,
        })
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err)
        setDebugInfo({ ok: false, error: message, reason })
      }
      setDebugUpdatedAt(new Date().toLocaleTimeString())
    },
    [probeUrl]
  )

  const formatBool = (value?: boolean) => (value ? t('liveDebugYes') : t('liveDebugNo'))
  const formatValue = (value?: string | number | null) =>
    value === null || value === undefined || value === '' ? '-' : String(value)

  useEffect(() => {
    setLoading(true)
    setError(false)
    setSnapshotMode(false)
    setSnapshotTick(0)
    setDebugInfo(null)
    setDebugUpdatedAt('')
    if (retryTimeoutRef.current) {
      window.clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
    if (loadingTimeoutRef.current) {
      window.clearTimeout(loadingTimeoutRef.current)
      loadingTimeoutRef.current = null
    }
    if (stallTimeoutRef.current) {
      window.clearTimeout(stallTimeoutRef.current)
      stallTimeoutRef.current = null
    }
  }, [cameraId])

  useEffect(() => {
    if (!containerRef.current) {
      setIsVisible(true)
      return
    }
    if (typeof IntersectionObserver === 'undefined') {
      setIsVisible(true)
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting)
      },
      { rootMargin: '200px', threshold: 0.1 }
    )
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!isVisible || !loadStream) {
      if (imgRef.current) imgRef.current.src = ''
      return
    }
    setLoading(true)
    setError(false)
    setRetryCount(0)
    updateDebug('visibility_change')
    if (retryTimeoutRef.current) {
      window.clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
    if (stallTimeoutRef.current) {
      window.clearTimeout(stallTimeoutRef.current)
    }
    stallTimeoutRef.current = window.setTimeout(() => {
      if (!snapshotMode && imgRef.current) {
        setSnapshotMode(true)
        setError(false)
        setRetryCount(0)
        updateDebug('stall_snapshot')
        // Reset the loading timeout so snapshot spinner auto-clears even if onLoad is slow.
        if (loadingTimeoutRef.current) {
          window.clearTimeout(loadingTimeoutRef.current)
        }
        loadingTimeoutRef.current = window.setTimeout(() => {
          setLoading(false)
        }, 2500)
      }
    }, STALL_SNAPSHOT_MS)
  }, [isVisible, loadStream, updateDebug])

  useEffect(() => {
    if (!snapshotMode) return
    const interval = window.setInterval(() => {
      setSnapshotTick((prev) => prev + 1)
    }, 1000)
    return () => window.clearInterval(interval)
  }, [snapshotMode])

  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        window.clearTimeout(retryTimeoutRef.current)
      }
      if (loadingTimeoutRef.current) {
        window.clearTimeout(loadingTimeoutRef.current)
      }
      if (stallTimeoutRef.current) {
        window.clearTimeout(stallTimeoutRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!loadStream || !isVisible) return
    if (loadingTimeoutRef.current) {
      window.clearTimeout(loadingTimeoutRef.current)
    }
    loadingTimeoutRef.current = window.setTimeout(() => {
      setLoading(false)
    }, 1500)
  }, [isVisible, cameraId, loadStream])

  const handleLoad = () => {
    if (!isVisible) return
    setLoading(false)
    setError(false)
    setRetryCount(0)
    if (stallTimeoutRef.current) {
      window.clearTimeout(stallTimeoutRef.current)
      stallTimeoutRef.current = null
    }
    updateDebug('load')
  }

  const handleError = () => {
    if (!isVisible) return
    setLoading(false)
    setError(true)
    updateDebug('img_error')
    if (!snapshotMode && retryCount >= 1) {
      setSnapshotMode(true)
      setError(false)
      setLoading(true)
      if (imgRef.current) {
        imgRef.current.src = `${snapshotUrl}?t=${Date.now()}`
      }
      return
    }
    if (retryCount < maxRetries) {
      const delay = RETRY_DELAYS[Math.min(retryCount, RETRY_DELAYS.length - 1)]
      retryTimeoutRef.current = window.setTimeout(() => {
        setRetryCount((prev) => prev + 1)
        setError(false)
        setLoading(true)
        if (imgRef.current) {
          const baseUrl = snapshotMode ? snapshotUrl : effectiveUrl
          imgRef.current.src = `${baseUrl}?t=${Date.now()}`
        }
      }, delay)
    }
  }

  const handleRetry = () => {
    setRetryCount(0)
    setError(false)
    setLoading(true)
    setSnapshotMode(false)
    if (stallTimeoutRef.current) {
      window.clearTimeout(stallTimeoutRef.current)
    }
    stallTimeoutRef.current = window.setTimeout(() => {
      if (!snapshotMode && imgRef.current) {
        setSnapshotMode(true)
        setError(false)
        setRetryCount(0)
        updateDebug('stall_snapshot')
        if (loadingTimeoutRef.current) {
          window.clearTimeout(loadingTimeoutRef.current)
        }
        loadingTimeoutRef.current = window.setTimeout(() => {
          setLoading(false)
        }, 2500)
      }
    }, STALL_SNAPSHOT_MS)
    updateDebug('manual_retry')
    if (retryTimeoutRef.current) {
      window.clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
    if (imgRef.current) {
      imgRef.current.src = `${effectiveUrl}?t=${Date.now()}`
    }
  }

  const statusColors = {
    connected: 'bg-green-500',
    retrying: 'bg-yellow-500',
    down: 'bg-red-500',
    initializing: 'bg-blue-500',
  }

  const statusLabels = {
    connected: t('connected'),
    retrying: t('retrying'),
    down: t('down'),
    initializing: t('initializing'),
  }

  const resolvedStatus = status || 'retrying'

  return (
    <div className="flex flex-col gap-2">
      <div ref={containerRef} className="relative bg-surface2 rounded-lg overflow-hidden aspect-video border border-border">
      {/* Camera Name & Status Overlay */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-black/60 to-transparent p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold">{cameraName}</h3>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${statusColors[resolvedStatus]}`} />
            <span className="text-white text-sm">{statusLabels[resolvedStatus]}</span>
          </div>
        </div>
      </div>

      {/* Placeholder when stream slot limit reached (e.g. only 2 streams on Pi) */}
      {!loadStream && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface2">
          <p className="text-muted text-center px-4 text-sm">
            {t('liveStreamLimit')}
          </p>
        </div>
      )}

      {/* Loading State */}
      {loadStream && loading && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface2">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-accent border-t-transparent mx-auto mb-4" />
            <p className="text-muted">{t('loading')}...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {loadStream && error && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface2">
          <div className="text-center p-6">
            <MdError className="text-red-500 text-5xl mx-auto mb-4" />
            <p className="text-text mb-2">{t('error')}</p>
            <p className="text-muted text-sm mb-4">
              {retryCount}/{maxRetries}
            </p>
            <button
              onClick={handleRetry}
              className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors mx-auto"
            >
              <MdRefresh className="text-lg" />
              {t('refresh')}
            </button>
          </div>
        </div>
      )}

      {/* MJPEG / Snapshot Stream */}
      {loadStream && isVisible && (
        <img
          ref={imgRef}
          src={
            snapshotMode
              ? `${snapshotUrl}?t=${snapshotTick}`
              : effectiveUrl
          }
          alt={cameraName}
          className={`w-full h-full object-contain ${error ? 'hidden' : 'block'}`}
          onLoad={handleLoad}
          onError={handleError}
        />
      )}

      {/* Success Indicator (brief) */}
      {loadStream && !loading && !error && retryCount > 0 && (
        <div className="absolute bottom-4 right-4 bg-green-500 text-white px-3 py-1 rounded-lg flex items-center gap-2 animate-fade-in">
          <MdCheckCircle />
          <span className="text-sm">{t('connected')}</span>
        </div>
      )}
      </div>

      <div className="rounded-lg border border-border bg-surface1 p-3 text-xs text-muted">
        <div className="flex items-center justify-between">
          <span className="text-text font-semibold">{t('liveDebugTitle')}</span>
          <span>{debugUpdatedAt ? `${t('liveDebugUpdated')}: ${debugUpdatedAt}` : t('liveDebugEmpty')}</span>
        </div>
        {debugInfo && (
          <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
            <span>{t('liveDebugOk')}</span>
            <span className={debugInfo.ok ? 'text-green-400' : 'text-red-400'}>
              {formatBool(debugInfo.ok)}
            </span>
            <span>{t('liveDebugSource')}</span>
            <span>{formatValue(debugInfo.source)}</span>
            <span>{t('liveDebugGo2rtc')}</span>
            <span>{formatBool(debugInfo.go2rtc_ok)}</span>
            <span>{t('liveDebugGo2rtcError')}</span>
            <span>{formatValue(debugInfo.go2rtc_error)}</span>
            <span>{t('liveDebugRtsp')}</span>
            <span>{formatBool(debugInfo.rtsp_available)}</span>
            <span>{t('liveDebugWorker')}</span>
            <span>{formatBool(debugInfo.worker_frame)}</span>
            <span>{t('liveDebugSnapshot')}</span>
            <span>{formatBool(snapshotMode)}</span>
            <span>{t('liveDebugReason')}</span>
            <span>{formatValue(debugInfo.reason)}</span>
            <span>{t('liveDebugStatus')}</span>
            <span>{formatValue(debugInfo.status)}</span>
            {debugInfo.error && (
              <>
                <span>{t('liveDebugError')}</span>
                <span>{formatValue(debugInfo.error)}</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
