/**
 * Live tab - Live stream output settings
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { LiveConfig } from '../../types/api';

interface LiveTabProps {
  config: LiveConfig;
  onChange: (config: LiveConfig) => void;
  onSave: () => void;
}

export const LiveTab: React.FC<LiveTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('liveViewSettings')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('liveViewDesc')}
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('outputMode')}
          </label>
          <select
            value={config.output_mode}
            onChange={(e) => onChange({ ...config, output_mode: e.target.value as LiveConfig['output_mode'] })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="mjpeg">MJPEG ({t('simple')})</option>
            <option value="webrtc">WebRTC ({t('lowLatency')})</option>
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
                {t('enableWebRTC')}
              </label>
            </div>

            {config.webrtc.enabled && (
              <div>
                <label className="block text-sm font-medium text-text mb-2">
                  {t('go2rtcURL')}
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
              </div>
            )}
          </div>
        )}
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveLiveSettings')}
      </button>
    </div>
  );
};
