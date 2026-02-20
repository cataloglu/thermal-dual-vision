import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  MdVideocam,
  MdCircle,
  MdRefresh,
  MdFiberManualRecord,
  MdRadar,
  MdEvent,
  MdAccessTime,
  MdStream,
  MdOpenInNew,
  MdBrokenImage,
} from 'react-icons/md'
import { api } from '../services/api'
import { useWebSocket } from '../hooks/useWebSocket'

interface CameraStatusItem {
  id: string
  name: string
  type: string
  enabled: boolean
  status: 'connected' | 'retrying' | 'down' | 'initializing'
  last_frame_ts: string | null
  event_count_24h: number
  last_event_ts: string | null
  recording: boolean
  detecting: boolean
  go2rtc_ok: boolean
  stream_roles: string[]
}

interface CamerasStatusResponse {
  cameras: CameraStatusItem[]
  go2rtc_ok: boolean
}

function timeAgo(isoTs: string | null, t: (k: string) => string): string {
  if (!isoTs) return t('camMonNever')
  const diff = Math.floor((Date.now() - new Date(isoTs).getTime()) / 1000)
  if (diff < 5) return t('camMonJustNow')
  if (diff < 60) return `${diff}${t('camMonSecAgo')}`
  if (diff < 3600) return `${Math.floor(diff / 60)}${t('camMonMinAgo')}`
  if (diff < 86400) return `${Math.floor(diff / 3600)}${t('camMonHrAgo')}`
  return `${Math.floor(diff / 86400)}${t('camMonDayAgo')}`
}

const STATUS_CONFIG = {
  connected: { dot: 'bg-success', badge: 'bg-success/15 text-success border-success/30', label: 'camMonConnected', ping: true },
  retrying: { dot: 'bg-yellow-500', badge: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30', label: 'camMonRetrying', ping: false },
  down: { dot: 'bg-error', badge: 'bg-error/15 text-error border-error/30', label: 'camMonDown', ping: false },
  initializing: { dot: 'bg-accent', badge: 'bg-accent/15 text-accent border-accent/30', label: 'camMonInitializing', ping: false },
}

function SnapshotImage({ cameraId, snapshotKey }: { cameraId: string; snapshotKey: number }) {
  const [errored, setErrored] = useState(false)
  const [loading, setLoading] = useState(true)
  const { t } = useTranslation()
  const url = `${api.getCameraSnapshotUrl(cameraId)}?t=${snapshotKey}`

  useEffect(() => {
    setErrored(false)
    setLoading(true)
  }, [snapshotKey])

  if (errored) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-muted gap-2">
        <MdBrokenImage className="text-3xl" />
        <span className="text-xs">{t('camMonNoSnapshot')}</span>
      </div>
    )
  }

  return (
    <>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface1">
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      )}
      <img
        src={url}
        alt="snapshot"
        className={`w-full h-full object-cover transition-opacity duration-300 ${loading ? 'opacity-0' : 'opacity-100'}`}
        onLoad={() => setLoading(false)}
        onError={() => { setLoading(false); setErrored(true) }}
      />
    </>
  )
}

