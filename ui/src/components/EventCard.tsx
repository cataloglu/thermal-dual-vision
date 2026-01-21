import { memo } from 'react'
import { useTranslation } from 'react-i18next'
import { MdPlayArrow, MdDownload, MdVisibility } from 'react-icons/md'

interface EventCardProps {
  id: string
  cameraId: string
  timestamp: string
  confidence: number
  summary: string | null
  collageUrl: string | null
  gifUrl: string | null
  mp4Url: string | null
  selected?: boolean
  onSelect?: (id: string) => void
  onClick: (id: string) => void
}

export const EventCard = memo(function EventCard({
  id,
  cameraId,
  timestamp,
  confidence,
  summary,
  collageUrl,
  gifUrl,
  mp4Url,
  selected = false,
  onSelect,
  onClick,
}: EventCardProps) {
  const { t } = useTranslation()
  const isRecent = (value: string) => Date.now() - new Date(value).getTime() < 30000
  const collagePending = !collageUrl && isRecent(timestamp)
  const getConfidenceBadge = () => {
    const percentage = Math.round(confidence * 100)
    let colorClass = 'bg-gray-500/20 text-gray-500'
    
    if (confidence >= 0.7) {
      colorClass = 'bg-success/20 text-success'
    } else if (confidence >= 0.4) {
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
    <div className="bg-surface1 border border-border rounded-lg overflow-hidden hover:bg-surface2 hover:border-accent transition-all group">
      <div className="flex gap-4 p-4">
        {/* Collage Thumbnail */}
        <div 
          className="flex-shrink-0 w-48 h-36 bg-surface2 rounded-lg overflow-hidden cursor-pointer"
          onClick={() => onClick(id)}
        >
          {collageUrl ? (
            <img
              src={collageUrl}
              alt="Event collage"
              loading="lazy"
              decoding="async"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xs text-muted">
              {collagePending ? t('processing') : t('noData')}
            </div>
          )}
        </div>

        {/* Event Info */}
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-text mb-1 truncate">
                {t('camera')}: {cameraId}
              </h3>
              <p className="text-muted text-sm">
                {formatDate(timestamp)}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {onSelect && (
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={(e) => {
                    e.stopPropagation()
                    onSelect(id)
                  }}
                  className="w-4 h-4 accent-accent"
                  aria-label={t('select')}
                />
              )}
              {getConfidenceBadge()}
            </div>
          </div>

          {/* AI Summary */}
          {summary && (
            <p className="text-text text-sm mb-4 line-clamp-2 flex-1">
              {summary}
            </p>
          )}

          {/* Actions */}
          <div className="flex gap-2 mt-auto">
            <button
              onClick={() => onClick(id)}
              className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors text-sm font-medium"
            >
              <MdVisibility />
              {t('view')}
            </button>
            {gifUrl ? (
              <a
                href={gifUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm"
              >
                <MdPlayArrow />
                GIF
              </a>
            ) : (
              <span className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-muted rounded-lg text-sm opacity-60">
                <MdPlayArrow />
                GIF
              </span>
            )}
            {mp4Url ? (
              <a
                href={mp4Url}
                download
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm"
              >
                <MdDownload />
                MP4
              </a>
            ) : (
              <span className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-muted rounded-lg text-sm opacity-60">
                <MdDownload />
                MP4
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
})
