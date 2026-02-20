import { useCallback, useMemo, useRef, useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { EventCard } from '../components/EventCard'
import { EventDetail } from '../components/EventDetail'
import { EventCompare } from '../components/EventCompare'
import { useEvents } from '../hooks/useEvents'
import { api } from '../services/api'
import { MdFilterList, MdClear, MdDownload, MdDelete } from 'react-icons/md'
import toast from 'react-hot-toast'
import { useWebSocket } from '../hooks/useWebSocket'
import { useDebounce } from '../hooks/useDebounce'
import { LoadingState } from '../components/LoadingState'
import { safeGetItem, safeSetItem } from '../utils/safeStorage'

interface Camera {
  id: string
  name: string
}

export function Events() {
  const { t } = useTranslation()
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [selectedEventTab, setSelectedEventTab] = useState<'collage' | 'video' | null>(null)
  const [cameras, setCameras] = useState<Camera[]>([])
  const [showFilters, setShowFilters] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [compareOpen, setCompareOpen] = useState(false)
  const [deleteAllLoading, setDeleteAllLoading] = useState(false)
  
  // Filter states
  const [cameraFilter, setCameraFilter] = useState<string>('')
  const [dateFilter, setDateFilter] = useState<string>('')
  const [confidenceFilter, setConfidenceFilter] = useState<number>(0)
  const [confidenceInput, setConfidenceInput] = useState<number>(0)
  const [showRejected, setShowRejected] = useState(false)

  // Fetch events with filters
  const debouncedCameraFilter = useDebounce(cameraFilter, 300)
  const debouncedDateFilter = useDebounce(dateFilter, 300)
  const debouncedConfidenceFilter = useDebounce(confidenceFilter, 300)

  const { 
    events, 
    loading, 
    error, 
    total, 
    page, 
    pageSize,
    totalPages, 
    nextPage, 
    prevPage,
    goToPage,
    refresh,
    resetPage,
    prependEvent,
    setPageSize,
  } = useEvents({
    cameraId: debouncedCameraFilter || undefined,
    date: debouncedDateFilter || undefined,
    minConfidence: debouncedConfidenceFilter > 0 ? debouncedConfidenceFilter / 100 : undefined,
    rejected: showRejected ? true : undefined,
  })

  // handleEvent ref avoids WS reconnect when filters change (useWebSocket stores callbacks in refs)
  const handleEventRef = useRef<(data: any) => void>(() => {})
  handleEventRef.current = useCallback((data: any) => {
    if (cameraFilter || dateFilter || confidenceFilter > 0) return
    const isRejected = Boolean(data?.rejected_by_ai)
    if (showRejected && !isRejected) return
    if (!showRejected && isRejected) return
    prependEvent(data)
  }, [cameraFilter, dateFilter, confidenceFilter, showRejected, prependEvent])

  const wsOptions = useMemo(() => ({
    onEvent: (data: any) => handleEventRef.current(data),
  }), [])  // stable reference — callback forwarded via ref

  useWebSocket('/api/ws/events', wsOptions)

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

  useEffect(() => {
    resetPage()
  }, [debouncedCameraFilter, debouncedDateFilter, debouncedConfidenceFilter, showRejected, resetPage])

  useEffect(() => {
    setSelectedIds(new Set())
  }, [debouncedCameraFilter, debouncedDateFilter, debouncedConfidenceFilter, showRejected, page, pageSize])

  useEffect(() => {
    const saved = safeGetItem('events_filters_open')
    if (saved) {
      setShowFilters(saved === 'true')
    }
  }, [])

  useEffect(() => {
    safeSetItem('events_filters_open', String(showFilters))
  }, [showFilters])

  const selectedEvent = events.find(e => e.id === selectedEventId)

  const cameraNameById = useMemo(() => {
    const map = new Map<string, string>()
    cameras.forEach((camera) => {
      map.set(camera.id, camera.name)
    })
    return map
  }, [cameras])

  const handleClearFilters = () => {
    setCameraFilter('')
    setDateFilter('')
    setConfidenceFilter(0)
    setConfidenceInput(0)
  }

  const handleSelect = useCallback((eventId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(eventId)) {
        next.delete(eventId)
      } else {
        next.add(eventId)
      }
      return next
    })
  }, [])

  const handleOpen = useCallback((eventId: string, tab?: 'collage' | 'video') => {
    setSelectedEventId(eventId)
    setSelectedEventTab(tab ?? null)
  }, [])
  const commitConfidence = useCallback(() => {
    setConfidenceFilter(confidenceInput)
  }, [confidenceInput])

  const hasActiveFilters = Boolean(cameraFilter || dateFilter || confidenceFilter > 0)

  const handleDeleteEvent = async (eventId: string) => {
    try {
      await api.deleteEvent(eventId)
      toast.success(t('eventDeleted'))
      setSelectedEventId(null)
      // Refresh events list
      refresh()
    } catch (error) {
      toast.error(t('deleteEventFailed'))
      console.error('Failed to delete event:', error)
    }
  }

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return
    const ids = Array.from(selectedIds)
    try {
      const result = await api.bulkDeleteEvents(ids)
      const deletedCount = result?.deleted_count ?? ids.length
      toast.success(t('deleteAllSuccess', { count: deletedCount }))
      setSelectedIds(new Set())
      refresh()
    } catch (error) {
      toast.error(t('deleteAllFailed'))
    }
  }

  const handleDeleteAll = async () => {
    if (deleteAllLoading) return
    const confirmText = t('deleteAllConfirmAll')
    if (!window.confirm(confirmText)) return

    try {
      setDeleteAllLoading(true)
      const result = await api.deleteEventsFiltered({})
      const deletedCount = result?.deleted_count ?? 0
      toast.success(
        t('deleteAllSuccess', { count: deletedCount })
      )
      setSelectedIds(new Set())
      resetPage()
      refresh()
    } catch (error) {
      toast.error(t('deleteAllFailed'))
    } finally {
      setDeleteAllLoading(false)
    }
  }

  const handleExport = (format: 'json' | 'csv') => {
    if (events.length === 0) return
    const filename = `events-${new Date().toISOString().slice(0, 10)}.${format}`
    let content = ''
    let mime = 'application/json'
    if (format === 'json') {
      content = JSON.stringify(events, null, 2)
    } else {
      const header = ['id', 'camera_id', 'timestamp', 'confidence', 'event_type', 'summary']
      const rows = events.map((e) => [
        e.id,
        e.camera_id,
        e.timestamp,
        e.confidence,
        e.event_type,
        e.summary ?? '',
      ])
      content = [header.join(','), ...rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))].join('\n')
      mime = 'text/csv'
    }
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  }

  const allSelected = useMemo(() => {
    if (events.length === 0) return false
    return events.every((event) => selectedIds.has(event.id))
  }, [events, selectedIds])

  const compareEvents = useMemo(() => {
    const ids = Array.from(selectedIds)
    if (ids.length !== 2) return null
    const left = events.find((event) => event.id === ids[0])
    const right = events.find((event) => event.id === ids[1])
    if (!left || !right) return null
    return { left, right }
  }, [events, selectedIds])

  const paginationItems = useMemo(() => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }
    const items: Array<number | '...'> = []
    items.push(1)
    if (page > 3) items.push('...')
    const start = Math.max(2, page - 1)
    const end = Math.min(totalPages - 1, page + 1)
    for (let i = start; i <= end; i += 1) {
      items.push(i)
    }
    if (page < totalPages - 2) items.push('...')
    items.push(totalPages)
    return items
  }, [page, totalPages])

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  if (loading && events.length === 0) {
    return <LoadingState variant="list" listCount={3} />
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
      {/* View tabs */}
      <div className="flex gap-2 mb-6 border-b border-border pb-2">
        <button
          onClick={() => setShowRejected(false)}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            !showRejected ? 'bg-accent text-white' : 'bg-surface1 text-muted hover:text-text'
          }`}
        >
          {t('eventsConfirmed')}
        </button>
        <button
          onClick={() => setShowRejected(true)}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            showRejected ? 'bg-accent text-white' : 'bg-surface1 text-muted hover:text-text'
          }`}
        >
          {t('eventsRejectedByAi')}
        </button>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-text mb-2">
            {showRejected ? t('eventsRejectedByAi') : t('events')}
          </h1>
          <p className="text-muted">
            {total > 0 ? `${t('total')} ${total} ${t('events').toLowerCase()}` : t('noEvents')}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {selectedIds.size > 0 && (
            <button
              onClick={handleBulkDelete}
              className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors bg-error text-white"
            >
              <MdDelete className="text-xl" />
              {t('deleteSelected')} ({selectedIds.size})
            </button>
          )}
          <button
            onClick={handleDeleteAll}
            disabled={deleteAllLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors bg-error/20 text-error border border-error/50 hover:bg-error/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <MdDelete className="text-xl" />
            {t('deleteAllEvents')}
          </button>
          <button
            onClick={() => setCompareOpen(true)}
            disabled={!compareEvents}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors bg-surface1 border border-border text-text hover:bg-surface2 disabled:opacity-50"
          >
            {t('compare')}
          </button>
          <button
            onClick={() => handleExport('json')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors bg-surface1 border border-border text-text hover:bg-surface2"
          >
            <MdDownload className="text-xl" />
            JSON
          </button>
          <button
            onClick={() => handleExport('csv')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors bg-surface1 border border-border text-text hover:bg-surface2"
          >
            <MdDownload className="text-xl" />
            CSV
          </button>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              showFilters || hasActiveFilters
                ? 'bg-accent text-white'
                : 'bg-surface1 border border-border text-text hover:bg-surface2'
            }`}
          >
            <MdFilterList className="text-xl" />
            {t('filter')}
            {hasActiveFilters && (
              <span className="ml-1 px-2 py-0.5 bg-white/20 rounded-full text-xs">
                {t('enabled')}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Top Pagination */}
      {totalPages > 1 && events.length > 0 && (
        <div className="mb-6 flex items-center justify-center gap-2">
          <button
            onClick={() => {
              prevPage()
              scrollToTop()
            }}
            disabled={page === 1}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('previous')}
          </button>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (allSelected) {
                  setSelectedIds(new Set())
                } else {
                  setSelectedIds(new Set(events.map((e) => e.id)))
                }
              }}
              className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors"
            >
              {allSelected ? t('clearFilters') : t('selectPage')}
            </button>
            {paginationItems.map((item, index) => {
              if (item === '...') {
                return (
                  <span key={`ellipsis-top-${index}`} className="px-2 text-muted">
                    ...
                  </span>
                )
              }
              const pageNum = item
              return (
                <button
                  key={`page-top-${pageNum}`}
                  onClick={() => {
                    goToPage(pageNum)
                    scrollToTop()
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
            onClick={() => {
              nextPage()
              scrollToTop()
            }}
            disabled={page === totalPages}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('next')}
          </button>
        </div>
      )}

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-surface1 border border-border rounded-lg p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Camera Filter */}
            <div>
              <label className="block text-sm font-medium text-muted mb-2">
                {t('camera')}
              </label>
              <select
                value={cameraFilter}
                onChange={(e) => setCameraFilter(e.target.value)}
                className="w-full px-4 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:border-accent"
              >
                <option value="">{t('cameras')}</option>
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
                {t('timestamp')}
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
                {t('confidence')}: {confidenceInput}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={confidenceInput}
                onChange={(e) => setConfidenceInput(Number(e.target.value))}
                onPointerUp={commitConfidence}
                onMouseUp={commitConfidence}
                onTouchEnd={commitConfidence}
                onKeyUp={commitConfidence}
                className="w-full h-2 bg-surface2 rounded-lg appearance-none cursor-pointer accent-accent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-muted mb-2">
                {t('page')} {t('total')}
              </label>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                className="w-full px-4 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:border-accent"
              >
                {[10, 20, 50].map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
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
                {t('clearFilters')}
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
              ? t('noData')
              : t('noEvents')}
          </p>
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors"
            >
              {t('clearFilters')}
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
              cameraName={cameraNameById.get(event.camera_id)}
              timestamp={event.timestamp}
              confidence={event.confidence}
              summary={event.summary}
              collageUrl={event.collage_url}
              mp4Url={event.mp4_url}
              selected={selectedIds.has(event.id)}
              onSelect={handleSelect}
              onClick={handleOpen}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            onClick={() => {
              prevPage()
              scrollToTop()
            }}
            disabled={page === 1}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('previous')}
          </button>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (allSelected) {
                  setSelectedIds(new Set())
                } else {
                  setSelectedIds(new Set(events.map((e) => e.id)))
                }
              }}
              className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors"
            >
              {allSelected ? t('clearFilters') : t('selectPage')}
            </button>
            {paginationItems.map((item, index) => {
              if (item === '...') {
                return (
                  <span key={`ellipsis-${index}`} className="px-2 text-muted">
                    ...
                  </span>
                )
              }
              const pageNum = item
              return (
                <button
                  key={pageNum}
                  onClick={() => {
                    goToPage(pageNum)
                    scrollToTop()
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
            onClick={() => {
              nextPage()
              scrollToTop()
            }}
            disabled={page === totalPages}
            className="px-4 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t('next')}
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
          cameraName={cameraNameById.get(selectedEvent.camera_id)}
          initialTab={selectedEventTab ?? undefined}
          onClose={() => {
            setSelectedEventId(null)
            setSelectedEventTab(null)
          }}
          onDelete={handleDeleteEvent}
        />
      )}

      {compareOpen && compareEvents && (
        <EventCompare
          left={compareEvents.left}
          right={compareEvents.right}
          cameraNameById={cameraNameById}
          onClose={() => setCompareOpen(false)}
        />
      )}
    </div>
  )
}
