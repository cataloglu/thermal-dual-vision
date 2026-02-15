import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { MdRefresh, MdError, MdCheckCircle } from 'react-icons/md'
import { getIngressBase } from '../services/api'
import { useSettings } from '../hooks/useSettings'
import '../go2rtc-player'

// Helper to get go2rtc URL (Ingress-aware, same base for /live, /dashboard etc.)
const getGo2rtcUrl = () => {
  const env = import.meta.env.VITE_GO2RTC_URL;
  if (env) return env;
  const ingress = getIngressBase();
  return ingress ? `${ingress}/go2rtc` : '/go2rtc';
};

const GO2RTC_URL = getGo2rtcUrl();
const normalizeGo2rtcBase = (url: string) => url.replace(/\/+$/, '');
const getGo2rtcWsUrl = (cameraId: string) =>
  `${normalizeGo2rtcBase(GO2RTC_URL)}/api/ws?src=${encodeURIComponent(cameraId)}`;

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
  const [isVisible, setIsVisible] = useState(true)
  const [go2rtcAvailable, setGo2rtcAvailable] = useState(false)
  
  const { settings } = useSettings()
  const outputMode = settings?.live?.output_mode || 'mjpeg'

  const imgRef = useRef<HTMLImageElement>(null)
  const playerRef = useRef<HTMLElement>(null)
  const retryTimeoutRef = useRef<number | null>(null)
  const loadingTimeoutRef = useRef<number | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const maxRetries = 15
  const RETRY_DELAYS = [1500, 2500, 4000, 6000, 8000, 10000, 12000, 15000, 18000, 20000]

  useEffect(() => {
    const checkGo2rtc = async () => {
      try {
        const res = await fetch(`${GO2RTC_URL}/api`, { method: 'GET', credentials: 'omit' })
        setGo2rtcAvailable(res.ok)
      } catch {
        setGo2rtcAvailable(false)
      }
    }
    checkGo2rtc()
    const interval = setInterval(checkGo2rtc, 15000)
    return () => clearInterval(interval)
  }, [])

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
  }, [streamUrl, cameraId, outputMode])

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
  }, [isVisible, streamUrl, outputMode])

  const handleLoad = () => {
    if (!isVisible) return
    setLoading(false)
    setError(false)
    setRetryCount(0)

  }

  const shouldShowWebrtc = outputMode === 'webrtc' && go2rtcAvailable
  const webrtcActive = shouldShowWebrtc && isVisible

  useEffect(() => {
    const player = playerRef.current as any
    if (!player) return

    if (!webrtcActive) {
      if (typeof player.ondisconnect === 'function') {
        player.ondisconnect()
      }
      return
    }

    player.mode = 'webrtc'
    player.media = 'video,audio'
    player.src = getGo2rtcWsUrl(cameraId)
  }, [webrtcActive, cameraId])

  useEffect(() => {
    if (!webrtcActive) return
    let cancelled = false
    let cleanup: (() => void) | null = null
    let attempts = 0

    const attach = () => {
      if (cancelled) return
      const player = playerRef.current as any
      const video = player?.video as HTMLVideoElement | undefined
      if (video) {
        const onReady = () => {
          if (!isVisible) return
          handleLoad()
        }
        const onVideoError = () => {
          if (!isVisible) return
          setLoading(false)
          setError(true)
        }
        video.addEventListener('playing', onReady)
        video.addEventListener('loadeddata', onReady)
        video.addEventListener('error', onVideoError)
        cleanup = () => {
          video.removeEventListener('playing', onReady)
          video.removeEventListener('loadeddata', onReady)
          video.removeEventListener('error', onVideoError)
        }
        return
      }

      attempts += 1
      if (attempts < 20) {
        window.setTimeout(attach, 200)
      }
    }

    attach()

    return () => {
      cancelled = true
      if (cleanup) {
        cleanup()
      }
    }
  }, [webrtcActive, cameraId, isVisible])

  const handleError = () => {
    if (!isVisible) return
    setLoading(false)
    setError(true)
    if (outputMode === 'webrtc') {
      return
    }

    // Auto-retry with exponential backoff
    if (retryCount < maxRetries) {
      const delay = RETRY_DELAYS[Math.min(retryCount, RETRY_DELAYS.length - 1)]
      retryTimeoutRef.current = window.setTimeout(() => {
        setRetryCount(prev => prev + 1)
        setError(false)
        setLoading(true)
        if (imgRef.current) {
          imgRef.current.src = `${streamUrl}?t=${Date.now()}`
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
    if (outputMode === 'webrtc') {
      const player = playerRef.current as any
      if (player) {
        if (typeof player.ondisconnect === 'function') {
          player.ondisconnect()
        }
        if (webrtcActive) {
          player.mode = 'webrtc'
          player.media = 'video,audio'
          player.src = getGo2rtcWsUrl(cameraId)
        }
      }
      return
    }
    if (imgRef.current) {
      imgRef.current.src = `${streamUrl}?t=${Date.now()}`
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

      {/* MJPEG Stream / WebRTC Player */}
      {shouldShowWebrtc ? (
        <video-stream
          ref={playerRef}
          className="w-full h-full"
          title="WebRTC Stream"
        />
      ) : (
        <img
          ref={imgRef}
          src={effectiveStreamUrl}
          alt={cameraName}
          loading="lazy"
          className={`w-full h-full object-contain ${error ? 'hidden' : 'block'}`}
          onLoad={handleLoad}
          onError={handleError}
        />
      )}

      {/* Status indicator for fallback */}
      {outputMode === 'webrtc' && !go2rtcAvailable && (
        <div className="absolute top-4 left-4 bg-red-500/90 text-white px-3 py-2 rounded-lg text-sm z-20">
          go2rtc unavailable, using MJPEG fallback
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
