import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { MdRefresh, MdError, MdCheckCircle } from 'react-icons/md'

interface StreamViewerProps {
  cameraId: string
  cameraName: string
  streamUrl: string
  status?: 'connected' | 'retrying' | 'down'
}

export function StreamViewer({ 
  cameraName, 
  streamUrl,
  status = 'connected' 
}: StreamViewerProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const imgRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    setLoading(true)
    setError(false)
  }, [streamUrl])

  const handleLoad = () => {
    setLoading(false)
    setError(false)
    setRetryCount(0)
  }

  const handleError = () => {
    setLoading(false)
    setError(true)
    
    // Auto-retry up to 3 times
    if (retryCount < 3) {
      setTimeout(() => {
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
    if (imgRef.current) {
      imgRef.current.src = `${streamUrl}?t=${Date.now()}`
    }
  }

  const statusColors = {
    connected: 'bg-green-500',
    retrying: 'bg-yellow-500',
    down: 'bg-red-500',
  }

  const statusLabels = {
    connected: t('connected'),
    retrying: t('retrying'),
    down: t('down'),
  }

  return (
    <div className="relative bg-surface2 rounded-lg overflow-hidden aspect-video border border-border">
      {/* Camera Name & Status Overlay */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-black/60 to-transparent p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold">{cameraName}</h3>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${statusColors[status]}`} />
            <span className="text-white text-sm">{statusLabels[status]}</span>
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
              {retryCount > 0 && `${retryCount}/3`}
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
        src={streamUrl}
        alt={cameraName}
        className={`w-full h-full object-contain ${loading || error ? 'hidden' : 'block'}`}
        onLoad={handleLoad}
        onError={handleError}
      />

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
