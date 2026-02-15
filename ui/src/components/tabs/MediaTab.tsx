/**
 * Media tab - Media cleanup settings
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { MediaConfig } from '../../types/api';

interface MediaTabProps {
  config: MediaConfig;
  onChange: (config: MediaConfig) => void;
  onSave: () => void;
}

export const MediaTab: React.FC<MediaTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('mediaCleanupTitle')}</h3>
        <p className="text-sm text-muted mb-4">
          {t('mediaCleanupDesc')}
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('mediaRetentionLabel')}
          </label>
          <select
            value={config.retention_days}
            onChange={(e) => onChange({ ...config, retention_days: parseInt(e.target.value) })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value={0}>{t('mediaRetentionUnlimited')}</option>
            <option value={1}>{t('mediaRetention1Day')}</option>
            <option value={3}>{t('mediaRetention3Days')}</option>
            <option value={5}>{t('mediaRetention5Days')}</option>
            <option value={7}>{t('mediaRetention7Days')}</option>
            <option value={14}>{t('mediaRetention14Days')}</option>
            <option value={30}>{t('mediaRetention30Days')}</option>
            <option value={90}>{t('mediaRetention90Days')}</option>
            <option value={365}>{t('mediaRetention365Days')}</option>
          </select>
          <p className="text-xs text-muted mt-1">
            {t('mediaRetentionHint')}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('mediaCleanupIntervalLabel')}
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
            {t('mediaCleanupIntervalHint')}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('mediaDiskLimitLabel', { value: config.disk_limit_percent })}
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
            <span>{t('mediaDiskLimitLow')}</span>
            <span>{t('mediaDiskLimitHigh')}</span>
          </div>
        </div>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('mediaSaveSettings')}
      </button>
    </div>
  );
};
