/**
 * Motion tab - Motion detection settings
 */
import React from 'react';
import type { MotionConfig } from '../../types/api';

interface MotionTabProps {
  config: MotionConfig;
  onChange: (config: MotionConfig) => void;
  onSave: () => void;
}

export const MotionTab: React.FC<MotionTabProps> = ({ config, onChange, onSave }) => {
  const applyPreset = (preset: 'thermal_recommended' | 'color_recommended') => {
    if (preset === 'thermal_recommended') {
      onChange({
        ...config,
        sensitivity: 8,
        min_area: 450,
        cooldown_seconds: 4
      });
    } else {
      onChange({
        ...config,
        sensitivity: 7,
        min_area: 500,
        cooldown_seconds: 5
      });
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

      {/* Presets */}
      <div>
        <label className="block text-sm font-medium text-text mb-2">
          Presets
        </label>
        <div className="flex gap-3">
          <button
            onClick={() => applyPreset('thermal_recommended')}
            className="px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors"
          >
            Thermal Recommended
          </button>
          <button
            onClick={() => applyPreset('color_recommended')}
            className="px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors"
          >
            Color Recommended
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
