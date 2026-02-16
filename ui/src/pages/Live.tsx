import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { StreamViewer } from '../components/StreamViewer'
import { api } from '../services/api'
import { MdRefresh, MdVideocam } from 'react-icons/md'
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

const LIVE_SELECTED_KEY = 'live_selected_camera_id'

export function Live() {
  const { t } = useTranslation()
  const [cameras, setCameras] = useState<Camera[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(() =>
    typeof localStorage !== 'undefined' ? localStorage.getItem(LIVE_SELECTED_KEY) : null
  )
  const [refreshKey, setRefreshKey] = useState(0)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const camerasData = await api.getCameras()
      setCameras(camerasData.cameras)
    } catch (error) {
      console.error('Failed to fetch live data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    const onVisible = () => {
      if (!document.hidden) {
        fetchData()
        setRefreshKey(k => k + 1)
      }
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [fetchData])

  const handleStatus = useCallback((data: any) => {
    if (!data?.camera_id) return
    setCameras((prev) =>
      prev.map((cam) =>
        cam.id === data.camera_id ? { ...cam, status: data.status } : cam
      )
    )
  }, [])

  useWebSocket('/api/ws/events', { onStatus: handleStatus })

  const liveCameras = cameras.filter(
    (cam) => cam.enabled && (cam.stream_roles ?? ['detect', 'live']).includes('live')
  )

  const selectedCamera = selectedId
    ? liveCameras.find((c) => c.id === selectedId)
    : liveCameras[0] ?? null

  const handleSelect = (cameraId: string) => {
    setSelectedId(cameraId)
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(LIVE_SELECTED_KEY, cameraId)
    }
    setRefreshKey((k) => k + 1)
  }

  if (loading) {
    return <LoadingState variant="list" listCount={2} />
  }

  return (
    <div className="p-8">
      <div className="flex flex-col gap-6 max-w-4xl mx-auto">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-text mb-2">{t('live')}</h1>
            <p className="text-muted">
              {t('liveSingleCameraDesc')}
            </p>
          </div>
          <button
            onClick={() => {
              fetchData()
              setRefreshKey((k) => k + 1)
            }}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors flex items-center gap-2"
          >
            <MdRefresh />
            {t('refresh')}
          </button>
        </div>

        {liveCameras.length === 0 ? (
          <div className="bg-surface1 border border-border rounded-lg p-12 text-center">
            <p className="text-muted mb-4">{t('noCameras')}</p>
            <Link
              to="/settings"
              className="inline-block px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
            >
              {t('add')} {t('camera')}
            </Link>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-sm text-muted flex items-center gap-2">
                <MdVideocam />
                {t('selectCamera')}
              </label>
              <select
                value={selectedCamera?.id ?? ''}
                onChange={(e) => handleSelect(e.target.value)}
                className="px-4 py-2 bg-surface1 border border-border rounded-lg text-text min-w-[200px]"
              >
                {liveCameras.map((cam) => (
                  <option key={cam.id} value={cam.id}>
                    {cam.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="rounded-lg overflow-hidden border border-border bg-surface2">
              {selectedCamera && (
                <StreamViewer
                  key={`${selectedCamera.id}-${refreshKey}`}
                  cameraId={selectedCamera.id}
                  cameraName={selectedCamera.name}
                  status={selectedCamera.status}
                  loadStream={true}
                />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
