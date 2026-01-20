/**
 * Stream tab - RTSP stream configuration
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { StreamConfig } from '../../types/api';

interface StreamTabProps {
  config: StreamConfig;
  onChange: (config: StreamConfig) => void;
  onSave: () => void;
}

export const StreamTab: React.FC<StreamTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('streamSettings')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('streamDesc')}
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Protokol
          </label>
          <select
            value={config.protocol}
            onChange={(e) => onChange({ ...config, protocol: e.target.value as StreamConfig['protocol'] })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="tcp">TCP (Önerilen)</option>
            <option value="udp">UDP</option>
          </select>
          <p className="text-xs text-muted mt-1">
            TCP paket kaybından kaynaklanan kare yırtılmasını önler
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Buffer Boyutu
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
            Düşük buffer = düşük gecikme (varsayılan: 1)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Yeniden Bağlanma Gecikmesi (saniye)
          </label>
          <input
            type="number"
            min="1"
            max="60"
            value={config.reconnect_delay_seconds}
            onChange={(e) => onChange({ ...config, reconnect_delay_seconds: parseInt(e.target.value) || 5 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Yeniden bağlanma denemeleri arasındaki gecikme
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Maksimum Yeniden Bağlanma Denemesi
          </label>
          <input
            type="number"
            min="1"
            max="50"
            value={config.max_reconnect_attempts}
            onChange={(e) => onChange({ ...config, max_reconnect_attempts: parseInt(e.target.value) || 10 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Maksimum yeniden bağlanma deneme sayısı
          </p>
        </div>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveStreamSettings')}
      </button>
    </div>
  );
};
