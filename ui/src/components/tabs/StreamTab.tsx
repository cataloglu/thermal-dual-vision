/**
 * Stream tab - RTSP stream configuration
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import type { StreamConfig } from '../../types/api';

interface StreamTabProps {
  config: StreamConfig;
  onChange: (config: StreamConfig) => void;
  onSave: () => void;
}

export const StreamTab: React.FC<StreamTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('streamSettings')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('streamDesc')}
        </p>
      </div>

      <div className="bg-surface2 border-l-4 border-info p-4 rounded-lg">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h4 className="font-semibold text-text">{t('perfShortcutTitle')}</h4>
            <p className="text-xs text-muted mt-1">{t('perfShortcutDesc')}</p>
          </div>
          <button
            onClick={() => navigate('/settings?tab=performance')}
            className="px-3 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface1/80 transition-colors text-sm"
          >
            {t('perfShortcutButton')}
          </button>
        </div>
        <div className="mt-3 text-xs text-muted space-y-1">
          <div>{t('streamSummaryProtocol', { value: config.protocol.toUpperCase() })}</div>
          <div>{t('streamSummaryBuffer', { value: config.buffer_size })}</div>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('reconnectDelay')} ({t('seconds')})
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
            {t('maxReconnectAttempts')}
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
        {t('saveStreamSettings')}
      </button>
    </div>
  );
};
