/**
 * Events tab - Event generation settings
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { EventConfig } from '../../types/api';

interface EventsTabProps {
  config: EventConfig;
  onChange: (config: EventConfig) => void;
  onSave: () => void;
}

export const EventsTab: React.FC<EventsTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('eventSettings')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('eventDesc')}
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Bekleme Süresi (saniye)
          </label>
          <input
            type="number"
            min="0"
            max="60"
            value={config.cooldown_seconds}
            onChange={(e) => onChange({ ...config, cooldown_seconds: parseInt(e.target.value) || 5 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Olaylar arası minimum süre (tekrarları önler)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Kare Tamponu Boyutu
          </label>
          <input
            type="number"
            min="5"
            max="30"
            value={config.frame_buffer_size}
            onChange={(e) => onChange({ ...config, frame_buffer_size: parseInt(e.target.value) || 10 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Collage oluşturma için kare sayısı
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Kare Aralığı
          </label>
          <input
            type="number"
            min="1"
            max="10"
            value={config.frame_interval}
            onChange={(e) => onChange({ ...config, frame_interval: parseInt(e.target.value) || 2 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Her kaç karede bir yakalama yapılacak
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Minimum Olay Süresi (saniye)
          </label>
          <input
            type="number"
            min="0.5"
            max="10"
            step="0.5"
            value={config.min_event_duration}
            onChange={(e) => onChange({ ...config, min_event_duration: parseFloat(e.target.value) || 1.0 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            Minimum olay süresi (çok kısa olayları filtreler)
          </p>
        </div>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveEventSettings')}
      </button>
    </div>
  );
};
