import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getEvents, getCameras, analyzeVideo } from '../services/api'
import { LoadingState } from '../components/LoadingState'
import { MdPlayArrow, MdCheckCircle, MdError, MdRefresh } from 'react-icons/md'

interface AnalysisResult {
  video_properties: { width: number; height: number; fps: number; frame_count: number; duration: number }
  analysis: {
    total_frames: number
    calculated_duration: number
    actual_duration: number
    duration_mismatch: number
    duplicate_frames: number
    duplicate_percentage: number
    duplicate_sequences: number
    timestamp_jumps: number
    estimated_missing_frames: number
  }
  diff_stats?: { average: number; std_dev: number; min: number; max: number }
  timestamp_jumps_detail?: Array<{ frame: number; from_ms: number; to_ms: number; gap_seconds: number; missing_frames_estimate: number }>
  duplicate_sequences_preview?: Array<{ start: number; end: number; length: number }>
  ok: boolean
  issues: string[]
}

interface EventItem {
  id: string
  camera_id: string
  timestamp: string
  mp4_url?: string
  media?: { mp4_url?: string }
}

export function VideoAnalysis() {
  const { t } = useTranslation()
  const location = useLocation()
  const stateEventId = (location.state as { eventId?: string })?.eventId
  const [events, setEvents] = useState<EventItem[]>([])
  const [cameras, setCameras] = useState<{ id: string; name: string }[]>([])
  const [selectedEventId, setSelectedEventId] = useState<string>(stateEventId || '')
  const [customPath, setCustomPath] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        const [eventsRes, camerasRes] = await Promise.all([
          getEvents({ page: 1, page_size: 50 }),
          getCameras(),
        ])
        const list = (eventsRes.events || []).filter((e: EventItem) => e.mp4_url || e.media?.mp4_url)
        setEvents(list)
        setCameras(camerasRes.cameras || [])
        if (list.length > 0) {
          const toSelect = (stateEventId && list.some((e: EventItem) => e.id === stateEventId))
            ? stateEventId
            : list[0].id
          setSelectedEventId(toSelect)
        }
      } catch (e) {
        console.error('Failed to fetch:', e)
        setError(t('loadFailed') || 'Failed to load')
      }
    }
    fetch()
  }, [])

  const handleAnalyze = async () => {
    setError(null)
    setResult(null)
    setAnalyzing(true)
    try {
      const params = selectedEventId ? { event_id: selectedEventId } : customPath ? { path: customPath } : null
      if (!params) {
        setError(t('videoAnalysisSelectEvent') || 'Select an event or enter a file path')
        return
      }
      const data = await analyzeVideo(params)
      setResult(data)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: { message?: string } } } }
      setError(err.response?.data?.detail?.message || (e instanceof Error ? e.message : 'Analysis failed'))
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text mb-2">
          {t('videoAnalysis') || 'Video Analizi'}
        </h1>
        <p className="text-muted">
          {t('videoAnalysisDesc') || 'Event videolarını çerçeve bazlı analiz edin: tekrar kareler, zaman sıçramaları, kalite sorunları.'}
        </p>
      </div>

      <div className="bg-surface1 border border-border rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold text-text mb-4">
          {t('videoAnalysisSelect') || 'Video Seç'}
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-muted mb-2">{t('events')} (MP4 olanlar)</label>
            <select
              value={selectedEventId}
              onChange={(e) => setSelectedEventId(e.target.value)}
              className="w-full px-4 py-2 bg-surface2 border border-border rounded-lg text-text"
            >
              <option value="">-- {t('selectEvent') || 'Event seçin'} --</option>
              {events.map((e) => {
                const cameraName = cameras.find((c) => c.id === e.camera_id)?.name || e.camera_id
                return (
                  <option key={e.id} value={e.id}>
                    {cameraName} · {e.timestamp?.slice(0, 19)}
                  </option>
                )
              })}
            </select>
          </div>
          <div>
            <label className="block text-sm text-muted mb-2">
              {t('videoAnalysisOrPath') || 'Veya sunucu dosya yolu'}
            </label>
            <input
              type="text"
              value={customPath}
              onChange={(e) => setCustomPath(e.target.value)}
              placeholder="C:\...\event-xxx-timelapse.mp4"
              className="w-full px-4 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted"
            />
          </div>
          <button
            onClick={handleAnalyze}
            disabled={analyzing || (!selectedEventId && !customPath)}
            className="flex items-center gap-2 px-6 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {analyzing ? (
              <>
                <MdRefresh className="animate-spin" />
                {t('analyzing') || 'Analiz ediliyor...'}
              </>
            ) : (
              <>
                <MdPlayArrow />
                {t('analyze') || 'Analiz Et'}
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-red-400">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-6">
          {/* Summary */}
          <div className={`rounded-lg p-6 border ${
            result.ok ? 'bg-green-500/10 border-green-500/30' : 'bg-amber-500/10 border-amber-500/30'
          }`}>
            <div className="flex items-center gap-2 mb-4">
              {result.ok ? (
                <MdCheckCircle className="text-green-500 text-2xl" />
              ) : (
                <MdError className="text-amber-500 text-2xl" />
              )}
              <h2 className="text-lg font-semibold text-text">
                {result.ok ? (t('videoOk') || 'Video iyi görünüyor') : (t('videoIssues') || 'Sorunlar tespit edildi')}
              </h2>
            </div>
            {result.issues.length > 0 && (
              <ul className="list-disc list-inside text-amber-200 space-y-1">
                {result.issues.map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            )}
          </div>

          {/* Video properties */}
          <div className="bg-surface1 border border-border rounded-lg p-6">
            <h3 className="text-lg font-semibold text-text mb-4">{t('videoProperties') || 'Video Özellikleri'}</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
              <div>
                <span className="text-muted">{t('resolution') || 'Çözünürlük'}:</span>
                <p className="text-text font-mono">{result.video_properties.width}×{result.video_properties.height}</p>
              </div>
              <div>
                <span className="text-muted">FPS:</span>
                <p className="text-text font-mono">{result.video_properties.fps}</p>
              </div>
              <div>
                <span className="text-muted">{t('frames') || 'Kare'}:</span>
                <p className="text-text font-mono">{result.video_properties.frame_count}</p>
              </div>
              <div>
                <span className="text-muted">{t('duration') || 'Süre'}:</span>
                <p className="text-text font-mono">{result.video_properties.duration}s</p>
              </div>
            </div>
          </div>

          {/* Analysis */}
          <div className="bg-surface1 border border-border rounded-lg p-6">
            <h3 className="text-lg font-semibold text-text mb-4">{t('analysis') || 'Analiz Sonuçları'}</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted">{t('actualDuration') || 'Gerçek süre'}:</span>
                <span className="text-text">{result.analysis.actual_duration}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">{t('durationMismatch') || 'Süre farkı'}:</span>
                <span className="text-text">{result.analysis.duration_mismatch}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">{t('duplicateFrames') || 'Tekrar kare'}:</span>
                <span className="text-text">{result.analysis.duplicate_frames} ({result.analysis.duplicate_percentage}%)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">{t('timestampJumps') || 'Zaman sıçraması'}:</span>
                <span className="text-text">{result.analysis.timestamp_jumps}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">{t('missingFrames') || 'Eksik kare tahmini'}:</span>
                <span className="text-text">~{result.analysis.estimated_missing_frames}</span>
              </div>
            </div>
          </div>

          {/* Timestamp jumps detail */}
          {result.timestamp_jumps_detail && result.timestamp_jumps_detail.length > 0 && (
            <div className="bg-surface1 border border-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-text mb-4">{t('timestampJumpsDetail') || 'Zaman sıçramaları'}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-muted text-left">
                      <th className="py-2">Frame</th>
                      <th className="py-2">Gap (s)</th>
                      <th className="py-2">Eksik kare</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.timestamp_jumps_detail.map((j, i) => (
                      <tr key={i} className="border-t border-border">
                        <td className="py-1 font-mono">{j.frame}</td>
                        <td className="py-1">{j.gap_seconds.toFixed(3)}</td>
                        <td className="py-1">~{j.missing_frames_estimate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Diff stats */}
          {result.diff_stats && Object.keys(result.diff_stats).length > 0 && (
            <div className="bg-surface1 border border-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-text mb-4">{t('frameDiffStats') || 'Kare fark istatistikleri'}</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div><span className="text-muted">Ort:</span> <span className="font-mono">{result.diff_stats.average?.toFixed(2)}</span></div>
                <div><span className="text-muted">Std:</span> <span className="font-mono">{result.diff_stats.std_dev?.toFixed(2)}</span></div>
                <div><span className="text-muted">Min:</span> <span className="font-mono">{result.diff_stats.min?.toFixed(2)}</span></div>
                <div><span className="text-muted">Max:</span> <span className="font-mono">{result.diff_stats.max?.toFixed(2)}</span></div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
