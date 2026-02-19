import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { MdCheckCircle, MdWarning, MdError, MdVideocam, MdSmartToy } from 'react-icons/md'
import { useWebSocket } from '../hooks/useWebSocket'
import { LoadingState } from '../components/LoadingState'

interface HealthData {
  status: string
  version: string
  uptime_s: number
  ai: {
    enabled: boolean
    reason: string
  }
  cameras: {
    online: number
    retrying: number
    down: number
  }
  components: {
    pipeline: string
    telegram: string
    mqtt: string
  }
}

interface Event {
  id: string
  camera_id: string
  timestamp: string
  confidence: number
  event_type: string
  summary: string | null
  collage_url: string | null
  gif_url: string | null
  mp4_url: string | null
}

interface HealthSnapshot {
  timestamp: string
  status: string
  cameras: HealthData['cameras']
}

export function Dashboard() {
  const { t } = useTranslation()
  const [health, setHealth] = useState<HealthData | null>(null)
  const [lastEvent, setLastEvent] = useState<Event | null>(null)
  const [cameras, setCameras] = useState<{ id: string; name: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [healthHistory, setHealthHistory] = useState<HealthSnapshot[]>([])

  const pushHealthSnapshot = useCallback((next: HealthData) => {
    setHealthHistory((hist) => {
      const last = hist[hist.length - 1]
      const isDuplicate =
        last &&
        last.status === next.status &&
        last.cameras.online === next.cameras.online &&
        last.cameras.retrying === next.cameras.retrying &&
        last.cameras.down === next.cameras.down
      if (isDuplicate) return hist
      return [
        ...hist,
        {
          timestamp: new Date().toISOString(),
          status: next.status,
          cameras: next.cameras,
        },
      ].slice(-6)
    })
  }, [])

  const handleEvent = useCallback((data: any) => {
    setLastEvent(data)
  }, [])

  const handleStatus = useCallback((data: any) => {
    setHealth((prev) => {
      if (!prev) return prev
      const counts = data?.counts
      if (!counts) return prev
      const next = {
        ...prev,
        cameras: {
          online: counts.online ?? prev.cameras.online,
          retrying: counts.retrying ?? prev.cameras.retrying,
          down: counts.down ?? prev.cameras.down,
        },
      }
      pushHealthSnapshot(next)
      return next
    })
  }, [pushHealthSnapshot])

  const wsOptions = useMemo(
    () => ({
      onEvent: handleEvent,
      onStatus: handleStatus,
    }),
    [handleEvent, handleStatus]
  )

  useWebSocket('/api/ws/events', wsOptions)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const healthData = await api.getHealth()
        setHealth(healthData)
        pushHealthSnapshot(healthData)
      } catch (error) {
        console.error('Failed to fetch health:', error)
      }

      try {
        const [eventsData, camerasRes] = await Promise.all([
          api.getEvents({ page: 1, page_size: 1 }),
          api.getCameras(),
        ])
        if (eventsData.events.length > 0) {
          setLastEvent(eventsData.events[0])
        }
        setCameras(camerasRes.cameras || [])
      } catch (error) {
        console.error('Failed to fetch events:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    // WebSocket handles real-time updates; only fetch once on mount
  }, [])

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (days > 0) return `${days}g ${hours}s ${minutes}d`
    if (hours > 0) return `${hours}s ${minutes}d`
    if (minutes > 0) return `${minutes}d ${secs}sn`
    return `${secs}sn`
  }

  const aiReason = useMemo(() => {
    if (!health) return ''
    if (health.ai.enabled) return ''
    const reason = health.ai.reason
    const reasonMap: Record<string, string> = {
      no_api_key: t('aiReasonNoApiKey'),
      not_configured: t('aiReasonNotConfigured'),
    }
    return reasonMap[reason] || reason
  }, [health, t])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ok':
        return <MdCheckCircle className="text-green-500 text-2xl" />
      case 'degraded':
        return <MdWarning className="text-yellow-500 text-2xl" />
      default:
        return <MdError className="text-red-500 text-2xl" />
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      ok: 'bg-green-500/20 text-green-500',
      degraded: 'bg-yellow-500/20 text-yellow-500',
      down: 'bg-red-500/20 text-red-500',
    }
    
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[status as keyof typeof colors] || colors.down}`}>
        {status.toUpperCase()}
      </span>
    )
  }

  if (loading) {
    return <LoadingState variant="cards" cardCount={4} />
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text mb-2">{t('dashboard')}</h1>
          <p className="text-muted">Sistem durumu ve özet bilgiler</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/settings?tab=cameras"
            className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
          >
            {t('add')} {t('camera')}
          </Link>
          <Link
            to="/live"
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors"
          >
            {t('live')}
          </Link>
        </div>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* System Health Card */}
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text">{t('systemStatus')}</h3>
            {health && getStatusIcon(health.status)}
          </div>
          
          {health && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">{t('status')}</span>
                {getStatusBadge(health.status)}
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">{t('version')}</span>
                <span className="text-text font-medium">{health.version}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">{t('uptime')}</span>
                <span className="text-text font-medium">{formatUptime(health.uptime_s)}</span>
              </div>
            </div>
          )}
          {healthHistory.length > 1 && (
            <div className="mt-4 border-t border-border pt-3 space-y-1">
              {healthHistory.slice(-5).map((item) => (
                <div key={item.timestamp} className="flex items-center justify-between text-xs text-muted">
                  <span>{new Date(item.timestamp).toLocaleTimeString('tr-TR')}</span>
                  <span className="text-text">
                    {item.cameras.online}/{item.cameras.retrying}/{item.cameras.down}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cameras Summary Card */}
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text">{t('cameras')}</h3>
            <MdVideocam className="text-accent text-2xl" />
          </div>
          
          {health && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">{t('online')}</span>
                <span className="text-green-500 font-bold text-xl">{health.cameras.online}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">{t('retrying')}</span>
                <span className="text-yellow-500 font-bold text-xl">{health.cameras.retrying}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">{t('down')}</span>
                <span className="text-red-500 font-bold text-xl">{health.cameras.down}</span>
              </div>
            </div>
          )}
        </div>

        {/* AI Status Card */}
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text">{t('aiStatus')}</h3>
            <MdSmartToy className="text-accent text-2xl" />
          </div>
          
          {health && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">{t('status')}</span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  health.ai.enabled 
                    ? 'bg-green-500/20 text-green-500' 
                    : 'bg-gray-500/20 text-gray-500'
                }`}>
                  {health.ai.enabled ? t('enabled').toUpperCase() : t('disabled').toUpperCase()}
                </span>
              </div>
              
              {!health.ai.enabled && (
                <div className="pt-2">
                  <p className="text-muted text-sm">
                    {t('reason')}: {aiReason}
                  </p>
                </div>
              )}
              
              {health.ai.enabled && (
                <div className="pt-2">
                  <p className="text-green-500 text-sm">
                    Event özetleri oluşturuluyor
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Last Event Card */}
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text">{t('lastEvent')}</h3>
          </div>
          
          {lastEvent ? (
            <Link to="/events" className="block group">
              <div className="space-y-3">
                {/* Collage Thumbnail */}
                <div className="aspect-video bg-surface2 rounded-lg overflow-hidden">
                  {lastEvent.collage_url ? (
                    <img 
                      src={api.resolveApiPath(lastEvent.collage_url)} 
                      alt="Event collage"
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xs text-muted">
                      {Date.now() - new Date(lastEvent.timestamp).getTime() < 30000
                        ? t('processing')
                        : t('noData')}
                    </div>
                  )}
                </div>
                
                {/* Event Info */}
                <div className="space-y-1">
                  <p className="text-text font-medium truncate">
                    {t('camera')}: {cameras.find((c) => c.id === lastEvent.camera_id)?.name ?? lastEvent.camera_id}
                  </p>
                  <p className="text-muted text-sm">
                    {new Date(lastEvent.timestamp).toLocaleString('tr-TR')}
                  </p>
                  <p className="text-accent text-sm group-hover:underline">
                    {t('view')} →
                  </p>
                </div>
              </div>
            </Link>
          ) : (
            <div className="flex items-center justify-center h-32">
              <p className="text-muted text-sm">{t('noEvents')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
