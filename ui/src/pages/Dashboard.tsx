import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { MdCheckCircle, MdWarning, MdError, MdVideocam, MdSmartToy } from 'react-icons/md'
import toast from 'react-hot-toast'

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
  collage_url: string
  gif_url: string
  mp4_url: string
}

export function Dashboard() {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [lastEvent, setLastEvent] = useState<Event | null>(null)
  const [loading, setLoading] = useState(true)

  // WebSocket removed (now in Sidebar)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [healthData, eventsData] = await Promise.all([
          api.getHealth(),
          api.getEvents({ page: 1, page_size: 1 })
        ])
        
        setHealth(healthData)
        if (eventsData.events.length > 0) {
          setLastEvent(eventsData.events[0])
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    // No more polling! WebSocket handles real-time updates
  }, [])

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (days > 0) return `${days}g ${hours}s`
    if (hours > 0) return `${hours}s ${minutes}d`
    return `${minutes}d`
  }

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
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-surface1 rounded w-48" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-40 bg-surface1 rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text mb-2">Kontrol Paneli</h1>
        <p className="text-muted">Sistem durumu ve özet bilgiler</p>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* System Health Card */}
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text">Sistem Durumu</h3>
            {health && getStatusIcon(health.status)}
          </div>
          
          {health && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">Durum</span>
                {getStatusBadge(health.status)}
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">Versiyon</span>
                <span className="text-text font-medium">{health.version}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">Çalışma Süresi</span>
                <span className="text-text font-medium">{formatUptime(health.uptime_s)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Cameras Summary Card */}
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text">Kameralar</h3>
            <MdVideocam className="text-accent text-2xl" />
          </div>
          
          {health && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">Çevrimiçi</span>
                <span className="text-green-500 font-bold text-xl">{health.cameras.online}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">Yeniden Deniyor</span>
                <span className="text-yellow-500 font-bold text-xl">{health.cameras.retrying}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">Çevrimdışı</span>
                <span className="text-red-500 font-bold text-xl">{health.cameras.down}</span>
              </div>
            </div>
          )}
        </div>

        {/* AI Status Card */}
        <div className="bg-surface1 border border-border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text">AI Durumu</h3>
            <MdSmartToy className="text-accent text-2xl" />
          </div>
          
          {health && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted text-sm">Durum</span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  health.ai.enabled 
                    ? 'bg-green-500/20 text-green-500' 
                    : 'bg-gray-500/20 text-gray-500'
                }`}>
                  {health.ai.enabled ? 'AKTİF' : 'PASİF'}
                </span>
              </div>
              
              {!health.ai.enabled && (
                <div className="pt-2">
                  <p className="text-muted text-sm">
                    Sebep: {health.ai.reason === 'no_api_key' ? 'API key yok' : health.ai.reason}
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
            <h3 className="text-lg font-semibold text-text">Son Olay</h3>
          </div>
          
          {lastEvent ? (
            <Link to="/events" className="block group">
              <div className="space-y-3">
                {/* Collage Thumbnail */}
                <div className="aspect-video bg-surface2 rounded-lg overflow-hidden">
                  <img 
                    src={lastEvent.collage_url} 
                    alt="Event collage"
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  />
                </div>
                
                {/* Event Info */}
                <div className="space-y-1">
                  <p className="text-text font-medium truncate">
                    Kamera: {lastEvent.camera_id}
                  </p>
                  <p className="text-muted text-sm">
                    {new Date(lastEvent.timestamp).toLocaleString('tr-TR')}
                  </p>
                  <p className="text-accent text-sm group-hover:underline">
                    Detayları Gör →
                  </p>
                </div>
              </div>
            </Link>
          ) : (
            <div className="flex items-center justify-center h-32">
              <p className="text-muted text-sm">Henüz olay yok</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
