/**
 * Settings page - Main settings interface
 */
import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { useSettings } from '../hooks/useSettings';
import { api } from '../services/api';
import { TabId } from '../components/SettingsTabs';
import { CamerasTab } from '../components/tabs/CamerasTab';
import { CameraSettingsTab } from '../components/tabs/PerformanceTab';
import { ZonesTab } from '../components/tabs/ZonesTab';
import { LiveTab } from '../components/tabs/LiveTab';
import { RecordingTab } from '../components/tabs/RecordingTab';
import { EventsTab } from '../components/tabs/EventsTab';
import { MediaTab } from '../components/tabs/MediaTab';
import { AITab } from '../components/tabs/AITab';
import { TelegramTab } from '../components/tabs/TelegramTab';
import { MqttTab } from '../components/tabs/MqttTab';
import { AppearanceTab } from '../components/tabs/AppearanceTab';
import type { Settings as SettingsType } from '../types/api';

export const Settings: React.FC = () => {
  const { t } = useTranslation();
  const { settings, loading, error, saveSettings } = useSettings();
  const [searchParams] = useSearchParams();
  const defaultTab = (searchParams.get('tab') as TabId) || 'cameras';
  const [activeTab, setActiveTab] = useState<TabId>(defaultTab);
  const [localSettings, setLocalSettings] = useState<SettingsType | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  // Sync activeTab with URL
  useEffect(() => {
    const tab = searchParams.get('tab') as TabId;
    if (tab) {
      setActiveTab(tab);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [searchParams]);

  React.useEffect(() => {
    if (settings && !isDirty) {
      setLocalSettings(settings);
    }
  }, [settings, isDirty]);

  const updateLocalSettings = useCallback((next: SettingsType) => {
    setLocalSettings(next);
    setIsDirty(true);
  }, []);

  const handleSave = useCallback(async (override?: Partial<SettingsType> | React.SyntheticEvent) => {
    if (!localSettings) {
      return
    }
    if (override && typeof (override as React.SyntheticEvent).preventDefault === 'function') {
      override = undefined
    }
    const updates: Partial<SettingsType> = (override as Partial<SettingsType>) ?? {};
    
    if (!override) {
      switch (activeTab) {
        case 'camera_settings':
        case 'performance':
        case 'detection':
        case 'motion':
        case 'thermal':
        case 'stream':
          updates.detection = localSettings.detection;
          updates.motion = localSettings.motion;
          updates.thermal = localSettings.thermal;
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
        case 'media':
          updates.media = localSettings.media;
          break;
        case 'ai':
          updates.ai = localSettings.ai;
          break;
        case 'telegram':
          updates.telegram = localSettings.telegram;
          break;
        case 'mqtt':
          updates.mqtt = localSettings.mqtt;
          break;
        case 'appearance':
          updates.appearance = localSettings.appearance;
          break;
      }
    }

    const saved = await saveSettings(updates);
    if (saved) {
      setLocalSettings(saved);
      setIsDirty(false);
    }
  }, [activeTab, localSettings, saveSettings]);

  const handleReset = async () => {
    try {
      await api.resetSettings();
      window.location.reload();
    } catch (error) {
      console.error('Failed to reset settings:', error);
    }
  };

  const handleSavePartial = useCallback(async (updates: Partial<SettingsType>) => {
    const saved = await saveSettings(updates);
    if (saved) {
      setLocalSettings(saved);
      setIsDirty(false);
    }
  }, [saveSettings]);

  const normalizedTab = useMemo(() => {
    if (['performance', 'detection', 'motion', 'thermal', 'stream'].includes(activeTab)) {
      return 'camera_settings'
    }
    return activeTab
  }, [activeTab])

  const tabContent = useMemo(() => {
    if (normalizedTab === 'cameras') return <CamerasTab />
    if (normalizedTab === 'camera_settings' && localSettings) {
      return (
        <CameraSettingsTab
          settings={localSettings}
          onChange={updateLocalSettings}
          onSave={handleSavePartial}
        />
      )
    }
    if (normalizedTab === 'zones') return <ZonesTab />
    if (normalizedTab === 'live' && localSettings) {
      return (
        <LiveTab
          config={localSettings.live}
          onChange={(live) => updateLocalSettings({ ...localSettings, live })}
          onSave={handleSave}
        />
      )
    }
    if (normalizedTab === 'recording' && localSettings) {
      return (
        <RecordingTab
          config={localSettings.record}
          onChange={(record) => updateLocalSettings({ ...localSettings, record })}
          onSave={handleSave}
        />
      )
    }
    if (normalizedTab === 'events' && localSettings) {
      return (
        <EventsTab
          config={localSettings.event}
          onChange={(event) => updateLocalSettings({ ...localSettings, event })}
          onSave={handleSave}
        />
      )
    }
    if (normalizedTab === 'media' && localSettings) {
      return (
        <MediaTab
          config={localSettings.media}
          onChange={(media) => updateLocalSettings({ ...localSettings, media })}
          onSave={handleSave}
        />
      )
    }
    if (normalizedTab === 'ai' && localSettings) {
      return (
        <AITab
          config={localSettings.ai}
          onChange={(ai) => updateLocalSettings({ ...localSettings, ai })}
          onSave={handleSave}
        />
      )
    }
    if (normalizedTab === 'telegram' && localSettings) {
      return (
        <TelegramTab
          config={localSettings.telegram}
          onChange={(telegram) => updateLocalSettings({ ...localSettings, telegram })}
          onSave={(nextTelegram) =>
            handleSave({ telegram: nextTelegram ?? localSettings.telegram })
          }
        />
      )
    }
    if (normalizedTab === 'mqtt' && localSettings) {
      return <MqttTab />
    }
    if (normalizedTab === 'appearance') return <AppearanceTab />
    return null
  }, [handleSave, handleSavePartial, localSettings, normalizedTab, updateLocalSettings])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto mb-4"></div>
          <p className="text-muted">{t('loadingSettings')}</p>
        </div>
      </div>
    );
  }

  if (error || !localSettings) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <p className="text-error mb-4">{error || t('settingsLoadFailed')}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90"
          >
            {t('retry')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-8 flex items-start justify-between">
          <h1 className="text-3xl font-bold text-text mb-2">{t('settingsTitle')}</h1>
          <p className="text-muted">{t('settingsSubtitle')}</p>
        </div>
        <div className="flex items-center gap-3 mb-6">
          {/* Export/Import kaldırıldı - kullanıcı karıştırıyor */}
          <button
            onClick={handleReset}
            className="px-4 py-2 bg-error text-white rounded-lg hover:bg-error/90 transition-colors"
          >
            {t('resetDefaults')}
          </button>
        </div>

        <div className="bg-surface1 border border-border rounded-lg p-6">
          <div className="mt-0">{tabContent}</div>
        </div>
      </div>
    </div>
  );
};
