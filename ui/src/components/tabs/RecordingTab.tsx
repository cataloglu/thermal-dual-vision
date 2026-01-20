/**
 * Recording tab - Recording and retention settings
 */
import React from 'react';
import type { RecordConfig } from '../../types/api';

interface RecordingTabProps {
  config: RecordConfig;
  onChange: (config: RecordConfig) => void;
  onSave: () => void;
}

export const RecordingTab: React.FC<RecordingTabProps> = ({ config, onChange, onSave }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Recording Settings</h3>
        <p className="text-sm text-muted mb-6">
          Configure event-based recording and retention policy
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="recording-enabled"
            checked={config.enabled}
            onChange={(e) => onChange({ ...config, enabled: e.target.checked })}
            className="w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
          />
          <label htmlFor="recording-enabled" className="text-sm font-medium text-text">
            Enable Recording
          </label>
        </div>

        {config.enabled && (
          <>
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Retention Days
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={config.retention_days}
                onChange={(e) => onChange({ ...config, retention_days: parseInt(e.target.value) || 7 })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <p className="text-xs text-muted mt-1">
                How many days to keep recordings
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
                className="w-full"
              />
              <p className="text-xs text-muted mt-1">
                Maximum disk usage percentage (50-95%)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Segment Length (seconds)
              </label>
              <input
                type="number"
                min="5"
                max="60"
                value={config.record_segments_seconds}
                onChange={(e) => onChange({ ...config, record_segments_seconds: parseInt(e.target.value) || 10 })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <p className="text-xs text-muted mt-1">
                Length of each recording segment
              </p>
            </div>
          </>
        )}
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        Save Recording Settings
      </button>
    </div>
  );
};
