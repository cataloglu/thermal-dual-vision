import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { MdRefresh, MdError, MdCheckCircle } from 'react-icons/md'
import { getLiveSnapshotUrl, getLiveWebRTCUrl, resolveApiPath } from '../services/api'

/** Max concurrent live streams (backend limit); only this many tiles load MJPEG. */
export const MAX_LIVE_STREAMS = 2

interface StreamViewerProps {
  cameraId: string
  cameraName: string
  streamUrl?: string
  status?: 'connected' | 'retrying' | 'down' | 'initializing'
  /** If false, show placeholder instead of loading stream (to respect backend limit). */
  loadStream?: boolean
}

interface LiveDebugInfo {
  ok?: boolean
  source?: string | null
  go2rtc_ok?: boolean
  go2rtc_error?: string | null
  rtsp_available?: boolean
  worker_frame?: boolean
  stream_name?: string | null
  status?: number
  error?: string
  reason?: string
}

type StreamMode = 'webrtc' | 'snapshot' | 'error'

async function startWebRTC(
  offerUrl: string,
  videoEl: HTMLVideoElement,
  signal: AbortSignal,
): Promise<RTCPeerConnection> {
  const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
  })

  pc.addTransceiver('video', { direction: 'recvonly' })
  pc.addTransceiver('audio', { direction: 'recvonly' })

  pc.ontrack = (ev) => {
    if (ev.streams[0]) {
      videoEl.srcObject = ev.streams[0]
    }
  }

  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)

  await new Promise<void>((resolve) => {
    if (pc.iceGatheringState === 'complete') { resolve(); return }
    const done = () => { if (pc.iceGatheringState === 'complete') { pc.removeEventListener('icegatheringstatechange', done); resolve() } }
    pc.addEventListener('icegatheringstatechange', done)
    setTimeout(resolve, 3000)
  })

  if (signal.aborted) { pc.close(); throw new DOMException('Aborted', 'AbortError') }

  const resp = await fetch(offerUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/sdp' },
    body: pc.localDescription!.sdp,
    signal,
  })

  if (!resp.ok) throw new Error(`WebRTC offer failed: ${resp.status}`)

  const answerSdp = await resp.text()
  await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp })

  return pc
}

