/**
 * Live tab - Live stream output settings
 */
import React from 'react';
import type { LiveConfig } from '../../types/api';

interface LiveTabProps {
  config: LiveConfig;
  onChange: (config: LiveConfig) => void;
  onSave: () => void;
}

export const LiveTab: React.FC<LiveTabProps> = ({ config, onChange, onSave }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Live View Settings</h3>
        <p className="text-sm text-muted mb-6">
          Configure live stream output (backend → browser)
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Output Mode
          </label>
          <select
            value={config.output_mode}
            onChange={(e) => onChange({ ...config, output_mode: e.target.value as LiveConfig['output_mode'] })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="mjpeg">MJPEG (Simple, 1-3s latency)</option>
            <option value="webrtc">WebRTC (Low latency, requires go2rtc)</option>
          </select>
        </div>

        {config.output_mode === 'webrtc' && (
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="webrtc-enabled"
                checked={config.webrtc.enabled}
                onChange={(e) => onChange({ 
                  ...config, 
                  webrtc: { ...config.webrtc, enabled: e.target.checked } 
                })}
                className="w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
              />
              <label htmlFor="webrtc-enabled" className="text-sm font-medium text-text">
                Enable WebRTC
              </label>
            </div>

            {config.webrtc.enabled && (
              <div>
                <label className="block text-sm font-medium text-text mb-2">
                  go2rtc Server URL
                </label>
                <input
                  type="text"
                  value={config.webrtc.go2rtc_url}
                  onChange={(e) => onChange({ 
                    ...config, 
                    webrtc: { ...config.webrtc, go2rtc_url: e.target.value } 
                  })}
                  placeholder="http://localhost:1984"
                  className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
                />
                <p className="text-xs text-muted mt-1">
                  go2rtc server is required for WebRTC streaming
                </p>
              </div>
            )}

            <div className="p-4 bg-warning bg-opacity-10 border border-warning rounded-lg">
              <p className="text-sm text-warning">
                WebRTC requires go2rtc server to be running separately
              </p>
            </div>
          </div>
        )}
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        Save Live Settings
      </button>
    </div>
  );
};
