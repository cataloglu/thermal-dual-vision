import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../services/api'

interface Event {
  id: string
  camera_id: string
  timestamp: string
  confidence: number
  event_type: string
  summary: string | null
  collage_url: string | null
  gif_url: string | null
  mp4_url: string | null
  rejected_by_ai?: boolean
}

interface EventsResponse {
  page: number
  page_size: number
  total: number
  events: Event[]
}

interface UseEventsParams {
  page?: number
  pageSize?: number
  cameraId?: string
  date?: string
  minConfidence?: number
  rejected?: boolean
}

export function useEvents(params: UseEventsParams = {}) {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(params.page || 1)
  const [pageSize, setPageSize] = useState(params.pageSize || 20)

  const abortRef = useRef<AbortController | null>(null)

  const fetchEvents = async () => {
    // Cancel any in-flight request before starting a new one
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    try {
      setLoading(true)
      setError(null)

      const data: EventsResponse = await api.getEvents({
        page,
        page_size: pageSize,
        camera_id: params.cameraId,
        date: params.date,
        confidence: params.minConfidence,
        rejected: params.rejected,
      }, { signal: controller.signal })

      if (!controller.signal.aborted) {
        setEvents(data.events)
        setTotal(data.total)
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') return
      setError(err instanceof Error ? err.message : 'Failed to fetch events')
      console.error('Failed to fetch events:', err)
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false)
      }
    }
  }

  const filterKey = useMemo(() => {
    return [
      params.cameraId ?? '',
      params.date ?? '',
      params.minConfidence ?? '',
      params.rejected ?? '',
    ].join('|')
  }, [params.cameraId, params.date, params.minConfidence, params.rejected])

  useEffect(() => {
    fetchEvents()
    return () => { abortRef.current?.abort() }
  }, [page, pageSize, filterKey])

  const refresh = () => fetchEvents()

  const totalPages = Math.ceil(total / pageSize)

  const nextPage = () => {
    if (page < totalPages) {
      setPage((p) => p + 1)
    }
  }

  const prevPage = () => {
    if (page > 1) {
      setPage((p) => p - 1)
    }
  }

  const goToPage = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage)
    }
  }

  const resetPage = () => setPage(1)

  const prependEvent = (event: Event) => {
    setEvents((prev) => [event, ...prev])
    setTotal((prev) => prev + 1)
  }

  return {
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
  }
}