function CameraCard({ cam, snapshotKey, t }: { cam: CameraStatusItem; snapshotKey: number; t: (k: string, opts?: Record<string, unknown>) => string }) {
  const cfg = STATUS_CONFIG[cam.status] ?? STATUS_CONFIG.initializing

  return (
    <div className={`bg-surface1 border rounded-xl overflow-hidden flex flex-col transition-all duration-200 hover:shadow-lg ${
      !cam.enabled ? 'opacity-50 border-border' : 'border-border hover:border-accent/50'
    }`}>
      {/* Snapshot thumbnail */}
      <div className="relative w-full h-32 sm:h-40 bg-surface2 flex items-center justify-center overflow-hidden">
        {cam.enabled ? (
          <SnapshotImage cameraId={cam.id} snapshotKey={snapshotKey} />
        ) : (
          <div className="flex flex-col items-center gap-2 text-muted">
            <MdVideocam className="text-3xl" />
            <span className="text-xs">{t('camMonDisabled')}</span>
          </div>
        )}

        {/* Status dot overlay */}
        <div className="absolute top-2 right-2 flex items-center gap-1.5 bg-black/60 backdrop-blur-sm rounded-full px-2 py-1">
          <div className={`relative w-2 h-2 rounded-full ${cfg.dot}`}>
            {cfg.ping && (
              <div className={`absolute inset-0 rounded-full ${cfg.dot} animate-ping opacity-75`} />
            )}
          </div>
          <span className="text-white text-xs font-medium">{t(cfg.label)}</span>
        </div>

        {/* Recording badge */}
        {cam.recording && (
          <div className="absolute top-2 left-2 flex items-center gap-1 bg-red-600/80 backdrop-blur-sm rounded-full px-2 py-1">
            <MdFiberManualRecord className="text-white text-xs animate-pulse" />
            <span className="text-white text-xs font-semibold">REC</span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3 sm:p-4 flex flex-col gap-3 flex-1">
        {/* Name + type */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-text font-semibold text-sm leading-tight">{cam.name}</h3>
            <span className="text-muted text-xs uppercase tracking-wide mt-0.5 block">
              {cam.type === 'dual' ? t('camMonTypeDual') : cam.type === 'thermal' ? t('camMonTypeThermal') : t('camMonTypeColor')}
            </span>
          </div>
          <Link
            to={`/live`}
            className="shrink-0 p-1.5 rounded-lg text-muted hover:text-accent hover:bg-surface2 transition-colors"
            title={t('camMonOpenLive')}
          >
            <MdOpenInNew className="text-base" />
          </Link>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-surface2 rounded-lg p-2.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-muted">
              <MdEvent className="text-sm" />
              <span className="text-xs">{t('camMonEvents24h')}</span>
            </div>
            <span className="text-text font-bold text-lg leading-none">{cam.event_count_24h}</span>
          </div>

          <div className="bg-surface2 rounded-lg p-2.5 flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-muted">
              <MdAccessTime className="text-sm" />
              <span className="text-xs">{t('camMonLastFrame')}</span>
            </div>
            <span className="text-text font-medium text-xs leading-snug">
              {timeAgo(cam.last_frame_ts, t)}
            </span>
          </div>
        </div>

        {/* Badges row */}
        <div className="flex flex-wrap gap-1.5">
          {/* go2rtc */}
          <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium ${
            cam.go2rtc_ok
              ? 'bg-success/10 text-success border-success/30'
              : 'bg-error/10 text-error border-error/30'
          }`}>
            <MdStream className="text-xs" />
            go2rtc
          </span>

          {/* Detecting */}
          <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium ${
            cam.detecting
              ? 'bg-accent/10 text-accent border-accent/30'
              : 'bg-surface2 text-muted border-border'
          }`}>
            <MdRadar className="text-xs" />
            {t('camMonDetecting')}
          </span>

          {/* Recording */}
          {cam.recording && (
            <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium bg-red-500/10 text-red-400 border-red-500/30">
              <MdFiberManualRecord className="text-xs animate-pulse" />
              {t('camMonRecording')}
            </span>
          )}
        </div>

        {/* Last event */}
        {cam.last_event_ts && (
          <div className="text-xs text-muted flex items-center gap-1">
            <MdCircle className="text-[6px] text-accent" />
            {t('camMonLastEvent')}: {timeAgo(cam.last_event_ts, t)}
          </div>
        )}
      </div>
    </div>
  )
}

export function CameraMonitor() {
  const { t } = useTranslation()
  const [data, setData] = useState<CamerasStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [snapshotKey, setSnapshotKey] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true)
    try {
      const res = await api.getCamerasStatus()
      setData(res)
    } catch {
      // silently fail; keep stale data
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  // Auto-refresh every 15s; refresh snapshots every 30s
  useEffect(() => {
    fetchStatus()
    intervalRef.current = setInterval(() => {
      fetchStatus(true)
      setSnapshotKey((k) => k + 1)
    }, 30_000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [fetchStatus])

  // Bump snapshot key on new detection events from WS
  const handleEvent = useCallback(() => {
    setSnapshotKey((k) => k + 1)
    fetchStatus(true)
  }, [fetchStatus])

  useWebSocket('/api/ws/events', { onEvent: handleEvent })

  const handleManualRefresh = () => {
    fetchStatus()
    setSnapshotKey((k) => k + 1)
  }

  const cameras = data?.cameras ?? []
  const connected = cameras.filter((c) => c.status === 'connected').length
  const retrying = cameras.filter((c) => c.status === 'retrying').length
  const down = cameras.filter((c) => c.status === 'down').length

  return (
    <div className="p-4 md:p-6 space-y-5 md:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-text">{t('cameraMonitor')}</h1>
          <p className="text-muted text-sm mt-1">{t('cameraMonitorDesc')}</p>
        </div>
        <button
          onClick={handleManualRefresh}
          disabled={refreshing}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2 bg-surface2 border border-border rounded-lg hover:bg-accent hover:text-white hover:border-accent transition-colors text-text text-sm font-medium disabled:opacity-50"
        >
          <MdRefresh className={`text-lg ${refreshing ? 'animate-spin' : ''}`} />
          {t('camMonRefresh')}
        </button>
      </div>

      {/* Summary bar */}
      {!loading && data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-surface1 border border-border rounded-xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 bg-surface2 rounded-lg flex items-center justify-center">
              <MdVideocam className="text-xl text-muted" />
            </div>
            <div>
              <div className="text-2xl font-bold text-text">{cameras.length}</div>
              <div className="text-xs text-muted">{t('camMonTotal')}</div>
            </div>
          </div>

          <div className="bg-surface1 border border-border rounded-xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <MdCircle className="text-xl text-success" />
            </div>
            <div>
              <div className="text-2xl font-bold text-success">{connected}</div>
              <div className="text-xs text-muted">{t('camMonConnected')}</div>
            </div>
          </div>

          <div className="bg-surface1 border border-border rounded-xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-500/10 rounded-lg flex items-center justify-center">
              <MdCircle className="text-xl text-yellow-500" />
            </div>
            <div>
              <div className="text-2xl font-bold text-yellow-400">{retrying}</div>
              <div className="text-xs text-muted">{t('camMonRetrying')}</div>
            </div>
          </div>

          <div className="bg-surface1 border border-border rounded-xl p-4 flex items-center gap-3">
            <div className="w-10 h-10 bg-error/10 rounded-lg flex items-center justify-center">
              <MdCircle className="text-xl text-error" />
            </div>
            <div>
              <div className="text-2xl font-bold text-error">{down}</div>
              <div className="text-xs text-muted">{t('camMonDown')}</div>
            </div>
          </div>
        </div>
      )}

      {/* Camera grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : cameras.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-muted gap-3">
          <MdVideocam className="text-5xl opacity-30" />
          <p className="text-sm">{t('camMonNoCameras')}</p>
          <Link to="/settings?tab=cameras" className="text-accent text-sm hover:underline">
            {t('camMonAddCamera')}
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {cameras.map((cam) => (
            <CameraCard key={cam.id} cam={cam} snapshotKey={snapshotKey} t={t} />
          ))}
        </div>
      )}
    </div>
  )
}
