/**
 * Zones tab - Zone/ROI configuration
 */
import React, { useState, useEffect } from 'react'
import { ZoneEditor } from '../ZoneEditor'
import { api } from '../../services/api'
import toast from 'react-hot-toast'

interface Camera {
  id: string
  name: string
}

interface Zone {
  id: string
  name: string
  enabled: boolean
  mode: string
  polygon: Array<[number, number]>
}

export const ZonesTab: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedCamera, setSelectedCamera] = useState<string>('')
  const [zones, setZones] = useState<Zone[]>([])
  const [zoneName, setZoneName] = useState('')
  const [zoneMode, setZoneMode] = useState<'person' | 'motion' | 'both'>('person')
  const [snapshotUrl, setSnapshotUrl] = useState<string>('')

  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const data = await api.getCameras()
        setCameras(data.cameras || [])
      } catch (error) {
        console.error('Failed to fetch cameras:', error)
      }
    }
    fetchCameras()
  }, [])

  useEffect(() => {
    if (selectedCamera) {
      // TODO: Fetch camera snapshot
      setSnapshotUrl(`/api/cameras/${selectedCamera}/snapshot`)
      // TODO: Fetch camera zones
      setZones([])
    }
  }, [selectedCamera])

  const handleSaveZone = (points: Array<{ x: number; y: number }>) => {
    if (!zoneName) {
      toast.error('Zone adı gerekli')
      return
    }

    // Normalize points to [x, y] array format
    const polygon: Array<[number, number]> = points.map(p => [p.x, p.y])
    
    // TODO: Save zone to backend with polygon data
    console.log('Saving zone:', { name: zoneName, mode: zoneMode, polygon })
    toast.success(`Zone kaydedildi: ${zoneName}`)
    setZoneName('')
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Bölge Ayarları</h3>
        <p className="text-sm text-muted mb-6">
          Kamera görüntüsünde algılama bölgeleri tanımlayın
        </p>
      </div>

      {/* Camera Selection */}
      <div>
        <label className="block text-sm font-medium text-text mb-2">
          Kamera Seçin
        </label>
        <select
          value={selectedCamera}
          onChange={(e) => setSelectedCamera(e.target.value)}
          className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
        >
          <option value="">Kamera seçin...</option>
          {cameras.map((camera) => (
            <option key={camera.id} value={camera.id}>
              {camera.name}
            </option>
          ))}
        </select>
      </div>

      {selectedCamera && (
        <>
          {/* Zone Editor */}
          <ZoneEditor
            snapshotUrl={snapshotUrl}
            onSave={handleSaveZone}
          />

          {/* Zone Name & Mode */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Zone Adı
              </label>
              <input
                type="text"
                value={zoneName}
                onChange={(e) => setZoneName(e.target.value)}
                placeholder="Giriş Yolu"
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Zone Modu
              </label>
              <select
                value={zoneMode}
                onChange={(e) => setZoneMode(e.target.value as typeof zoneMode)}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="person">Person (Alarm ver)</option>
                <option value="motion">Motion (Pre-filter)</option>
                <option value="both">Both (Her ikisi)</option>
              </select>
            </div>
          </div>

          {/* Existing Zones */}
          {zones.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-text mb-3">Kayıtlı Bölgeler</h4>
              <div className="space-y-2">
                {zones.map((zone) => (
                  <div
                    key={zone.id}
                    className="flex items-center justify-between p-3 bg-surface1 border border-border rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={zone.enabled}
                        className="w-4 h-4 accent-accent"
                        readOnly
                      />
                      <span className="text-text">{zone.name}</span>
                      <span className="px-2 py-1 bg-surface2 text-muted text-xs rounded">
                        {zone.mode}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <button className="px-3 py-1 bg-surface2 border border-border text-text rounded hover:bg-surface2/80 transition-colors text-sm">
                        Düzenle
                      </button>
                      <button className="px-3 py-1 bg-error/20 border border-error/50 text-error rounded hover:bg-error/30 transition-colors text-sm">
                        Sil
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {!selectedCamera && (
        <div className="bg-surface1 border border-border rounded-lg p-12 text-center">
          <p className="text-muted">Lütfen önce bir kamera seçin</p>
        </div>
      )}
    </div>
  )
}
