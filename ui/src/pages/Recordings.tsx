import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { MdPlayArrow, MdDownload, MdDelete, MdFilterList } from 'react-icons/md'
import toast from 'react-hot-toast'

interface Recording {
  id: string
  camera_id: string
  start_time: string
  end_time: string
  duration_seconds: number
  file_size_mb: number
  file_path: string
}

export function Recordings() {
  const { t } = useTranslation()
  const [recordings, setRecordings] = useState<Recording[]>([])
  const [cameras, setCameras] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showFilters, setShowFilters] = useState(false)
  
  // Filters
  const [cameraFilter, setCameraFilter] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20

  useEffect(() => {
    fetchRecordings()
    fetchCameras()
  }, [page, cameraFilter, startDate, endDate])

  const fetchRecordings = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        ...(cameraFilter && { camera_id: cameraFilter }),
        ...(startDate && { start_date: startDate }),
        ...(endDate && { end_date: endDate }),
      })
      
      const response = await fetch(`/api/recordings?${params}`)
      const data = await response.json()
      setRecordings(data.recordings || [])
      setTotal(data.total || 0)
    } catch (error) {
      console.error('Failed to fetch recordings:', error)
      toast.error(t('failed'))
    } finally {
      setLoading(false)
    }
  }

  const fetchCameras = async () => {
    try {
      const response = await fetch('/api/cameras')
      const data = await response.json()
      setCameras(data.cameras || [])
    } catch (error) {
      console.error('Failed to fetch cameras:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm(t('delete') + '?')) return
    
    try {
      await fetch(`/api/recordings/${id}`, { method: 'DELETE' })
      toast.success(t('success'))
      fetchRecordings()
    } catch (error) {
      toast.error(t('failed'))
    }
  }

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const totalPages = Math.ceil(total / pageSize)

  if (loading && recordings.length === 0) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-surface1 rounded w-48" />
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-surface1 rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text mb-2">{t('recording')}</h1>
          <p className="text-muted">
            {total > 0 ? `${t('total')} ${total}` : t('noData')}
          </p>
        </div>

        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            showFilters ? 'bg-accent text-white' : 'bg-surface1 border border-border text-text hover:bg-surface2'
          }`}
        >
          <MdFilterList />
          {t('filter')}
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-surface1 border border-border rounded-lg p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-muted mb-2">{t('camera')}</label>
              <select
                value={cameraFilter}
                onChange={(e) => setCameraFilter(e.target.value)}
                className="w-full px-4 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:border-accent"
              >
                <option value="">{t('cameras')}</option>
                {cameras.map((cam) => (
                  <option key={cam.id} value={cam.id}>{cam.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-muted mb-2">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-4 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-muted mb-2">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-4 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>
          </div>
        </div>
      )}

      {/* No Recordings */}
      {recordings.length === 0 && !loading && (
        <div className="bg-surface1 border border-border rounded-lg p-12 text-center">
          <p className="text-muted">{t('noData')}</p>
        </div>
      )}

      {/* Recordings List */}
      {recordings.length > 0 && (
        <div className="space-y-4">
          {recordings.map((recording) => (
            <div
              key={recording.id}
              className="bg-surface1 border border-border rounded-lg p-6 hover:border-accent transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-text mb-1">
                    {t('camera')}: {recording.camera_id}
                  </h3>
                  <p className="text-muted text-sm">
                    {new Date(recording.start_time).toLocaleString()} - {new Date(recording.end_time).toLocaleString()}
                  </p>
                  <div className="flex gap-4 mt-2 text-sm text-muted">
                    <span>Duration: {formatDuration(recording.duration_seconds)}</span>
                    <span>Size: {recording.file_size_mb.toFixed(2)} MB</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
                  >
                    <MdPlayArrow />
                    {t('view')}
                  </button>
                  <a
                    href={recording.file_path}
                    download
                    className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors"
                  >
                    <MdDownload />
                    {t('download')}
                  </a>
                  <button
                    onClick={() => handleDelete(recording.id)}
                    className="flex items-center gap-2 px-4 py-2 bg-error/20 border border-error/50 text-error rounded-lg hover:bg-error/30 transition-colors"
                  >
                    <MdDelete />
                    {t('delete')}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50"
          >
            {t('previous')}
          </button>
          <span className="px-4 py-2 text-muted">
            {t('page')} {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50"
          >
            {t('next')}
          </button>
        </div>
      )}
    </div>
  )
}
