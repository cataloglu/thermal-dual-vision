import { useEffect, useRef, useState } from 'react'
import { MdClose, MdDownload, MdDelete } from 'react-icons/md'

interface EventDetailProps {
  event: {
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
  onClose: () => void
  onDelete?: (eventId: string) => void
}

export function EventDetail({ event, onClose, onDelete }: EventDetailProps) {
  const modalRef = useRef<HTMLDivElement>(null)
  const [activeTab, setActiveTab] = useState<'collage' | 'gif' | 'video'>('collage')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    document.addEventListener('mousedown', handleClickOutside)
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.removeEventListener('mousedown', handleClickOutside)
      document.body.style.overflow = 'unset'
    }
  }, [onClose])

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const getConfidenceBadge = () => {
    const percentage = Math.round(event.confidence * 100)
    let colorClass = 'bg-gray-500/20 text-gray-500'
    
    if (event.confidence >= 0.7) {
      colorClass = 'bg-success/20 text-success'
    } else if (event.confidence >= 0.4) {
      colorClass = 'bg-warning/20 text-warning'
    } else {
      colorClass = 'bg-error/20 text-error'
    }
    
    return (
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${colorClass}`}>
        {percentage}%
      </span>
    )
  }

  const handleDelete = () => {
    if (onDelete) {
      onDelete(event.id)
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div
        ref={modalRef}
        className="bg-surface1 border border-border rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="sticky top-0 bg-surface1 border-b border-border p-6 flex items-center justify-between z-10">
          <div>
            <h2 className="text-2xl font-bold text-text mb-1">
              Event Detayı
            </h2>
            <p className="text-muted text-sm">
              {formatDate(event.timestamp)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface2 rounded-lg transition-colors"
          >
            <MdClose className="text-2xl text-muted" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Tabs */}
          <div className="flex gap-2 border-b border-border">
            <button
              onClick={() => setActiveTab('collage')}
              className={`px-4 py-2 font-medium transition-colors border-b-2 ${
                activeTab === 'collage'
                  ? 'border-accent text-accent'
                  : 'border-transparent text-muted hover:text-text'
              }`}
            >
              Collage
            </button>
            <button
              onClick={() => setActiveTab('gif')}
              className={`px-4 py-2 font-medium transition-colors border-b-2 ${
                activeTab === 'gif'
                  ? 'border-accent text-accent'
                  : 'border-transparent text-muted hover:text-text'
              }`}
            >
              GIF Önizleme
            </button>
            <button
              onClick={() => setActiveTab('video')}
              className={`px-4 py-2 font-medium transition-colors border-b-2 ${
                activeTab === 'video'
                  ? 'border-accent text-accent'
                  : 'border-transparent text-muted hover:text-text'
              }`}
            >
              Video
            </button>
          </div>

          {/* Media Preview */}
          <div className="bg-surface2 rounded-lg overflow-hidden">
            {activeTab === 'collage' && (
              <img
                src={event.collage_url}
                alt="Event collage"
                className="w-full h-auto"
              />
            )}
            {activeTab === 'gif' && (
              <img
                src={event.gif_url}
                alt="Event GIF"
                className="w-full h-auto"
              />
            )}
            {activeTab === 'video' && (
              <video
                src={event.mp4_url}
                controls
                autoPlay
                loop
                className="w-full h-auto"
              >
                Tarayıcınız video oynatmayı desteklemiyor.
              </video>
            )}
          </div>

          {/* Event Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">Kamera</h3>
              <p className="text-text font-medium">{event.camera_id}</p>
            </div>

            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">Güven Skoru</h3>
              <div>{getConfidenceBadge()}</div>
            </div>

            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">Event Tipi</h3>
              <p className="text-text font-medium capitalize">{event.event_type}</p>
            </div>

            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">Event ID</h3>
              <p className="text-text font-mono text-sm">{event.id}</p>
            </div>
          </div>

          {/* AI Summary */}
          {event.summary && (
            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">AI Özeti</h3>
              <p className="text-text">{event.summary}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-border">
            <a
              href={event.collage_url}
              download
              className="flex items-center gap-2 px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors font-medium"
            >
              <MdDownload />
              Collage İndir
            </a>
            <a
              href={event.gif_url}
              download
              className="flex items-center gap-2 px-6 py-3 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors"
            >
              <MdDownload />
              GIF İndir
            </a>
            <a
              href={event.mp4_url}
              download
              className="flex items-center gap-2 px-6 py-3 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors"
            >
              <MdDownload />
              MP4 İndir
            </a>

            {onDelete && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="flex items-center gap-2 px-6 py-3 bg-error/20 text-error border border-error/50 rounded-lg hover:bg-error/30 transition-colors ml-auto"
              >
                <MdDelete />
                Sil
              </button>
            )}
          </div>

          {/* Delete Confirmation */}
          {showDeleteConfirm && (
            <div className="bg-error/10 border border-error/50 rounded-lg p-4">
              <p className="text-text mb-4">
                Bu eventi silmek istediğinize emin misiniz? Bu işlem geri alınamaz.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 bg-error text-white rounded-lg hover:bg-error/90 transition-colors font-medium"
                >
                  Evet, Sil
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors"
                >
                  İptal
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
