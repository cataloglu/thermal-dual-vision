import { useRef, useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { MdUndo, MdClear, MdSave } from 'react-icons/md'

interface Point {
  x: number
  y: number
}

interface ZoneEditorProps {
  snapshotUrl?: string
  initialPoints?: Point[]
  onSave: (points: Point[]) => void
}

export function ZoneEditor({ snapshotUrl, initialPoints = [], onSave }: ZoneEditorProps) {
  const { t } = useTranslation()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const imgRef = useRef<HTMLImageElement | null>(null)
  const [points, setPoints] = useState<Point[]>(initialPoints)
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null)

  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Draw snapshot if available
    if (snapshotUrl) {
      if (!imgRef.current || imgRef.current.src !== snapshotUrl) {
        const img = new Image()
        img.src = snapshotUrl
        imgRef.current = img
      }
      const img = imgRef.current
      if (img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
        drawPolygon(ctx)
      } else {
        img.onload = () => {
          if (canvasRef.current) {
            const ctx2 = canvasRef.current.getContext('2d')
            if (ctx2) {
              ctx2.clearRect(0, 0, canvas.width, canvas.height)
              ctx2.drawImage(img, 0, 0, canvas.width, canvas.height)
              drawPolygon(ctx2)
            }
          }
        }
      }
    } else {
      // Draw placeholder
      ctx.fillStyle = '#1E293B'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#94A3B8'
      ctx.font = '16px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(t('selectCamera'), canvas.width / 2, canvas.height / 2)
      drawPolygon(ctx)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshotUrl, points, hoveredPoint, t])

  useEffect(() => {
    drawCanvas()
  }, [drawCanvas])

  const drawPolygon = (ctx: CanvasRenderingContext2D) => {
    if (points.length === 0) return

    // Draw lines
    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y)
    }
    if (points.length > 2) {
      ctx.closePath()
      ctx.fillStyle = 'rgba(16, 185, 129, 0.2)' // Yeşil fill
      ctx.fill()
    }
    ctx.strokeStyle = '#10B981' // Yeşil border
    ctx.lineWidth = 2
    ctx.stroke()

    // Draw points
    points.forEach((point, index) => {
      ctx.beginPath()
      ctx.arc(point.x, point.y, 6, 0, 2 * Math.PI)
      ctx.fillStyle = hoveredPoint === index ? '#EF4444' : '#FFFFFF'
      ctx.fill()
      ctx.strokeStyle = '#000000'
      ctx.lineWidth = 2
      ctx.stroke()
    })
  }

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // Check if clicking near existing point
    const clickedPoint = points.findIndex(p => 
      Math.sqrt((p.x - x) ** 2 + (p.y - y) ** 2) < 10
    )

    if (clickedPoint === -1 && points.length < 20) {
      // Add new point
      setPoints([...points, { x, y }])
    }
  }

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // Check if hovering over point
    const hovered = points.findIndex(p => 
      Math.sqrt((p.x - x) ** 2 + (p.y - y) ** 2) < 10
    )

    setHoveredPoint(hovered === -1 ? null : hovered)
  }

  const handleCanvasContextMenu = (e: React.MouseEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // Find clicked point
    const clickedPoint = points.findIndex(p => 
      Math.sqrt((p.x - x) ** 2 + (p.y - y) ** 2) < 10
    )

    if (clickedPoint !== -1) {
      // Remove point
      setPoints(points.filter((_, i) => i !== clickedPoint))
    }
  }

  const handleUndo = () => {
    if (points.length > 0) {
      setPoints(points.slice(0, -1))
    }
  }

  const handleClear = () => {
    setPoints([])
  }

  const handleSave = () => {
    if (points.length < 3) {
      alert(t('zoneMinPointsRequired'))
      return
    }

    // Normalize coordinates (0.0-1.0)
    const canvas = canvasRef.current
    if (!canvas) return

    const normalizedPoints = points.map(p => ({
      x: p.x / canvas.width,
      y: p.y / canvas.height
    }))

    onSave(normalizedPoints)
  }

  return (
    <div className="space-y-4">
      {/* Canvas */}
      <div className="border border-border rounded-lg overflow-hidden bg-surface2">
        <canvas
          ref={canvasRef}
          width={800}
          height={600}
          onClick={handleCanvasClick}
          onMouseMove={handleCanvasMouseMove}
          onContextMenu={handleCanvasContextMenu}
          className="w-full h-auto cursor-crosshair"
        />
      </div>

      {/* Instructions */}
      <div className="bg-surface2 border-l-4 border-info p-4 rounded-lg text-sm">
        <p className="text-text mb-2"><strong>{t('howToUse')}:</strong></p>
        <ul className="text-muted space-y-1">
          <li>• {t('leftClick')}</li>
          <li>• {t('rightClick')}</li>
          <li>• {t('minPoints')}</li>
          <li>• {t('maxPoints')}</li>
        </ul>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={points.length < 3}
          className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <MdSave />
          {t('saveZone')} ({points.length})
        </button>
        <button
          onClick={handleUndo}
          disabled={points.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors disabled:opacity-50"
        >
          <MdUndo />
          {t('undo')}
        </button>
        <button
          onClick={handleClear}
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
