import { useEffect, useMemo, useState } from 'react'
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
}

export function useEvents(params: UseEventsParams = {}) {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(params.page || 1)
  const [pageSize, setPageSize] = useState(params.pageSize || 20)

  const fetchEvents = async () => {
    try {
      setLoading(true)
      setError(null)

      const data: EventsResponse = await api.getEvents({
        page,
        page_size: pageSize,
        camera_id: params.cameraId,
        date: params.date,
        confidence: params.minConfidence,
      })

      setEvents(data.events)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch events')
      console.error('Failed to fetch events:', err)
    } finally {
      setLoading(false)
    }
  }

  const filterKey = useMemo(() => {
    return [
      params.cameraId ?? '',
      params.date ?? '',
      params.minConfidence ?? '',
    ].join('|')
  }, [params.cameraId, params.date, params.minConfidence])

  useEffect(() => {
    fetchEvents()
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
