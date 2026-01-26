/**
 * Recording tab - Recording and retention settings
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { RecordConfig } from '../../types/api';

interface RecordingTabProps {
  config: RecordConfig;
  onChange: (config: RecordConfig) => void;
  onSave: () => void;
}

export const RecordingTab: React.FC<RecordingTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  const deleteOrder = config.delete_order.filter((type) => type !== 'gif')

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('recordingSettingsTitle')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('recordingSettingsDesc')}
        </p>
      </div>

      {/* Important Notice */}
      <div className="bg-surface2 border-l-4 border-warning p-4 rounded-lg">
        <h3 className="font-bold text-warning mb-2">⚠️ {t('recordingImportantTitle')}</h3>
        <div className="space-y-3 text-sm">
          <div>
            <strong className="text-text">{t('recordingEventTitle')}</strong>
            <p className="text-muted">{t('recordingEventDesc')}</p>
            <p className="text-success">✅ {t('recordingEventAlwaysOn')}</p>
          </div>
          <div>
            <strong className="text-text">{t('recordingContinuousTitle')}</strong>
            <p className="text-muted">{t('recordingContinuousDesc')}</p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {/* Sürekli kayıt kaldırıldı - sadece event bazlı kayıt var */}
        {(
          <>
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('recordingRetentionLabel')}
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
                {t('recordingRetentionHint')}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('recordingDiskLimitLabel', { value: config.disk_limit_percent })}
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
              <p className="text-xs text-muted mt-1">
                {t('recordingDiskLimitHint')}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('recordingSegmentLabel')}
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
                {t('recordingSegmentHint')}
              </p>
            </div>

            {/* TASK 19: Cleanup Policy */}
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('recordingCleanupPolicyLabel')}
              </label>
              <select
                value={config.cleanup_policy}
                onChange={(e) => onChange({ ...config, cleanup_policy: e.target.value as 'oldest_first' | 'lowest_confidence' })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="oldest_first">{t('recordingCleanupOldest')}</option>
                <option value="lowest_confidence">{t('recordingCleanupLowest')}</option>
              </select>
              <p className="text-xs text-muted mt-1">
                {t('recordingCleanupHint')}
              </p>
            </div>

            {/* TASK 20: Delete Order - FIXED */}
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('recordingDeleteOrderLabel')}
              </label>
              <div className="space-y-2">
                {deleteOrder.map((type, idx) => (
                  <div key={`${type}-${idx}`} className="flex items-center gap-2 p-2 bg-surface2 rounded">
                    <span className="text-muted">{idx + 1}.</span>
                    <span className="flex-1 capitalize text-text">{type}</span>
                    <button
                      type="button"
                      onClick={() => {
                        if (idx === 0) return
                        const next = [...deleteOrder]
                        const temp = next[idx]
                        next[idx] = next[idx - 1]
                        next[idx - 1] = temp
                        onChange({ ...config, delete_order: next })
                      }}
                      disabled={idx === 0}
                      className="px-2 py-1 bg-surface1 border border-border text-text rounded hover:bg-surface1/80 disabled:opacity-30 text-sm"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (idx === deleteOrder.length - 1) return
                        const next = [...deleteOrder]
                        const temp = next[idx]
                        next[idx] = next[idx + 1]
                        next[idx + 1] = temp
                        onChange({ ...config, delete_order: next })
                      }}
                      disabled={idx === deleteOrder.length - 1}
                      className="px-2 py-1 bg-surface1 border border-border text-text rounded hover:bg-surface1/80 disabled:opacity-30 text-sm"
                    >
                      ↓
                    </button>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted mt-1">
                {t('recordingDeleteOrderHint')}
              </p>
            </div>
          </>
        )}

        {/* Event bazlı kayıt her zaman aktif bilgisi */}
        <div className="bg-success/10 border border-success/40 rounded-lg p-4">
          <p className="text-success text-sm font-semibold mb-1">
            ✅ Event Kayıtları Aktif
          </p>
          <p className="text-muted text-xs">
            Person algılandığında otomatik olarak collage ve MP4 oluşturulur
          </p>
        </div>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('recordingSaveSettings')}
      </button>
    </div>
  );
};
