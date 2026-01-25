/**
 * Live tab - Live stream output settings
 */
import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import type { LiveConfig } from '../../types/api';
import apiClient from '../../services/api';

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
        // Get Ingress base path from window.location
        const pathname = window.location.pathname;
        const basePath = pathname.replace(/\/+$/, '').replace(/\/index\.html$/, '');
        
        // Ingress: /hassio/ingress/TOKEN/go2rtc/api
        // Direct: /go2rtc/api
        const go2rtcUrl = basePath && basePath !== '/' ? `${basePath}/go2rtc/api` : '/go2rtc/api';
        
        const response = await fetch(go2rtcUrl);
        setGo2rtcAvailable(response.ok);
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

        {/* WebRTC automatically configured - no user input needed */}
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
