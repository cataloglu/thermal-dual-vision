import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { StreamViewer } from '../components/StreamViewer'
import { api } from '../services/api'
import apiClient from '../services/api'
import { MdGridView } from 'react-icons/md'
import { useWebSocket } from '../hooks/useWebSocket'
import { LoadingState } from '../components/LoadingState'

interface Camera {
  id: string
  name: string
  type: string
  enabled: boolean
  status: 'connected' | 'retrying' | 'down' | 'initializing'
  stream_roles: string[]
}

interface LiveStream {
  camera_id: string
  name: string
  stream_url: string
  output_mode: string
}

export function Live() {
  const { t } = useTranslation()
  const [cameras, setCameras] = useState<Camera[]>([])
  const [streams, setStreams] = useState<LiveStream[]>([])
  const [loading, setLoading] = useState(true)
  const [gridMode, setGridMode] = useState<1 | 2 | 3>(2) // 1x1, 2x2, 3x3
  const [visibleCount, setVisibleCount] = useState(6)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [camerasData, streamsData] = await Promise.all([
          api.getCameras(),
          api.getLiveStreams()
        ])
        
        setCameras(camerasData.cameras)
        setStreams(streamsData.streams)
      } catch (error) {
        console.error('Failed to fetch live data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const savedGrid = localStorage.getItem('live_grid_mode')
    if (savedGrid) {
      const mode = Number(savedGrid)
      if (mode === 1 || mode === 2 || mode === 3) {
        setGridMode(mode)
      }
    }
    
    return () => undefined
  }, [])

  const handleStatus = useCallback((data: any) => {
    if (!data?.camera_id) return
    setCameras((prev) =>
      prev.map((cam) =>
        cam.id === data.camera_id ? { ...cam, status: data.status } : cam
      )
    )
  }, [])

  const wsOptions = useMemo(() => ({ onStatus: handleStatus }), [handleStatus])

  useWebSocket('/api/ws/events', wsOptions)

  const getGridClass = () => {
    switch (gridMode) {
      case 1:
        return 'grid-cols-1'
      case 2:
        return 'grid-cols-1 md:grid-cols-2'
      case 3:
        return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'
      default:
        return 'grid-cols-1 md:grid-cols-2'
    }
  }

  useEffect(() => {
    localStorage.setItem('live_grid_mode', String(gridMode))
  }, [gridMode])

  const outputMode = useMemo(() => streams[0]?.output_mode || 'mjpeg', [streams])

  // Filter cameras that have 'live' in stream_roles
  const liveCameras = cameras.filter(cam => 
    cam.enabled && cam.stream_roles.includes('live')
  )
  const visibleCameras = useMemo(() => liveCameras.slice(0, visibleCount), [liveCameras, visibleCount])

  if (loading) {
    return <LoadingState variant="list" listCount={2} />
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text mb-2">{t('live')}</h1>
          <p className="text-muted">
            {liveCameras.length} {t('camera').toLowerCase()} {t('enabled').toLowerCase()}
          </p>
        </div>

        {/* Grid Mode Toggle */}
        <div className="flex items-center gap-2 bg-surface1 border border-border rounded-lg p-1">
          {[1, 2, 3].map((mode) => (
            <button
              key={mode}
              onClick={() => setGridMode(mode as 1 | 2 | 3)}
              className={`px-4 py-2 rounded-md transition-colors flex items-center gap-2 ${
                gridMode === mode
                  ? 'bg-accent text-white'
                  : 'text-muted hover:text-text'
              }`}
            >
              <MdGridView />
              <span>{mode}x{mode}</span>
            </button>
          ))}
        </div>
      </div>

      {/* No Cameras */}
      {liveCameras.length === 0 && (
        <div className="bg-surface1 border border-border rounded-lg p-12 text-center">
          <p className="text-muted mb-4">{t('noCameras')}</p>
          <Link
            to="/settings"
            className="inline-block px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
          >
            {t('add')} {t('camera')}
          </Link>
        </div>
      )}

      {/* Camera Grid */}
      {liveCameras.length > 0 && (
        <div className={`grid ${getGridClass()} gap-6`}>
          {visibleCameras.map((camera) => {
            const stream = streams.find(s => s.camera_id === camera.id)
            // Use axios baseURL to get Ingress prefix
            const baseURL = apiClient.defaults.baseURL || '/api'
            const streamUrl = stream?.stream_url || `${baseURL}/live/${camera.id}.mjpeg`
            
            return (
              <StreamViewer
                key={camera.id}
                cameraId={camera.id}
                cameraName={camera.name}
                streamUrl={streamUrl}
                status={camera.status}
              />
            )
          })}
        </div>
      )}

      {liveCameras.length > visibleCount && (
        <div className="mt-6 flex justify-center">
          <button
            onClick={() => setVisibleCount((prev) => prev + 6)}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors"
          >
            {t('loadMore')}
          </button>
        </div>
      )}

      {/* Stream Mode Info */}
      <div className="mt-8 bg-surface1 border border-border rounded-lg p-4">
        <p className="text-muted text-sm">
          <span className="font-semibold text-text">Stream Modu:</span> {outputMode.toUpperCase()}
          {outputMode === 'webrtc' && (
            <span className="ml-2 text-yellow-500">
              (WebRTC aktif - go2rtc gerekli)
            </span>
          )}
        </p>
      </div>
    </div>
  )
}
