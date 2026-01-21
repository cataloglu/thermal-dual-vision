import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { MdRefresh, MdError, MdCheckCircle, MdFullscreen, MdPhotoCamera } from 'react-icons/md'
import { api } from '../services/api'

interface StreamViewerProps {
  cameraId: string
  cameraName: string
  streamUrl: string
  status?: 'connected' | 'retrying' | 'down' | 'initializing'
}

export function StreamViewer({ 
  cameraId,
  cameraName, 
  streamUrl,
  status 
}: StreamViewerProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [recording, setRecording] = useState(false)
  const [recordingLoading, setRecordingLoading] = useState(false)
  const [isVisible, setIsVisible] = useState(false)
  const imgRef = useRef<HTMLImageElement>(null)
  const retryTimeoutRef = useRef<number | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const maxRetries = 10

  useEffect(() => {
    setLoading(true)
    setError(false)
    if (retryTimeoutRef.current) {
      window.clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }, [streamUrl])

  useEffect(() => {
    if (!containerRef.current) return
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
    if (isVisible) return
    setLoading(true)
    setError(false)
    setRetryCount(0)
    if (imgRef.current) {
      imgRef.current.src = ''
    }
  }, [isVisible])

  useEffect(() => {
    const loadRecording = async () => {
      try {
        const data = await api.getRecordingStatus(cameraId)
        setRecording(Boolean(data.recording))
      } catch {
        setRecording(false)
      }
    }
    loadRecording()
  }, [cameraId])

  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        window.clearTimeout(retryTimeoutRef.current)
      }
    }
  }, [])

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
    
    // Auto-retry up to 10 times
    if (retryCount < maxRetries) {
      retryTimeoutRef.current = window.setTimeout(() => {
        setRetryCount(prev => prev + 1)
        if (imgRef.current) {
          imgRef.current.src = `${streamUrl}?t=${Date.now()}`
        }
      }, 2000)
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
      imgRef.current.src = `${streamUrl}?t=${Date.now()}`
    }
  }

  const handleSnapshot = () => {
    const url = api.getCameraSnapshotUrl(cameraId)
    window.open(url, '_blank')
  }

  const handleFullscreen = () => {
    if (!containerRef.current) return
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => undefined)
    } else {
      containerRef.current.requestFullscreen().catch(() => undefined)
    }
  }

  const handleRecordingToggle = async () => {
    setRecordingLoading(true)
    try {
      if (recording) {
        const data = await api.stopRecording(cameraId)
        setRecording(Boolean(data.recording))
      } else {
        const data = await api.startRecording(cameraId)
        setRecording(Boolean(data.recording))
      }
    } finally {
      setRecordingLoading(false)
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
  const effectiveStreamUrl = isVisible ? streamUrl : ''

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
      <img
        ref={imgRef}
        src={effectiveStreamUrl}
        alt={cameraName}
        loading="lazy"
        className={`w-full h-full object-contain ${loading || error ? 'hidden' : 'block'}`}
        onLoad={handleLoad}
        onError={handleError}
      />

      {!error && (
        <div className="absolute bottom-4 left-4 flex items-center gap-2">
          <button
            onClick={handleSnapshot}
            className="px-3 py-2 bg-surface1/80 text-white rounded-lg hover:bg-surface1 transition-colors"
            title={t('snapshot')}
          >
            <MdPhotoCamera />
          </button>
          <button
            onClick={handleRecordingToggle}
            disabled={recordingLoading}
            className={`px-3 py-2 rounded-lg transition-colors ${recording ? 'bg-error text-white' : 'bg-surface1/80 text-white hover:bg-surface1'}`}
            title={recording ? t('stopRecording') : t('startRecording')}
          >
            {recording ? '●' : '○'}
          </button>
          <button
            onClick={handleFullscreen}
            className="px-3 py-2 bg-surface1/80 text-white rounded-lg hover:bg-surface1 transition-colors"
            title={t('fullscreen')}
          >
            <MdFullscreen />
          </button>
        </div>
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
