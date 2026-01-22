/**
 * Settings tabs navigation component
 */
import React from 'react';

export type TabId = 
  | 'cameras'
  | 'detection'
  | 'motion'
  | 'thermal'
  | 'stream'
  | 'zones'
  | 'live'
  | 'recording'
  | 'events'
  | 'media'
  | 'ai'
  | 'telegram'
  | 'appearance';

interface Tab {
  id: TabId;
  label: string;
}

const tabs: Tab[] = [
  { id: 'cameras', label: 'Kameralar' },
  { id: 'detection', label: 'Algılama' },
  { id: 'thermal', label: 'Termal' },
  { id: 'stream', label: 'Stream' },
  { id: 'zones', label: 'Bölgeler' },
  { id: 'live', label: 'Canlı' },
  { id: 'recording', label: 'Kayıt' },
  { id: 'events', label: 'Olaylar' },
  { id: 'ai', label: 'AI' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'appearance', label: 'Görünüm' },
];

interface SettingsTabsProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export const SettingsTabs: React.FC<SettingsTabsProps> = ({ activeTab, onTabChange }) => {
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
