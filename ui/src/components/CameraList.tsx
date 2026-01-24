import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { MdEdit, MdDelete, MdAdd, MdCheckCircle, MdError, MdWarning } from 'react-icons/md'
import { api } from '../services/api'
import toast from 'react-hot-toast'

interface Camera {
  id: string
  name: string
  type: string
  enabled: boolean
  status: string
  rtsp_url_thermal?: string
  rtsp_url_color?: string
  detection_source: string
  stream_roles: string[]
}

interface CameraListProps {
  onAdd: () => void
  onEdit: (camera: Camera) => void
  onRefresh?: () => void
}

export function CameraList({ onAdd, onEdit, onRefresh }: CameraListProps) {
  const { t } = useTranslation()
  const [cameras, setCameras] = useState<Camera[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const fetchCameras = async () => {
    try {
      const data = await api.getCameras()
      setCameras(data.cameras || [])
    } catch (error) {
      console.error('Failed to fetch cameras:', error)
      toast.error('Kameralar yüklenemedi')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCameras()
  }, [])

  const handleDelete = async (cameraId: string) => {
    try {
      await api.deleteCamera(cameraId)
      toast.success('Kamera silindi')
      setCameras((prev) => prev.filter((cam) => cam.id !== cameraId))
      if (onRefresh) onRefresh()
    } catch (error) {
      console.error('Failed to delete camera:', error)
      toast.error('Kamera silinemedi')
    } finally {
      setDeleteConfirm(null)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <MdCheckCircle className="text-green-500" />
      case 'retrying':
        return <MdWarning className="text-yellow-500" />
      case 'initializing':
        return <MdWarning className="text-blue-500" />
      default:
        return <MdError className="text-red-500" />
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'connected':
        return t('connected')
      case 'retrying':
        return t('retrying')
      case 'down':
        return t('down')
      case 'initializing':
        return t('initializing')
      default:
        return t('loading')
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <div key={i} className="h-24 bg-surface1 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-text">{t('cameras')}</h3>
        <button
          onClick={onAdd}
          className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
        >
          <MdAdd className="text-xl" />
          {t('add')}
        </button>
      </div>

      {/* No Cameras */}
      {cameras.length === 0 && (
        <div className="bg-surface1 border border-border rounded-lg p-8 text-center">
          <p className="text-muted mb-4">{t('noCameras')}</p>
          <button
            onClick={onAdd}
            className="px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
          >
            {t('add')} {t('camera')}
          </button>
        </div>
      )}

      {/* Camera List */}
      {cameras.map((camera) => (
        <div
          key={camera.id}
          className="bg-surface1 border border-border rounded-lg p-4 hover:border-accent transition-colors"
        >
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h4 className="text-lg font-semibold text-text">{camera.name}</h4>
                <span className="px-2 py-1 bg-surface2 text-muted text-xs rounded">
                  {camera.type.toUpperCase()}
                </span>
                <div className="flex items-center gap-1">
                  {getStatusIcon(camera.status)}
                  <span className="text-sm text-muted">{getStatusLabel(camera.status)}</span>
                </div>
              </div>
              
              <div className="flex items-center gap-4 text-sm text-muted">
                <span>{camera.detection_source}</span>
                <span>{camera.stream_roles.join(', ')}</span>
                <span className={camera.enabled ? 'text-green-500' : 'text-red-500'}>
                  {camera.enabled ? t('enabled') : t('disabled')}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => onEdit(camera)}
                className="p-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors"
              >
                <MdEdit className="text-lg" />
              </button>
              
              {deleteConfirm === camera.id ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleDelete(camera.id)}
                    className="px-3 py-2 bg-error text-white rounded-lg hover:bg-error/90 transition-colors text-sm"
                  >
                    {t('delete')}
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    className="px-3 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm"
                  >
                    {t('cancel')}
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setDeleteConfirm(camera.id)}
                  className="p-2 bg-error/20 border border-error/50 text-error rounded-lg hover:bg-error/30 transition-colors"
                >
                  <MdDelete className="text-lg" />
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
