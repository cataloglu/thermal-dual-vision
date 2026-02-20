import { useRef, useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { MdUndo, MdClear, MdSave, MdRefresh } from 'react-icons/md'

interface Point {
  x: number
  y: number
}

interface ExistingZone {
  id: string
  name: string
  enabled: boolean
  polygon: Array<[number, number]>
}

interface ZoneEditorProps {
  snapshotUrl?: string
  initialPoints?: Point[]
  existingZones?: ExistingZone[]
  onSave: (points: Point[]) => void
  onRefreshSnapshot?: () => void
}

const HIT_RADIUS = 12

export function ZoneEditor({ snapshotUrl, initialPoints = [], existingZones = [], onSave, onRefreshSnapshot }: ZoneEditorProps) {
  const { t } = useTranslation()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imgRef = useRef<HTMLImageElement | null>(null)
  const [points, setPoints] = useState<Point[]>(initialPoints)
  const [mousePos, setMousePos] = useState<Point | null>(null)
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null)
  const [draggingPoint, setDraggingPoint] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // Redraw whenever state changes
  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Background
    ctx.fillStyle = '#1E293B'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // Draw snapshot
    const img = imgRef.current
    if (img && img.complete && img.naturalWidth > 0) {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    } else if (!snapshotUrl) {
      ctx.fillStyle = '#94A3B8'
      ctx.font = '16px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(t('selectCamera'), canvas.width / 2, canvas.height / 2)
    }

    // Draw saved (existing) zones on canvas
    if (existingZones.length > 0) {
      existingZones.forEach((zone) => {
        if (zone.polygon.length < 3) return
        const pts = zone.polygon.map(([nx, ny]) => ({
          x: nx * canvas.width,
          y: ny * canvas.height,
        }))
        const color = zone.enabled ? '#3B82F6' : '#6B7280'
        const alpha = zone.enabled ? 0.2 : 0.12

        // Filled polygon
        ctx.beginPath()
        ctx.moveTo(pts[0].x, pts[0].y)
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y)
        ctx.closePath()
        ctx.fillStyle = `rgba(${zone.enabled ? '59,130,246' : '107,114,128'},${alpha})`
        ctx.fill()

        // Outline
        ctx.beginPath()
        ctx.moveTo(pts[0].x, pts[0].y)
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y)
        ctx.closePath()
        ctx.strokeStyle = color
        ctx.lineWidth = 1.5
        ctx.setLineDash([5, 3])
        ctx.stroke()
        ctx.setLineDash([])

        // Zone name label at centroid
        const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length
        const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length
        ctx.font = 'bold 11px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillStyle = 'rgba(0,0,0,0.55)'
        ctx.fillRect(cx - 36, cy - 9, 72, 18)
        ctx.fillStyle = zone.enabled ? '#93C5FD' : '#9CA3AF'
        ctx.fillText(zone.name, cx, cy)
        ctx.textBaseline = 'alphabetic'
      })
    }

    if (points.length === 0) return

    // Filled polygon (currently drawing)
    if (points.length > 2) {
      ctx.beginPath()
      ctx.moveTo(points[0].x, points[0].y)
      for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y)
      ctx.closePath()
      ctx.fillStyle = 'rgba(16, 185, 129, 0.25)'
      ctx.fill()
    }

    // Polygon edges
    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y)
    if (points.length > 2) ctx.closePath()
    ctx.strokeStyle = '#10B981'
    ctx.lineWidth = 2
    ctx.stroke()

    // Preview line: last point → mouse cursor
    if (mousePos && draggingPoint === null) {
      const nearFirst = points.length >= 3 &&
        Math.hypot(mousePos.x - points[0].x, mousePos.y - points[0].y) < HIT_RADIUS

      ctx.beginPath()
      ctx.moveTo(points[points.length - 1].x, points[points.length - 1].y)
      ctx.lineTo(mousePos.x, mousePos.y)
      ctx.strokeStyle = nearFirst ? '#10B981' : 'rgba(255,255,255,0.5)'
      ctx.lineWidth = 1.5
      ctx.setLineDash([6, 4])
      ctx.stroke()
      ctx.setLineDash([])
    }

    // Points
    points.forEach((point, index) => {
      const isHovered = hoveredPoint === index
      const isFirst = index === 0
      const canClose = isFirst && points.length >= 3

      ctx.beginPath()
      ctx.arc(point.x, point.y, isHovered ? 9 : 7, 0, 2 * Math.PI)
      ctx.fillStyle = isHovered && canClose ? '#10B981' : isHovered ? '#EF4444' : '#FFFFFF'
      ctx.fill()
      ctx.strokeStyle = '#000'
      ctx.lineWidth = 2
      ctx.stroke()

      // Point index label
      ctx.fillStyle = '#000'
      ctx.font = 'bold 10px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(String(index + 1), point.x, point.y)
    })
    ctx.textBaseline = 'alphabetic'
  }, [snapshotUrl, points, existingZones, mousePos, hoveredPoint, draggingPoint, t])

  useEffect(() => {
    drawCanvas()
  }, [drawCanvas])

  // Load snapshot image and trigger redraw once loaded
  useEffect(() => {
    if (!snapshotUrl) {
      imgRef.current = null
      drawCanvas()
      return
    }
    setIsLoading(true)
    const img = new Image()
    img.onload = () => {
      imgRef.current = img
      setIsLoading(false)
      drawCanvas()
    }
    img.onerror = () => {
      setIsLoading(false)
      drawCanvas()
    }
    img.src = snapshotUrl
  }, [snapshotUrl, drawCanvas])

  const getCanvasPos = (e: React.MouseEvent<HTMLCanvasElement>): Point => {
    const canvas = canvasRef.current!
    const rect = canvas.getBoundingClientRect()
    return {
      x: (e.clientX - rect.left) * (canvas.width / rect.width),
      y: (e.clientY - rect.top) * (canvas.height / rect.height),
    }
  }

  const findPointAt = (pos: Point) =>
    points.findIndex(p => Math.hypot(p.x - pos.x, p.y - pos.y) < HIT_RADIUS)

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (e.button !== 0) return
    const pos = getCanvasPos(e)
    const idx = findPointAt(pos)
    if (idx !== -1) {
      setDraggingPoint(idx)
    }
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const pos = getCanvasPos(e)
    setMousePos(pos)

    if (draggingPoint !== null) {
      setPoints(prev => prev.map((p, i) => i === draggingPoint ? pos : p))
      return
    }

    const hitIdx = findPointAt(pos)
    setHoveredPoint(hitIdx === -1 ? null : hitIdx)
  }

  const handleMouseUp = () => {
    setDraggingPoint(null)
  }

  const handleMouseLeave = () => {
    setMousePos(null)
    setHoveredPoint(null)
    setDraggingPoint(null)
  }

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (draggingPoint !== null) return
    const pos = getCanvasPos(e)
    const idx = findPointAt(pos)

    // Clicking first point with 3+ points closes/saves polygon — just a visual hint; user clicks Save
    if (idx === 0 && points.length >= 3) return

    // Clicking existing point: no-op (dragging handles move)
    if (idx !== -1) return

    if (points.length < 20) {
      setPoints(prev => [...prev, pos])
    }
  }

  const handleContextMenu = (e: React.MouseEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    const pos = getCanvasPos(e)
    const idx = findPointAt(pos)
    if (idx !== -1) setPoints(prev => prev.filter((_, i) => i !== idx))
  }

  const handleSave = () => {
    if (points.length < 3) {
      alert(t('zoneMinPointsRequired'))
      return
    }
    const canvas = canvasRef.current
    if (!canvas) return
    onSave(points.map(p => ({ x: p.x / canvas.width, y: p.y / canvas.height })))
    setPoints([])
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-text">{t('zoneEditor')}</h4>
        {onRefreshSnapshot && (
          <button
            onClick={() => { setIsLoading(true); onRefreshSnapshot() }}
            className="flex items-center gap-1.5 px-3 py-1 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors text-sm"
          >
            <MdRefresh />
            {t('refresh')}
          </button>
        )}
      </div>

      {/* Canvas container */}
      <div className="relative border border-border rounded-lg overflow-hidden bg-surface2">
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          onClick={handleClick}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
          onContextMenu={handleContextMenu}
          className="w-full h-auto cursor-crosshair select-none"
        />
        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-surface2/80 gap-3">
            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <span className="text-muted text-sm">{t('loading')}...</span>
          </div>
        )}
        {/* Point counter badge */}
        {points.length > 0 && (
          <div className="absolute top-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
            {points.length} {t('points') || 'nokta'}
          </div>
        )}
      </div>

      {/* Compact instructions */}
      <div className="flex gap-4 text-xs text-muted bg-surface2 px-4 py-2 rounded-lg">
        <span>🖱️ Sol tık → nokta ekle</span>
        <span>↕️ Sürükle → noktayı taşı</span>
        <span>🖱️ Sağ tık → nokta sil</span>
        <span>Min 3 nokta gerekli</span>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={points.length < 3}
          className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <MdSave />
          {t('saveZone')} ({points.length}/3+)
        </button>
        <button
          onClick={() => setPoints(prev => prev.slice(0, -1))}
          disabled={points.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors disabled:opacity-50"
        >
          <MdUndo />
          {t('undo')}
        </button>
        <button
          onClick={() => setPoints([])}
          disabled={points.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-error/20 border border-error/50 text-error rounded-lg hover:bg-error/30 transition-colors disabled:opacity-50"
        >
          <MdClear />
          {t('clear')}
        </button>
      </div>
    </div>
  )
}
