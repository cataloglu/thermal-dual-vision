import { useState, useEffect } from 'react'
import { EventCard } from '../components/EventCard'
import { EventDetail } from '../components/EventDetail'
import { useEvents } from '../hooks/useEvents'
import { api } from '../services/api'
import { MdFilterList, MdClear } from 'react-icons/md'
import toast from 'react-hot-toast'

interface Camera {
  id: string
  name: string
}

export function Events() {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [cameras, setCameras] = useState<Camera[]>([])
  const [showFilters, setShowFilters] = useState(false)
  
  // Filter states
  const [cameraFilter, setCameraFilter] = useState<string>('')
  const [dateFilter, setDateFilter] = useState<string>('')
  const [confidenceFilter, setConfidenceFilter] = useState<number>(0)

  // Fetch events with filters
  const { 
    events, 
    loading, 
    error, 
    total, 
    page, 
    totalPages, 
    nextPage, 
    prevPage 
  } = useEvents({
    cameraId: cameraFilter || undefined,
    date: dateFilter || undefined,
    minConfidence: confidenceFilter > 0 ? confidenceFilter / 100 : undefined,
  })

  // Fetch cameras for filter dropdown
  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const data = await api.getCameras()
        setCameras(data.cameras || [])
      } catch (error) {
        console.error('Failed to fetch cameras:', error)
      }
    }
    fetchCameras()
  }, [])

  const selectedEvent = events.find(e => e.id === selectedEventId)

  const handleClearFilters = () => {
    setCameraFilter('')
    setDateFilter('')
    setConfidenceFilter(0)
  }

  const hasActiveFilters = cameraFilter || dateFilter || confidenceFilter > 0

  const handleDeleteEvent = async (_eventId: string) => {
    try {
      // TODO: Implement delete API call when backend is ready
      // await api.deleteEvent(eventId)
      toast.success('Event silindi')
      setSelectedEventId(null)
      // Refresh events list
      window.location.reload()
    } catch (error) {
      toast.error('Event silinemedi')
      console.error('Failed to delete event:', error)
    }
  }

  if (loading && events.length === 0) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-surface1 rounded w-48" />
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-40 bg-surface1 rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-error/10 border border-error/50 rounded-lg p-6 text-center">
          <p className="text-error mb-4">Events yüklenirken hata oluştu</p>
          <p className="text-muted text-sm">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text mb-2">Olaylar</h1>
          <p className="text-muted">
            {total > 0 ? `Toplam ${total} olay kaydedildi` : 'Henüz olay kaydı yok'}
          </p>
        </div>

        {/* Filter Toggle */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            showFilters || hasActiveFilters
              ? 'bg-accent text-white'
              : 'bg-surface1 border border-border text-text hover:bg-surface2'
          }`}
        >
          <MdFilterList className="text-xl" />
          Filtrele
          {hasActiveFilters && (
            <span className="ml-1 px-2 py-0.5 bg-white/20 rounded-full text-xs">
              Aktif
            </span>
          )}
        </button>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-surface1 border border-border rounded-lg p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Camera Filter */}
            <div>
              <label className="block text-sm font-medium text-muted mb-2">
                Kamera
              </label>
              <select
                value={cameraFilter}
                onChange={(e) => setCameraFilter(e.target.value)}
                className="w-full px-4 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:border-accent"
              >
                <option value="">Tüm Kameralar</option>
                {cameras.map((camera) => (
                  <option key={camera.id} value={camera.id}>
                    {camera.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Date Filter */}
            <div>
              <label className="block text-sm font-medium text-muted mb-2">
                Tarih
              </label>
              <input
                type="date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="w-full px-4 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:border-accent"
              />
            </div>

            {/* Confidence Filter */}
            <div>
              <label className="block text-sm font-medium text-muted mb-2">
                Minimum Güven: {confidenceFilter}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={confidenceFilter}
                onChange={(e) => setConfidenceFilter(Number(e.target.value))}
                className="w-full h-2 bg-surface2 rounded-lg appearance-none cursor-pointer accent-accent"
              />
            </div>
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <div className="mt-4 pt-4 border-t border-border">
              <button
                onClick={handleClearFilters}
                className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm"
              >
                <MdClear />
                Filtreleri Temizle
              </button>
            </div>
          )}
        </div>
      )}

      {/* No Events */}
      {events.length === 0 && !loading && (
        <div className="bg-surface1 border border-border rounded-lg p-12 text-center">
          <p className="text-muted mb-4">
            {hasActiveFilters 
              ? 'Filtre kriterlerine uygun olay bulunamadı' 
              : 'Henüz olay kaydı yok'}
          </p>
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
            >
              Filtreleri Temizle
            </button>
          )}
        </div>
      )}

      {/* Events List */}
      {events.length > 0 && (
        <div className="space-y-4">
          {events.map((event) => (
            <EventCard
              key={event.id}
              id={event.id}
              cameraId={event.camera_id}
              timestamp={event.timestamp}
              confidence={event.confidence}
              summary={event.summary}
              collageUrl={event.collage_url}
              gifUrl={event.gif_url}
              mp4Url={event.mp4_url}
              onClick={() => setSelectedEventId(event.id)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            onClick={prevPage}
            disabled={page === 1}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Önceki
          </button>
          
          <div className="flex items-center gap-2">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum: number
              if (totalPages <= 5) {
                pageNum = i + 1
              } else if (page <= 3) {
                pageNum = i + 1
              } else if (page >= totalPages - 2) {
                pageNum = totalPages - 4 + i
              } else {
                pageNum = page - 2 + i
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => {
                    // Page change handled by useEvents hook
                    window.scrollTo({ top: 0, behavior: 'smooth' })
                  }}
                  className={`w-10 h-10 rounded-lg transition-colors ${
                    page === pageNum
                      ? 'bg-accent text-white'
                      : 'bg-surface1 border border-border text-text hover:bg-surface2'
                  }`}
                >
                  {pageNum}
                </button>
              )
            })}
          </div>
          
          <button
            onClick={nextPage}
            disabled={page === totalPages}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Sonraki
          </button>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && events.length > 0 && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-40">
          <div className="bg-surface1 border border-border rounded-lg p-6">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-accent border-t-transparent mx-auto" />
          </div>
        </div>
      )}

      {/* Event Detail Modal */}
      {selectedEvent && (
        <EventDetail
          event={selectedEvent}
          onClose={() => setSelectedEventId(null)}
          onDelete={handleDeleteEvent}
        />
      )}
    </div>
  )
}
