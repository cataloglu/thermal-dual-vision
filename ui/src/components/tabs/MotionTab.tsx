/**
 * Motion tab - Motion detection settings
 */
import React, { useState, useEffect } from 'react';
import type { MotionConfig } from '../../types/api';
import toast from 'react-hot-toast';

interface MotionTabProps {
  config: MotionConfig;
  onChange: (config: MotionConfig) => void;
  onSave: () => void;
}

interface Camera {
  id: string;
  name: string;
  type: string;
}

export const MotionTab: React.FC<MotionTabProps> = ({ config, onChange, onSave }) => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string>('');

  useEffect(() => {
    // Fetch cameras
    fetch('/api/cameras')
      .then(res => res.json())
      .then(data => {
        setCameras(data.cameras || []);
        if (data.cameras && data.cameras.length > 0) {
          setSelectedCamera(data.cameras[0].id);
        }
      })
      .catch(err => console.error('Failed to fetch cameras:', err));
  }, []);

  const selectedCameraData = cameras.find(c => c.id === selectedCamera);
  const isThermal = selectedCameraData?.type === 'thermal' || selectedCameraData?.type === 'dual';

  const applyPreset = (preset: 'thermal_recommended' | 'color_recommended') => {
    if (preset === 'thermal_recommended') {
      onChange({
        ...config,
        sensitivity: 8,
        min_area: 450,
        cooldown_seconds: 4
      });
      toast.success('Thermal preset uygulandı');
    } else {
      onChange({
        ...config,
        sensitivity: 7,
        min_area: 500,
        cooldown_seconds: 5
      });
      toast.success('Color preset uygulandı');
    }
  };

  const applyRecommendedForCamera = () => {
    if (isThermal) {
      applyPreset('thermal_recommended');
    } else {
      applyPreset('color_recommended');
    }
  };
  
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Motion Detection</h3>
        <p className="text-sm text-muted mb-6">
          Pre-filter for person detection (frame-diff based)
        </p>
      </div>

      {/* Camera Selection */}
      <div className="bg-surface2 border-l-4 border-info p-4 rounded-lg">
        <div className="mb-3">
          <label className="block text-sm font-medium text-text mb-2">
            Select Camera to Configure
          </label>
          <select
            value={selectedCamera}
            onChange={(e) => setSelectedCamera(e.target.value)}
            className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            {cameras.map((cam) => (
              <option key={cam.id} value={cam.id}>
                {cam.name} ({cam.type})
              </option>
            ))}
          </select>
        </div>
        {selectedCameraData && (
          <p className="text-xs text-muted">
            💡 Kamera Tipi: <span className="font-semibold text-text">{selectedCameraData.type.toUpperCase()}</span>
            {isThermal 
              ? ' → Thermal için önerilen ayarları kullanın' 
              : ' → Color için önerilen ayarları kullanın'}
          </p>
        )}
      </div>

      {/* Presets */}
      <div>
        <label className="block text-sm font-medium text-text mb-2">
          Presets
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            onClick={() => applyPreset('thermal_recommended')}
            className={`px-4 py-2 border rounded-lg transition-colors ${
              isThermal 
                ? 'bg-accent text-white border-accent' 
                : 'bg-surface2 border-border text-text hover:bg-surface2/80'
            }`}
          >
            Thermal Recommended
            {isThermal && ' ✓'}
          </button>
          <button
            onClick={() => applyPreset('color_recommended')}
            className={`px-4 py-2 border rounded-lg transition-colors ${
              !isThermal 
                ? 'bg-accent text-white border-accent' 
                : 'bg-surface2 border-border text-text hover:bg-surface2/80'
            }`}
          >
            Color Recommended
            {!isThermal && ' ✓'}
          </button>
          <button
            onClick={applyRecommendedForCamera}
            className="px-4 py-2 bg-success text-white border border-success rounded-lg hover:bg-success/90 transition-colors"
          >
            Apply for {selectedCameraData?.type || 'Camera'}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Sensitivity: {config.sensitivity}
          </label>
          <input
            type="range"
            min="1"
            max="10"
            value={config.sensitivity}
            onChange={(e) => onChange({ ...config, sensitivity: parseInt(e.target.value) })}
            className="w-full h-2 bg-surface2 rounded-lg appearance-none cursor-pointer accent-accent"
          />
          <div className="flex justify-between text-xs text-muted mt-1">
            <span>1 (Low)</span>
            <span>10 (High)</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Min Area (pixels)
          </label>
          <input
            type="number"
            min="100"
            max="5000"
            value={config.min_area}
            onChange={(e) => onChange({ ...config, min_area: parseInt(e.target.value) || 500 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Minimum pixel area for motion detection
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Cooldown (seconds)
          </label>
          <input
            type="number"
            min="0"
            max="60"
            value={config.cooldown_seconds}
            onChange={(e) => onChange({ ...config, cooldown_seconds: parseInt(e.target.value) || 5 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Minimum time between motion detections
          </p>
        </div>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        Save Motion Settings
      </button>
    </div>
  );
};
