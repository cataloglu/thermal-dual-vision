/**
 * Media tab - Media cleanup settings
 */
import React from 'react';
import type { MediaConfig } from '../../types/api';

interface MediaTabProps {
  config: MediaConfig;
  onChange: (config: MediaConfig) => void;
  onSave: () => void;
}

export const MediaTab: React.FC<MediaTabProps> = ({ config, onChange, onSave }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Media Cleanup</h3>
        <p className="text-sm text-muted mb-6">
          Configure media file retention and disk management
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Retention Days
          </label>
          <input
            type="number"
            min="1"
            max="365"
            value={config.retention_days}
            onChange={(e) => onChange({ ...config, retention_days: parseInt(e.target.value) || 30 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            How many days to keep media files
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Cleanup Interval (hours)
          </label>
          <input
            type="number"
            min="1"
            max="168"
            value={config.cleanup_interval_hours}
            onChange={(e) => onChange({ ...config, cleanup_interval_hours: parseInt(e.target.value) || 24 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            How often to run cleanup job (default: 24 hours)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Disk Limit: {config.disk_limit_percent}%
          </label>
          <input
            type="range"
            min="50"
            max="95"
            step="5"
            value={config.disk_limit_percent}
            onChange={(e) => onChange({ ...config, disk_limit_percent: parseInt(e.target.value) })}
            className="w-full h-2 bg-surface2 rounded-lg appearance-none cursor-pointer accent-accent"
          />
          <div className="flex justify-between text-xs text-muted mt-1">
            <span>50% (Conservative)</span>
            <span>95% (Aggressive)</span>
          </div>
        </div>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        Save Media Settings
      </button>
    </div>
  );
};
