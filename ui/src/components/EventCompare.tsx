import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { MdClose } from 'react-icons/md'

interface EventCompareProps {
  left: {
    id: string
    camera_id: string
    timestamp: string
    confidence: number
    event_type: string
    collage_url: string
  }
  right: {
    id: string
    camera_id: string
    timestamp: string
    confidence: number
    event_type: string
    collage_url: string
  }
  onClose: () => void
}

export function EventCompare({ left, right, onClose }: EventCompareProps) {
  const { t } = useTranslation()
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [])

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-surface1 border border-border rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-surface1 border-b border-border p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-text">{t('compare')}</h2>
          <button onClick={onClose} className="p-2 hover:bg-surface2 rounded-lg transition-colors">
            <MdClose className="text-2xl text-muted" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
          {[left, right].map((event) => (
            <div key={event.id} className="space-y-3">
              <div className="bg-surface2 rounded-lg overflow-hidden">
                <img src={event.collage_url} alt="Event collage" className="w-full h-auto" />
              </div>
              <div className="bg-surface2 border border-border rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm text-muted">
                  <span>{t('camera')}</span>
                  <span className="text-text">{event.camera_id}</span>
                </div>
                <div className="flex justify-between text-sm text-muted">
                  <span>{t('timestamp')}</span>
                  <span className="text-text">{formatDate(event.timestamp)}</span>
                </div>
                <div className="flex justify-between text-sm text-muted">
                  <span>{t('confidence')}</span>
                  <span className="text-text">{Math.round(event.confidence * 100)}%</span>
                </div>
                <div className="flex justify-between text-sm text-muted">
                  <span>{t('events')}</span>
                  <span className="text-text">{event.event_type}</span>
                </div>
                <div className="text-xs text-muted break-all">
                  {event.id}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
