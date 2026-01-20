/**
 * Settings page - Main settings interface
 */
import React, { useState } from 'react';
import { Toaster } from 'react-hot-toast';
import { useSettings } from '../hooks/useSettings';
import { SettingsTabs, TabId } from '../components/SettingsTabs';
import { CamerasTab } from '../components/tabs/CamerasTab';
import { DetectionTab } from '../components/tabs/DetectionTab';
import { ThermalTab } from '../components/tabs/ThermalTab';
import { StreamTab } from '../components/tabs/StreamTab';
import { ZonesTab } from '../components/tabs/ZonesTab';
import { LiveTab } from '../components/tabs/LiveTab';
import { RecordingTab } from '../components/tabs/RecordingTab';
import { EventsTab } from '../components/tabs/EventsTab';
import { AITab } from '../components/tabs/AITab';
import { TelegramTab } from '../components/tabs/TelegramTab';
import { AppearanceTab } from '../components/tabs/AppearanceTab';
import type { Settings as SettingsType } from '../types/api';

export const Settings: React.FC = () => {
  const { settings, loading, error, saveSettings } = useSettings();
  const [activeTab, setActiveTab] = useState<TabId>('cameras');
  const [localSettings, setLocalSettings] = useState<SettingsType | null>(null);

  React.useEffect(() => {
    if (settings) {
      setLocalSettings(settings);
    }
  }, [settings]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto mb-4"></div>
          <p className="text-muted">Loading settings...</p>
        </div>
      </div>
    );
  }

  if (error || !localSettings) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <p className="text-error mb-4">{error || 'Failed to load settings'}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const handleSave = async () => {
    const updates: Partial<SettingsType> = {};
    
    switch (activeTab) {
      case 'detection':
        updates.detection = localSettings.detection;
        break;
      case 'thermal':
        updates.thermal = localSettings.thermal;
        break;
      case 'stream':
        updates.stream = localSettings.stream;
        break;
      case 'live':
        updates.live = localSettings.live;
        break;
      case 'recording':
        updates.record = localSettings.record;
        break;
      case 'events':
        updates.event = localSettings.event;
        break;
      case 'ai':
        updates.ai = localSettings.ai;
        break;
      case 'telegram':
        updates.telegram = localSettings.telegram;
        break;
      case 'appearance':
        updates.appearance = localSettings.appearance;
        break;
    }

    const success = await saveSettings(updates);
    if (success) {
      setLocalSettings(settings);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#111A2E',
            color: '#E6EAF2',
            border: '1px solid #22304A',
          },
          success: {
            iconTheme: {
              primary: '#2ECC71',
              secondary: '#111A2E',
            },
          },
          error: {
            iconTheme: {
              primary: '#FF4D4F',
              secondary: '#111A2E',
            },
          },
        }}
      />

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-text mb-2">Settings</h1>
          <p className="text-muted">Configure detection, cameras, and notifications</p>
        </div>

        <div className="bg-surface1 border border-border rounded-lg p-6">
          <SettingsTabs activeTab={activeTab} onTabChange={setActiveTab} />

          <div className="mt-6">
            {activeTab === 'cameras' && <CamerasTab />}
            
            {activeTab === 'detection' && localSettings && (
              <DetectionTab
                config={localSettings.detection}
                onChange={(detection) => setLocalSettings({ ...localSettings, detection })}
                onSave={handleSave}
              />
            )}
            
            {activeTab === 'thermal' && localSettings && (
              <ThermalTab
                config={localSettings.thermal}
                onChange={(thermal) => setLocalSettings({ ...localSettings, thermal })}
                onSave={handleSave}
              />
            )}
            
            {activeTab === 'stream' && localSettings && (
              <StreamTab
                config={localSettings.stream}
                onChange={(stream) => setLocalSettings({ ...localSettings, stream })}
                onSave={handleSave}
              />
            )}
            
            {activeTab === 'zones' && <ZonesTab />}
            
            {activeTab === 'live' && localSettings && (
              <LiveTab
                config={localSettings.live}
                onChange={(live) => setLocalSettings({ ...localSettings, live })}
                onSave={handleSave}
              />
            )}
            
            {activeTab === 'recording' && localSettings && (
              <RecordingTab
                config={localSettings.record}
                onChange={(record) => setLocalSettings({ ...localSettings, record })}
                onSave={handleSave}
              />
            )}
            
            {activeTab === 'events' && localSettings && (
              <EventsTab
                config={localSettings.event}
                onChange={(event) => setLocalSettings({ ...localSettings, event })}
                onSave={handleSave}
              />
            )}
            
            {activeTab === 'ai' && localSettings && (
              <AITab
                config={localSettings.ai}
                onChange={(ai) => setLocalSettings({ ...localSettings, ai })}
                onSave={handleSave}
              />
            )}
            
            {activeTab === 'telegram' && localSettings && (
              <TelegramTab
                config={localSettings.telegram}
                onChange={(telegram) => setLocalSettings({ ...localSettings, telegram })}
                onSave={handleSave}
              />
            )}
            {activeTab === 'appearance' && (
              <AppearanceTab />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
