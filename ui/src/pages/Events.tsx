import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { MdDownload, MdPlayArrow } from 'react-icons/md'

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

export function Events() {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setLoading(true)
        const data = await api.getEvents({ page, page_size: pageSize })
        setEvents(data.events)
        setTotal(data.total)
      } catch (error) {
        console.error('Failed to fetch events:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchEvents()
  }, [page])

  const totalPages = Math.ceil(total / pageSize)

  if (loading && events.length === 0) {
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
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text mb-2">Olaylar</h1>
        <p className="text-muted">Toplam {total} olay kaydedildi</p>
      </div>

      {/* No Events */}
      {events.length === 0 && (
        <div className="bg-surface1 border border-border rounded-lg p-12 text-center">
          <p className="text-muted">Henüz olay kaydı yok</p>
        </div>
      )}

      {/* Events List */}
      {events.length > 0 && (
        <div className="space-y-4">
          {events.map((event) => (
            <div
              key={event.id}
              className="bg-surface1 border border-border rounded-lg p-6 hover:border-accent transition-colors"
            >
              <div className="flex gap-6">
                {/* Collage Thumbnail */}
                <div className="flex-shrink-0 w-48 h-32 bg-surface2 rounded-lg overflow-hidden">
                  <img
                    src={event.collage_url}
                    alt="Event collage"
                    className="w-full h-full object-cover"
                  />
                </div>

                {/* Event Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="text-lg font-semibold text-text mb-1">
                        Kamera: {event.camera_id}
                      </h3>
                      <p className="text-muted text-sm">
                        {new Date(event.timestamp).toLocaleString('tr-TR')}
                      </p>
                    </div>
                    <span className="px-3 py-1 bg-accent/20 text-accent rounded-full text-sm font-medium">
                      {Math.round(event.confidence * 100)}%
                    </span>
                  </div>

                  {/* AI Summary */}
                  {event.summary && (
                    <p className="text-text text-sm mb-4 line-clamp-2">
                      {event.summary}
                    </p>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3">
                    <a
                      href={event.gif_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm"
                    >
                      <MdPlayArrow />
                      GIF Önizle
                    </a>
                    <a
                      href={event.mp4_url}
                      download
                      className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm"
                    >
                      <MdDownload />
                      MP4 İndir
                    </a>
                  </div>
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
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Önceki
          </button>
          
          <span className="px-4 py-2 text-muted">
            Sayfa {page} / {totalPages}
          </span>
          
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Sonraki
          </button>
        </div>
      )}
    </div>
  )
}
