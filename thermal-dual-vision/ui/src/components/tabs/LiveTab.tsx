/**
 * Live tab - Live stream output settings
 */
import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import type { LiveConfig } from '../../types/api';

interface LiveTabProps {
  config: LiveConfig;
  onChange: (config: LiveConfig) => void;
  onSave: () => void;
}

export const LiveTab: React.FC<LiveTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  const [go2rtcAvailable, setGo2rtcAvailable] = useState(false);

  useEffect(() => {
    const checkGo2rtc = async () => {
      try {
        const GO2RTC_URL = import.meta.env.VITE_GO2RTC_URL || 'http://localhost:1984';
        const response = await fetch(`${GO2RTC_URL}/api`, { mode: 'no-cors' });
        setGo2rtcAvailable(true); // Assuming success if reachable, but no-cors makes it opaque. Checking availability logic.
      } catch {
        setGo2rtcAvailable(false);
      }
    };
    checkGo2rtc();
  }, []);
  
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
            Output Mode
          </label>
          <select
            value={config.output_mode}
            onChange={(e) => onChange({ ...config, output_mode: e.target.value as 'mjpeg' | 'webrtc' })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="mjpeg">MJPEG (basit, her zaman çalışır)</option>
            <option value="webrtc" disabled={!go2rtcAvailable}>
              WebRTC (hızlı, go2rtc gerekli) {!go2rtcAvailable && '- Unavailable'}
            </option>
          </select>
          
          {/* Status indicator */}
          <div className="mt-2 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${go2rtcAvailable ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-xs text-muted">
              go2rtc: {go2rtcAvailable ? 'Available' : 'Not running'}
            </span>
          </div>
          
          <p className="text-xs text-muted mt-2">
            MJPEG: 2-5s latency, basit<br />
            WebRTC: 0.5s latency, go2rtc container gerekli
          </p>
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