export function StreamViewer({
  cameraId,
  cameraName,
  status,
  loadStream = true,
}: StreamViewerProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [streamMode, setStreamMode] = useState<StreamMode>('webrtc')
  const [snapshotTick, setSnapshotTick] = useState(0)
  const [debugInfo, setDebugInfo] = useState<LiveDebugInfo | null>(null)
  const [debugUpdatedAt, setDebugUpdatedAt] = useState('')
  const [isVisible, setIsVisible] = useState(true)

  const videoRef = useRef<HTMLVideoElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const pcRef = useRef<RTCPeerConnection | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const snapshotIntervalRef = useRef<number | null>(null)
  const lastDebugRef = useRef(0)

  const webrtcUrl = resolveApiPath(getLiveWebRTCUrl(cameraId))
  const snapshotUrl = resolveApiPath(getLiveSnapshotUrl(cameraId))
  const probeUrl = resolveApiPath(`/api/live/${cameraId}.mjpeg?probe=1`)

  const updateDebug = useCallback(async (reason: string) => {
    const now = Date.now()
    if (now - lastDebugRef.current < 1000) return
    lastDebugRef.current = now
    try {
      const res = await fetch(`${probeUrl}&t=${now}`, { cache: 'no-store' })
      const data = await res.json().catch(() => null)
      setDebugInfo({ ...(data ?? {}), status: res.status, reason })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setDebugInfo({ ok: false, error: message, reason })
    }
    setDebugUpdatedAt(new Date().toLocaleTimeString())
  }, [probeUrl])

  const stopWebRTC = useCallback(() => {
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null }
    if (pcRef.current) { pcRef.current.close(); pcRef.current = null }
    if (videoRef.current) { videoRef.current.srcObject = null }
  }, [])

  const stopSnapshot = useCallback(() => {
    if (snapshotIntervalRef.current) {
      clearInterval(snapshotIntervalRef.current)
      snapshotIntervalRef.current = null
    }
  }, [])

  const startSnapshot = useCallback(() => {
    stopWebRTC()
    setStreamMode('snapshot')
    setLoading(true)
    setError(false)
    updateDebug('fallback_snapshot')
    if (imgRef.current) imgRef.current.src = `${snapshotUrl}?t=${Date.now()}`
    stopSnapshot()
    snapshotIntervalRef.current = window.setInterval(() => {
      setSnapshotTick((p) => p + 1)
    }, 1000)
  }, [stopWebRTC, stopSnapshot, snapshotUrl, updateDebug])

  const startWebRTCStream = useCallback(async () => {
    if (!videoRef.current || !loadStream || !isVisible) return
    stopWebRTC()
    stopSnapshot()
    setStreamMode('webrtc')
    setLoading(true)
    setError(false)

    const ac = new AbortController()
    abortRef.current = ac

    try {
      const pc = await startWebRTC(webrtcUrl, videoRef.current, ac.signal)
      if (ac.signal.aborted) { pc.close(); return }
      pcRef.current = pc

      pc.onconnectionstatechange = () => {
        const s = pc.connectionState
        if (s === 'connected') {
          setLoading(false)
          setError(false)
          updateDebug('webrtc_connected')
        } else if (s === 'failed' || s === 'disconnected' || s === 'closed') {
          if (!ac.signal.aborted) {
            updateDebug('webrtc_failed')
            startSnapshot()
          }
        }
      }

      setTimeout(() => {
        if (pc.connectionState !== 'connected' && !ac.signal.aborted) {
          updateDebug('webrtc_timeout')
          startSnapshot()
        }
      }, 15000)
    } catch (err) {
      if (!ac.signal.aborted) {
        updateDebug('webrtc_error')
        startSnapshot()
      }
    }
  }, [loadStream, isVisible, webrtcUrl, stopWebRTC, stopSnapshot, updateDebug, startSnapshot])

  useEffect(() => {
    if (!containerRef.current) { setIsVisible(true); return }
    if (typeof IntersectionObserver === 'undefined') { setIsVisible(true); return }
    const observer = new IntersectionObserver(
      ([entry]) => setIsVisible(entry.isIntersecting),
      { rootMargin: '200px', threshold: 0.1 }
    )
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!isVisible || !loadStream) {
      stopWebRTC()
      stopSnapshot()
      return
    }
    updateDebug('visibility_change')
    startWebRTCStream()
  }, [isVisible, loadStream, cameraId])

  useEffect(() => {
    return () => {
      stopWebRTC()
      stopSnapshot()
    }
  }, [])

  const handleVideoPlaying = () => {
    setLoading(false)
    setError(false)
  }

  const handleSnapshotLoad = () => {
    setLoading(false)
    setError(false)
  }

  const handleSnapshotError = () => {
    setLoading(false)
    setError(true)
    updateDebug('snapshot_error')
  }

  const handleRetry = () => {
    setError(false)
    startWebRTCStream()
  }

  const formatBool = (value?: boolean) => (value ? t('liveDebugYes') : t('liveDebugNo'))
  const formatValue = (value?: string | number | null) =>
    value === null || value === undefined || value === '' ? '-' : String(value)

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
    <div className="flex flex-col gap-2">
      <div ref={containerRef} className="relative bg-surface2 rounded-lg overflow-hidden aspect-video border border-border">
        <div className="absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-black/60 to-transparent p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-white font-semibold">{cameraName}</h3>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${statusColors[resolvedStatus]}`} />
              <span className="text-white text-sm">{statusLabels[resolvedStatus]}</span>
            </div>
          </div>
        </div>

        {!loadStream && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface2">
            <p className="text-muted text-center px-4 text-sm">{t('liveStreamLimit')}</p>
          </div>
        )}

        {loadStream && loading && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface2">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-accent border-t-transparent mx-auto mb-4" />
              <p className="text-muted">{t('loading')}...</p>
            </div>
          </div>
        )}

        {loadStream && error && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface2">
            <div className="text-center p-6">
              <MdError className="text-red-500 text-5xl mx-auto mb-4" />
              <p className="text-text mb-4">{t('error')}</p>
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

        {loadStream && isVisible && (
          <>
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className={`w-full h-full object-contain ${streamMode === 'webrtc' && !error ? 'block' : 'hidden'}`}
              onPlaying={handleVideoPlaying}
            />
            <img
              ref={imgRef}
              src={streamMode === 'snapshot' ? `${snapshotUrl}?t=${snapshotTick}` : undefined}
              alt={cameraName}
              className={`w-full h-full object-contain ${streamMode === 'snapshot' && !error ? 'block' : 'hidden'}`}
              onLoad={handleSnapshotLoad}
              onError={handleSnapshotError}
            />
          </>
        )}

        {loadStream && !loading && !error && streamMode === 'webrtc' && (
          <div className="absolute bottom-4 right-4 bg-green-500 text-white px-3 py-1 rounded-lg flex items-center gap-2">
            <MdCheckCircle />
            <span className="text-sm">WebRTC</span>
          </div>
        )}

        {loadStream && !loading && !error && streamMode === 'snapshot' && (
          <div className="absolute bottom-4 right-4 bg-yellow-500 text-white px-3 py-1 rounded-lg flex items-center gap-2">
            <span className="text-sm">Snapshot</span>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border bg-surface1 p-3 text-xs text-muted">
        <div className="flex items-center justify-between">
          <span className="text-text font-semibold">{t('liveDebugTitle')}</span>
          <span>{debugUpdatedAt ? `${t('liveDebugUpdated')}: ${debugUpdatedAt}` : t('liveDebugEmpty')}</span>
        </div>
        {debugInfo && (
          <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
            <span>{t('liveDebugOk')}</span>
            <span className={debugInfo.ok ? 'text-green-400' : 'text-red-400'}>
              {formatBool(debugInfo.ok)}
            </span>
            <span>{t('liveDebugSource')}</span>
            <span>{formatValue(debugInfo.source)}</span>
            <span>{t('liveDebugGo2rtc')}</span>
            <span>{formatBool(debugInfo.go2rtc_ok)}</span>
            <span>{t('liveDebugGo2rtcError')}</span>
            <span>{formatValue(debugInfo.go2rtc_error)}</span>
            <span>{t('liveDebugRtsp')}</span>
            <span>{formatBool(debugInfo.rtsp_available)}</span>
            <span>{t('liveDebugWorker')}</span>
            <span>{formatBool(debugInfo.worker_frame)}</span>
            <span>Stream</span>
            <span className={streamMode === 'webrtc' ? 'text-green-400' : 'text-yellow-400'}>
              {streamMode}
            </span>
            <span>{t('liveDebugReason')}</span>
            <span>{formatValue(debugInfo.reason)}</span>
            <span>{t('liveDebugStatus')}</span>
            <span>{formatValue(debugInfo.status)}</span>
            {debugInfo.error && (
              <>
                <span>{t('liveDebugError')}</span>
                <span>{formatValue(debugInfo.error)}</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
