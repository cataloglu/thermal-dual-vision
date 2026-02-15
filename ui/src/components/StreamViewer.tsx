import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { MdRefresh, MdError, MdCheckCircle } from 'react-icons/md'
import { getLiveStreamUrl } from '../services/api'

interface StreamViewerProps {
  cameraId: string
  cameraName: string
  streamUrl?: string
  status?: 'connected' | 'retrying' | 'down' | 'initializing'
}

export function StreamViewer({
  cameraId,
  cameraName,
  status,
}: StreamViewerProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [isVisible, setIsVisible] = useState(true)

  const imgRef = useRef<HTMLImageElement>(null)
  const retryTimeoutRef = useRef<number | null>(null)
  const loadingTimeoutRef = useRef<number | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const maxRetries = 15
  const RETRY_DELAYS = [1500, 2500, 4000, 6000, 8000, 10000, 12000, 15000, 18000, 20000]

  const effectiveUrl = getLiveStreamUrl(cameraId)

  useEffect(() => {
    setLoading(true)
    setError(false)
    if (retryTimeoutRef.current) {
      window.clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
    if (loadingTimeoutRef.current) {
      window.clearTimeout(loadingTimeoutRef.current)
      loadingTimeoutRef.current = null
    }
  }, [cameraId])

  useEffect(() => {
    if (!containerRef.current) {
      setIsVisible(true)
      return
    }
    if (typeof IntersectionObserver === 'undefined') {
      setIsVisible(true)
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting)
      },
      { rootMargin: '200px', threshold: 0.1 }
    )
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!isVisible) {
      if (imgRef.current) imgRef.current.src = ''
      return
    }
    setLoading(true)
    setError(false)
    setRetryCount(0)
    if (retryTimeoutRef.current) {
      window.clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }, [isVisible])

  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        window.clearTimeout(retryTimeoutRef.current)
      }
      if (loadingTimeoutRef.current) {
        window.clearTimeout(loadingTimeoutRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!isVisible) return
    if (loadingTimeoutRef.current) {
      window.clearTimeout(loadingTimeoutRef.current)
    }
    loadingTimeoutRef.current = window.setTimeout(() => {
      setLoading(false)
    }, 1500)
  }, [isVisible, cameraId])

  const handleLoad = () => {
    if (!isVisible) return
    setLoading(false)
    setError(false)
    setRetryCount(0)
  }

  const handleError = () => {
    if (!isVisible) return
    setLoading(false)
    setError(true)
    if (retryCount < maxRetries) {
      const delay = RETRY_DELAYS[Math.min(retryCount, RETRY_DELAYS.length - 1)]
      retryTimeoutRef.current = window.setTimeout(() => {
        setRetryCount((prev) => prev + 1)
        setError(false)
        setLoading(true)
        if (imgRef.current) {
          imgRef.current.src = `${effectiveUrl}?t=${Date.now()}`
        }
      }, delay)
    }
  }

  const handleRetry = () => {
    setRetryCount(0)
    setError(false)
    setLoading(true)
    if (retryTimeoutRef.current) {
      window.clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
    if (imgRef.current) {
      imgRef.current.src = `${effectiveUrl}?t=${Date.now()}`
    }
  }

  const statusColors = {
    connected: 'bg-green-500',
    retrying: 'bg-yellow-500',
    down: 'bg-red-500',
    initializing: 'bg-blue-500',
  }

  const statusLabels = {
    connected: t('connected'),
    retrying: t('retrying'),
    down: t('down'),
    initializing: t('initializing'),
  }

  const resolvedStatus = status || 'retrying'

  return (
    <div ref={containerRef} className="relative bg-surface2 rounded-lg overflow-hidden aspect-video border border-border">
      {/* Camera Name & Status Overlay */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-black/60 to-transparent p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold">{cameraName}</h3>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${statusColors[resolvedStatus]}`} />
            <span className="text-white text-sm">{statusLabels[resolvedStatus]}</span>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && !error && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface2">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-accent border-t-transparent mx-auto mb-4" />
            <p className="text-muted">{t('loading')}...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface2">
          <div className="text-center p-6">
            <MdError className="text-red-500 text-5xl mx-auto mb-4" />
            <p className="text-text mb-2">{t('error')}</p>
            <p className="text-muted text-sm mb-4">
              {retryCount}/{maxRetries}
            </p>
            <button
              onClick={handleRetry}
              className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors mx-auto"
            >
              <MdRefresh className="text-lg" />
              {t('refresh')}
            </button>
          </div>
        </div>
      )}

      {/* MJPEG Stream */}
      {isVisible && (
        <img
          ref={imgRef}
          src={effectiveUrl}
          alt={cameraName}
          loading="lazy"
          className={`w-full h-full object-contain ${error ? 'hidden' : 'block'}`}
          onLoad={handleLoad}
          onError={handleError}
        />
      )}

      {/* Success Indicator (brief) */}
      {!loading && !error && retryCount > 0 && (
        <div className="absolute bottom-4 right-4 bg-green-500 text-white px-3 py-1 rounded-lg flex items-center gap-2 animate-fade-in">
          <MdCheckCircle />
          <span className="text-sm">{t('connected')}</span>
        </div>
      )}
    </div>
  )
}
