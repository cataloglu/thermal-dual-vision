/**
 * Recording tab - Event recording info (retention in Media tab)
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { RecordConfig } from '../../types/api';

interface RecordingTabProps {
  config?: RecordConfig;
  onChange?: (config: RecordConfig) => void;
  onSave?: () => void;
  onNavigateToMedia?: () => void;
}

export const RecordingTab: React.FC<RecordingTabProps> = ({ onNavigateToMedia }) => {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('recordingSettingsTitle')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('recordingSettingsDesc')}
        </p>
      </div>

      {/* Event recording - always on */}
      <div className="bg-success/10 border border-success/40 rounded-lg p-4">
        <p className="text-success text-sm font-semibold mb-2">
          ✅ {t('recordingEventAlwaysOn')}
        </p>
        <p className="text-muted text-sm mb-2">
          {t('recordingEventDesc')}
        </p>
        <p className="text-muted text-xs">
          {t('recordingBufferInfo')}
        </p>
      </div>

      {/* Retention - in Media tab */}
      <div className="bg-surface2 border border-border rounded-lg p-4">
        <p className="text-text text-sm font-medium mb-2">
          {t('recordingRetentionInMedia')}
        </p>
        <p className="text-muted text-xs mb-4">
          {t('recordingRetentionInMediaHint')}
        </p>
        {onNavigateToMedia && (
          <button
            onClick={onNavigateToMedia}
            className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors text-sm"
          >
            {t('recordingGoToMedia')}
          </button>
        )}
      </div>
    </div>
  );
};
