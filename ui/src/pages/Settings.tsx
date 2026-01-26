/**
 * Settings page - Main settings interface
 */
import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useSettings } from '../hooks/useSettings';
import { api } from '../services/api';
import { TabId } from '../components/SettingsTabs';
import { CamerasTab } from '../components/tabs/CamerasTab';
import { DetectionTab } from '../components/tabs/DetectionTab';
import { MotionTab } from '../components/tabs/MotionTab';
import { ThermalTab } from '../components/tabs/ThermalTab';
import { StreamTab } from '../components/tabs/StreamTab';
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
        case 'detection':
          updates.detection = localSettings.detection;
          break;
        case 'motion':
          updates.motion = localSettings.motion;
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

  const applyPerformancePreset = useCallback(async (preset: 'eco' | 'balanced' | 'quality') => {
    if (!localSettings) return;

    const baseDetection = localSettings.detection;
    const baseMotion = localSettings.motion;
    const baseThermal = localSettings.thermal;

    const updates: Partial<SettingsType> = (() => {
      if (preset === 'eco') {
        return {
          detection: {
            ...baseDetection,
            model: 'yolov8n-person',
            inference_fps: 3,
            inference_resolution: [512, 512],
            confidence_threshold: 0.35,
          },
          motion: {
            ...baseMotion,
            sensitivity: 6,
            min_area: 700,
            cooldown_seconds: 5,
          },
          thermal: {
            ...baseThermal,
            enable_enhancement: false,
          },
        };
      }
      if (preset === 'quality') {
        return {
          detection: {
            ...baseDetection,
            model: 'yolov9t',
            inference_fps: 7,
            inference_resolution: [640, 640],
            confidence_threshold: 0.25,
          },
          motion: {
            ...baseMotion,
            sensitivity: 8,
            min_area: 450,
            cooldown_seconds: 4,
          },
          thermal: {
            ...baseThermal,
            enable_enhancement: true,
            enhancement_method: 'clahe',
            clahe_clip_limit: 2.0,
          },
        };
      }
      return {
        detection: {
          ...baseDetection,
          model: 'yolov8s-person',
          inference_fps: 5,
          inference_resolution: [640, 640],
          confidence_threshold: 0.3,
        },
        motion: {
          ...baseMotion,
          sensitivity: 7,
          min_area: 500,
          cooldown_seconds: 5,
        },
        thermal: {
          ...baseThermal,
          enable_enhancement: true,
          enhancement_method: 'clahe',
          clahe_clip_limit: 2.0,
        },
      };
    })();

    const nextSettings = {
      ...localSettings,
      ...updates,
    } as SettingsType;

    updateLocalSettings(nextSettings);
    const saved = await saveSettings(updates);
    if (saved) {
      setLocalSettings(saved);
      setIsDirty(false);
    }
  }, [localSettings, saveSettings, updateLocalSettings]);

  const tabContent = useMemo(() => {
    if (activeTab === 'cameras') return <CamerasTab />
    if (activeTab === 'detection' && localSettings) {
      return (
        <DetectionTab
          config={localSettings.detection}
          onChange={(detection) => updateLocalSettings({ ...localSettings, detection })}
          onSave={handleSave}
        />
      )
    }
    if (activeTab === 'motion' && localSettings) {
      return (
        <MotionTab
          config={localSettings.motion}
          onChange={(motion) => updateLocalSettings({ ...localSettings, motion })}
          onSave={handleSave}
        />
      )
    }
    if (activeTab === 'thermal' && localSettings) {
      return (
        <ThermalTab
          config={localSettings.thermal}
          onChange={(thermal) => updateLocalSettings({ ...localSettings, thermal })}
          onSave={handleSave}
        />
      )
    }
    if (activeTab === 'stream' && localSettings) {
      return (
        <StreamTab
          config={localSettings.stream}
          onChange={(stream) => updateLocalSettings({ ...localSettings, stream })}
          onSave={handleSave}
        />
      )
    }
    if (activeTab === 'zones') return <ZonesTab />
    if (activeTab === 'live' && localSettings) {
      return (
        <LiveTab
          config={localSettings.live}
          onChange={(live) => updateLocalSettings({ ...localSettings, live })}
          onSave={handleSave}
        />
      )
    }
    if (activeTab === 'recording' && localSettings) {
      return (
        <RecordingTab
          config={localSettings.record}
          onChange={(record) => updateLocalSettings({ ...localSettings, record })}
          onSave={handleSave}
        />
      )
    }
    if (activeTab === 'events' && localSettings) {
      return (
        <EventsTab
          config={localSettings.event}
          onChange={(event) => updateLocalSettings({ ...localSettings, event })}
          onSave={handleSave}
        />
      )
    }
    if (activeTab === 'media' && localSettings) {
      return (
        <MediaTab
          config={localSettings.media}
          onChange={(media) => updateLocalSettings({ ...localSettings, media })}
          onSave={handleSave}
        />
      )
    }
    if (activeTab === 'ai' && localSettings) {
      return (
        <AITab
          config={localSettings.ai}
          onChange={(ai) => updateLocalSettings({ ...localSettings, ai })}
          onSave={handleSave}
        />
      )
    }
    if (activeTab === 'telegram' && localSettings) {
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
    if (activeTab === 'mqtt' && localSettings) {
      return <MqttTab />
    }
    if (activeTab === 'appearance') return <AppearanceTab />
    return null
  }, [activeTab, handleSave, localSettings, updateLocalSettings])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto mb-4"></div>
          <p className="text-muted">Ayarlar yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !localSettings) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <p className="text-error mb-4">{error || 'Ayarlar yüklenemedi'}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90"
          >
            Yeniden Dene
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="mb-8 flex items-start justify-between">
          <h1 className="text-3xl font-bold text-text mb-2">Settings</h1>
          <p className="text-muted">Configure detection, cameras, and notifications</p>
        </div>
        <div className="flex items-center gap-3 mb-6">
          {/* Export/Import kaldırıldı - kullanıcı karıştırıyor */}
          <button
            onClick={handleReset}
            className="px-4 py-2 bg-error text-white rounded-lg hover:bg-error/90 transition-colors"
          >
            Reset to Defaults
          </button>
        </div>

        <div className="bg-surface1 border border-border rounded-lg p-6 mb-6">
          <div className="flex flex-col gap-2 mb-4">
            <h2 className="text-lg font-semibold text-text">{t('perfPresetsTitle')}</h2>
            <p className="text-sm text-muted">{t('perfPresetsDesc')}</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button
              onClick={() => applyPerformancePreset('eco')}
              className="p-4 rounded-lg border border-border bg-surface2 text-left hover:bg-surface2/80 transition-colors"
            >
              <div className="font-semibold text-text">{t('perfPresetEcoTitle')}</div>
              <div className="text-xs text-muted mt-1">{t('perfPresetEcoDesc')}</div>
            </button>
            <button
              onClick={() => applyPerformancePreset('balanced')}
              className="p-4 rounded-lg border border-border bg-surface2 text-left hover:bg-surface2/80 transition-colors"
            >
              <div className="font-semibold text-text">{t('perfPresetBalancedTitle')}</div>
              <div className="text-xs text-muted mt-1">{t('perfPresetBalancedDesc')}</div>
            </button>
            <button
              onClick={() => applyPerformancePreset('quality')}
              className="p-4 rounded-lg border border-border bg-surface2 text-left hover:bg-surface2/80 transition-colors"
            >
              <div className="font-semibold text-text">{t('perfPresetQualityTitle')}</div>
              <div className="text-xs text-muted mt-1">{t('perfPresetQualityDesc')}</div>
            </button>
          </div>
          <p className="text-xs text-muted mt-3">{t('perfPresetNote')}</p>
        </div>

        <div className="bg-surface1 border border-border rounded-lg p-6">
          <div className="mt-0">{tabContent}</div>
        </div>
      </div>
    </div>
  );
};
