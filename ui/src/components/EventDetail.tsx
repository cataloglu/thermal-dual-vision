import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { MdClose, MdDownload, MdDelete, MdMovieFilter } from 'react-icons/md'
import { api, resolveApiPath } from '../services/api'

interface EventDetailProps {
  event: {
    id: string
    camera_id: string
    timestamp: string
    confidence: number
    event_type: string
    summary: string | null
    collage_url: string | null
    mp4_url: string | null
  }
  cameraName?: string
  initialTab?: 'collage' | 'video'
  onClose: () => void
  onDelete?: (eventId: string) => void
}

export function EventDetail({ event, cameraName, initialTab, onClose, onDelete }: EventDetailProps) {
  const { t } = useTranslation()
  const [videoError, setVideoError] = useState(false)
  const navigate = useNavigate()
  const modalRef = useRef<HTMLDivElement>(null)
  const [displayEvent, setDisplayEvent] = useState(event)
  const isRecent = (value: string) => Date.now() - new Date(value).getTime() < 60000
  const mediaPending = (!displayEvent.collage_url || !displayEvent.mp4_url) && isRecent(displayEvent.timestamp)
  const collagePending = !displayEvent.collage_url && isRecent(displayEvent.timestamp)
  const mp4Pending = !displayEvent.mp4_url && isRecent(displayEvent.timestamp)

  useEffect(() => { setDisplayEvent(event); setVideoError(false) }, [event])

  useEffect(() => {
    // Poll until BOTH collage and mp4 are available (or event is older than 60s)
    if (!mediaPending || !displayEvent.id) return
    const poll = async () => {
      try {
        const res = await api.getEvent(displayEvent.id)
        const mp4 = (res as { media?: { mp4_url?: string }; mp4_url?: string }).media?.mp4_url
          ?? (res as { mp4_url?: string }).mp4_url
        const collage = (res as { media?: { collage_url?: string }; collage_url?: string }).media?.collage_url
          ?? (res as { collage_url?: string }).collage_url
        if (mp4 || collage) {
          setDisplayEvent((prev) => ({ ...prev, mp4_url: mp4 ?? prev.mp4_url, collage_url: collage ?? prev.collage_url }))
        }
      } catch {
        // ignore
      }
    }
    poll()
    const id = setInterval(poll, 3000)
    return () => clearInterval(id)
  }, [mediaPending, displayEvent.id])
  const [activeTab, setActiveTab] = useState<'collage' | 'video'>(
    initialTab ?? (displayEvent.mp4_url ? 'video' : 'collage')
  )
  const [tagInput, setTagInput] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [note, setNote] = useState('')

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

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab)
      return
    }
    setActiveTab(displayEvent.mp4_url ? 'video' : 'collage')
  }, [displayEvent.id, displayEvent.mp4_url, initialTab])

  useEffect(() => {
    const raw = localStorage.getItem('event_meta')
    if (!raw) return
    try {
      const meta = JSON.parse(raw) as Record<string, { tags: string[]; note: string }>
      const entry = meta[displayEvent.id]
      if (entry) {
        setTags(entry.tags || [])
        setNote(entry.note || '')
      }
    } catch {
      // ignore malformed storage
    }
  }, [displayEvent.id])

  const persistMeta = (nextTags: string[], nextNote: string) => {
    const raw = localStorage.getItem('event_meta')
    let meta: Record<string, { tags: string[]; note: string }> = {}
    try {
      meta = raw ? JSON.parse(raw) : {}
    } catch {
      meta = {}
    }

    // Evict entries with no data to prevent unbounded growth (quota protection)
    const MAX_ENTRIES = 200
    const keys = Object.keys(meta)
    if (keys.length >= MAX_ENTRIES) {
      // Remove entries that have no tags and no note first
      for (const k of keys) {
        if (meta[k].tags.length === 0 && !meta[k].note) {
          delete meta[k]
        }
      }
      // If still over limit, remove oldest keys (insertion order)
      const remaining = Object.keys(meta)
      if (remaining.length >= MAX_ENTRIES) {
        remaining.slice(0, remaining.length - MAX_ENTRIES + 1).forEach((k) => delete meta[k])
      }
    }

    if (nextTags.length === 0 && !nextNote) {
      delete meta[displayEvent.id]
    } else {
      meta[displayEvent.id] = { tags: nextTags, note: nextNote }
    }

    try {
      localStorage.setItem('event_meta', JSON.stringify(meta))
    } catch {
      // Quota exceeded — clear stale empty entries and retry once
      try {
        Object.keys(meta).forEach((k) => {
          if (meta[k].tags.length === 0 && !meta[k].note) delete meta[k]
        })
        localStorage.setItem('event_meta', JSON.stringify(meta))
      } catch {
        // give up silently
      }
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString(undefined, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const getConfidenceBadge = () => {
    const percentage = Math.round(displayEvent.confidence * 100)
    let colorClass = 'bg-gray-500/20 text-gray-500'
    
    if (displayEvent.confidence >= 0.7) {
      colorClass = 'bg-success/20 text-success'
    } else if (displayEvent.confidence >= 0.4) {
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
    if (!onDelete) return
    if (!window.confirm(`${t('delete')}?`)) return
    if (onDelete) {
      onDelete(displayEvent.id)
      onClose()
    }
  }

  const handleAddTag = () => {
    const trimmed = tagInput.trim()
    if (!trimmed) return
    if (tags.includes(trimmed)) return
    const next = [...tags, trimmed]
    setTags(next)
    setTagInput('')
    persistMeta(next, note)
  }

  const handleRemoveTag = (tag: string) => {
    const next = tags.filter((t) => t !== tag)
    setTags(next)
    persistMeta(next, note)
  }

  const handleNoteChange = (value: string) => {
    setNote(value)
    persistMeta(tags, value)
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
              {t('events')} {t('view')}
            </h2>
            <p className="text-muted text-sm">
              {formatDate(displayEvent.timestamp)}
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
              displayEvent.collage_url ? (
                <img
                  src={resolveApiPath(displayEvent.collage_url)}
                  alt="Event collage"
                  className="w-full h-auto"
                />
              ) : (
                <div className="p-8 text-center text-muted">
                  {collagePending ? t('processing') : t('noData')}
                </div>
              )
            )}
            {activeTab === 'video' && (
              displayEvent.mp4_url && !videoError ? (
                <div>
                  <video
                    key={displayEvent.mp4_url}
                    src={resolveApiPath(displayEvent.mp4_url)}
                    controls
                    autoPlay
                    loop
                    playsInline
                    muted
                    preload="auto"
                    className="w-full h-auto"
                    onError={() => setVideoError(true)}
                  >
                    Tarayıcınız video oynatmayı desteklemiyor.
                  </video>
                  <div className="p-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => { onClose(); navigate('/video-analysis', { state: { eventId: displayEvent.id } }); }}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface1 border border-border rounded-lg hover:bg-surface2 transition-colors"
                    >
                      <MdMovieFilter />
                      {t('analyze') || 'Analiz Et'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-muted">
                  {mp4Pending ? t('processing') : t('noData')}
                </div>
              )
            )}
          </div>

          {/* Event Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">{t('camera')}</h3>
              <p className="text-text font-medium">{cameraName ?? displayEvent.camera_id}</p>
            </div>

            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">{t('confidence')}</h3>
              <div>{getConfidenceBadge()}</div>
            </div>

            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">{t('events')}</h3>
              <p className="text-text font-medium capitalize">{displayEvent.event_type}</p>
            </div>

            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">ID</h3>
              <p className="text-text font-mono text-sm">{displayEvent.id}</p>
            </div>
          </div>

          {/* AI Summary */}
          {displayEvent.summary && (
            <div className="bg-surface2 border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold text-muted mb-2">AI</h3>
              <p className="text-text">{displayEvent.summary}</p>
            </div>
          )}

          {/* Tags & Notes */}
          <div className="bg-surface2 border border-border rounded-lg p-4 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-muted mb-2">{t('tags')}</h3>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAddTag()
                  }}
                  placeholder={t('addTag')}
                  className="flex-1 px-3 py-2 bg-surface1 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
                />
                <button
                  onClick={handleAddTag}
                  className="px-3 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface1/80 transition-colors"
                >
                  {t('add')}
                </button>
              </div>
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 bg-surface1 border border-border text-text rounded-lg text-sm flex items-center gap-2"
                    >
                      {tag}
                      <button onClick={() => handleRemoveTag(tag)} className="text-error">
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-muted mb-2">{t('notes')}</h3>
              <textarea
                value={note}
                onChange={(e) => handleNoteChange(e.target.value)}
                placeholder={t('addNote')}
                rows={3}
                className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
            <p className="text-xs text-muted mt-2 italic">{t('localStorageNote')}</p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-border">
            {displayEvent.collage_url ? (
              <a
                href={resolveApiPath(displayEvent.collage_url)}
                download
                className="flex items-center gap-2 px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors font-medium"
              >
                <MdDownload />
                Collage
              </a>
            ) : (
              <span className="flex items-center gap-2 px-6 py-3 bg-accent/40 text-white rounded-lg opacity-60 font-medium">
                <MdDownload />
                Collage
              </span>
            )}
            {displayEvent.mp4_url ? (
              <a
                href={resolveApiPath(displayEvent.mp4_url)}
                download
                className="flex items-center gap-2 px-6 py-3 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors"
              >
                <MdDownload />
                MP4
              </a>
            ) : (
              <span className="flex items-center gap-2 px-6 py-3 bg-surface2 border border-border text-muted rounded-lg opacity-60">
                <MdDownload />
                MP4
              </span>
            )}

            {onDelete && (
              <button
                onClick={handleDelete}
                className="flex items-center gap-2 px-6 py-3 bg-error/20 text-error border border-error/50 rounded-lg hover:bg-error/30 transition-colors ml-auto"
              >
                <MdDelete />
                {t('delete')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
