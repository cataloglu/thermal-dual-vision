/**
 * Settings tabs navigation component
 */
import React from 'react';

export type TabId = 
  | 'cameras'
  | 'detection'
  | 'thermal'
  | 'stream'
  | 'zones'
  | 'live'
  | 'recording'
  | 'events'
  | 'ai'
  | 'telegram';

interface Tab {
  id: TabId;
  label: string;
}

const tabs: Tab[] = [
  { id: 'cameras', label: 'Cameras' },
  { id: 'detection', label: 'Detection' },
  { id: 'thermal', label: 'Thermal' },
  { id: 'stream', label: 'Stream' },
  { id: 'zones', label: 'Zones' },
  { id: 'live', label: 'Live' },
  { id: 'recording', label: 'Recording' },
  { id: 'events', label: 'Events' },
  { id: 'ai', label: 'AI' },
  { id: 'telegram', label: 'Telegram' },
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
