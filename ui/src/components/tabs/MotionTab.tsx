/**
 * Motion tab - Motion detection settings
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import type { MotionConfig } from '../../types/api';

interface MotionTabProps {
  config: MotionConfig;
  onChange: (config: MotionConfig) => void;
  onSave: () => void;
}

export const MotionTab: React.FC<MotionTabProps> = ({ config }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('motionTitle')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('motionDesc')}
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
          <div>{t('motionSummarySensitivity', { value: config.sensitivity })}</div>
          <div>{t('motionSummaryMinArea', { value: config.min_area })}</div>
          <div>{t('motionSummaryCooldown', { value: config.cooldown_seconds })}</div>
        </div>
      </div>
    </div>
  );
};
