/**
 * Events tab - Event generation settings
 */
import React from 'react';
import type { EventConfig } from '../../types/api';

interface EventsTabProps {
  config: EventConfig;
  onChange: (config: EventConfig) => void;
  onSave: () => void;
}

export const EventsTab: React.FC<EventsTabProps> = ({ config, onChange, onSave }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Event Settings</h3>
        <p className="text-sm text-muted mb-6">
          Configure event generation and frame buffer settings
        </p>
      </div>

      <div className="space-y-4">
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
            Minimum time between events (prevents duplicates)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Frame Buffer Size
          </label>
          <input
            type="number"
            min="5"
            max="30"
            value={config.frame_buffer_size}
            onChange={(e) => onChange({ ...config, frame_buffer_size: parseInt(e.target.value) || 10 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Number of frames to buffer for collage generation
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Frame Interval
          </label>
          <input
            type="number"
            min="1"
            max="10"
            value={config.frame_interval}
            onChange={(e) => onChange({ ...config, frame_interval: parseInt(e.target.value) || 2 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Capture every Nth frame
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Min Event Duration (seconds)
          </label>
          <input
            type="number"
            min="0"
            max="10"
            step="0.5"
            value={config.min_event_duration}
            onChange={(e) => onChange({ ...config, min_event_duration: parseFloat(e.target.value) || 1.0 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Minimum duration for an event to be recorded
          </p>
        </div>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        Save Event Settings
      </button>
    </div>
  );
};
