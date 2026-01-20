/**
 * Stream tab - RTSP stream configuration
 */
import React from 'react';
import type { StreamConfig } from '../../types/api';

interface StreamTabProps {
  config: StreamConfig;
  onChange: (config: StreamConfig) => void;
  onSave: () => void;
}

export const StreamTab: React.FC<StreamTabProps> = ({ config, onChange, onSave }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Stream Settings</h3>
        <p className="text-sm text-muted mb-6">
          Configure RTSP stream ingestion (camera → backend)
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Protocol
          </label>
          <select
            value={config.protocol}
            onChange={(e) => onChange({ ...config, protocol: e.target.value as StreamConfig['protocol'] })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="tcp">TCP (Recommended)</option>
            <option value="udp">UDP</option>
          </select>
          <p className="text-xs text-muted mt-1">
            TCP prevents frame tearing from packet loss
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Buffer Size
          </label>
          <input
            type="number"
            min="1"
            max="10"
            value={config.buffer_size}
            onChange={(e) => onChange({ ...config, buffer_size: parseInt(e.target.value) || 1 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Lower buffer = lower latency (default: 1)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Reconnect Delay (seconds)
          </label>
          <input
            type="number"
            min="1"
            max="60"
            value={config.reconnect_delay_seconds}
            onChange={(e) => onChange({ ...config, reconnect_delay_seconds: parseInt(e.target.value) || 5 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Max Reconnect Attempts
          </label>
          <input
            type="number"
            min="1"
            max="50"
            value={config.max_reconnect_attempts}
            onChange={(e) => onChange({ ...config, max_reconnect_attempts: parseInt(e.target.value) || 10 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        Save Stream Settings
      </button>
    </div>
  );
};
