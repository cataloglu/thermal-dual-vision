/**
 * Settings tabs navigation component
 */
import React from 'react';
import { useTranslation } from 'react-i18next';

export type TabId = 
  | 'cameras'
  | 'camera_settings'
  | 'performance'
  | 'detection'
  | 'motion'
  | 'thermal'
  | 'stream'
  | 'zones'
  | 'live'
  | 'events'
  | 'media'
  | 'ai'
  | 'telegram'
  | 'mqtt'
  | 'appearance';

interface Tab {
  id: TabId;
  label: string;
}

interface SettingsTabsProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export const SettingsTabs: React.FC<SettingsTabsProps> = ({ activeTab, onTabChange }) => {
  const { t } = useTranslation();
  const tabs: Tab[] = [
    { id: 'cameras', label: t('cameras') },
    { id: 'camera_settings', label: t('cameraSettings') },
    { id: 'zones', label: t('zones') },
    { id: 'live', label: t('live') },
    { id: 'events', label: t('events') },
    { id: 'media', label: t('media') },
    { id: 'ai', label: t('ai') },
    { id: 'telegram', label: t('telegram') },
    { id: 'mqtt', label: t('mqtt') },
    { id: 'appearance', label: t('appearance') },
  ];

  return (
    <div className="flex space-x-1 border-b border-border mb-6 overflow-x-auto">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`
            px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap
            ${
              activeTab === tab.id
                ? 'text-accent border-b-2 border-accent'
                : 'text-muted hover:text-text'
            }
          `}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};
