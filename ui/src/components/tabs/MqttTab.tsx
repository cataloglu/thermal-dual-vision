import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../services/api';
import type { MqttConfig } from '../../types/api';

interface MqttStatus {
  enabled: boolean;
  connected: boolean;
  broker: string;
  topic_prefix: string;
  availability_topic: string;
  connected_at: string | null;
  active_topics: string[];
  publish_count: number;
  last_messages: Record<string, { payload: string; timestamp: string }>;
  last_error: string | null;
}

interface MqttTabProps {
  config: MqttConfig;
  onChange: (config: MqttConfig) => void;
  onSave: (nextConfig?: MqttConfig) => void;
}

export function MqttTab({ config, onChange, onSave }: MqttTabProps) {
  const MASKED_VALUE = '***REDACTED***'
  const { t } = useTranslation();
  const [mqttStatus, setMqttStatus] = useState<MqttStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [cameras, setCameras] = useState<any[]>([]);
  const [passwordDraft, setPasswordDraft] = useState('');
  const [passwordTouched, setPasswordTouched] = useState(false);

  // Fetch cameras for sensor list
  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const response = await api.getCameras();
        setCameras(response.cameras || []);
      } catch (error) {
        console.error('Failed to fetch cameras:', error);
      }
    };
    fetchCameras();
  }, []);

  // Fetch MQTT status
  useEffect(() => {
    if (!config.enabled) {
      setMqttStatus(null);
      return;
    }

    const fetchStatus = async () => {
      try {
        setStatusLoading(true);
        const data = await api.getMqttStatus();
        setMqttStatus(data);
      } catch (error) {
        console.error('Failed to fetch MQTT status:', error);
      } finally {
        setStatusLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Refresh every 5s

    return () => clearInterval(interval);
  }, [config.enabled]);

  useEffect(() => {
    if (config.password && config.password !== MASKED_VALUE) {
      setPasswordDraft(config.password);
      setPasswordTouched(true);
      return;
    }
    if (!passwordTouched) {
      setPasswordDraft('');
    }
  }, [config.password, passwordTouched]);

  const handleMqttChange = (key: string, value: any) => {
    onChange({
      ...config,
      [key]: value,
    });
  };

  const handlePasswordChange = (value: string) => {
    setPasswordTouched(true);
    setPasswordDraft(value);
    onChange({
      ...config,
      password: value,
    });
  };

  const hasPassword = Boolean(config.password)
  const isPasswordMasked = config.password === MASKED_VALUE
  const passwordValue = passwordTouched ? passwordDraft : (isPasswordMasked ? '' : config.password || '')

  return (
    <div className="space-y-6">
      <div className="bg-card p-6 rounded-lg border border-border">
        <h3 className="text-lg font-medium text-foreground mb-4">
          {t('haMqtt')}
        </h3>

        <div className="space-y-4">
          {/* Enabled Toggle */}
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-foreground">
              {t('mqttEnabled')}
            </label>
            <button
              onClick={() => handleMqttChange('enabled', !config.enabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                config.enabled ? 'bg-primary' : 'bg-muted'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  config.enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                {t('brokerHost')}
              </label>
              <input
                type="text"
                value={config.host}
                onChange={(e) => handleMqttChange('host', e.target.value)}
                placeholder="core-mosquitto"
                className="w-full bg-background border border-border rounded px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <p className="text-xs text-muted-foreground mt-1">
                {t('haDefault')}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                {t('port')}
              </label>
              <input
                type="number"
                value={config.port}
                onChange={(e) => handleMqttChange('port', parseInt(e.target.value))}
                className="w-full bg-background border border-border rounded px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                {t('username')}
              </label>
              <input
                type="text"
                value={config.username || ''}
                onChange={(e) => handleMqttChange('username', e.target.value)}
                className="w-full bg-background border border-border rounded px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                {t('password')}
              </label>
              <input
                type="password"
                value={passwordValue}
                onChange={(e) => handlePasswordChange(e.target.value)}
                placeholder={hasPassword ? '******' : ''}
                className="w-full bg-background border border-border rounded px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            
             <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">
                {t('topicPrefix')}
              </label>
              <input
                type="text"
                value={config.topic_prefix}
                onChange={(e) => handleMqttChange('topic_prefix', e.target.value)}
                className="w-full bg-background border border-border rounded px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
        </div>
      </div>
      
      <div className="bg-card p-6 rounded-lg border border-border">
         <h3 className="text-lg font-medium text-foreground mb-4">
           {t('haStatus')}
         </h3>
         <p className="text-sm text-muted-foreground">
           {t('haStatusDesc')}
         </p>
      </div>

      {/* MQTT Monitoring (NEW) */}
      {config.enabled && (
        <div className="bg-card p-6 rounded-lg border border-border">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-foreground">
              📊 MQTT Monitoring (v2.2)
            </h3>
            {mqttStatus && (
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                mqttStatus.connected 
                  ? 'bg-green-500/20 text-green-500'
                  : 'bg-red-500/20 text-red-500'
              }`}>
                {mqttStatus.connected ? '🟢 Connected' : '🔴 Disconnected'}
              </span>
            )}
          </div>

          {statusLoading && !mqttStatus ? (
            <div className="text-sm text-muted-foreground">Loading MQTT status...</div>
          ) : mqttStatus ? (
            <div className="space-y-4">
              {/* Connection Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-background rounded-lg border border-border">
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Broker</div>
                  <div className="text-sm font-mono text-foreground">{mqttStatus.broker}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Topic Prefix</div>
                  <div className="text-sm font-mono text-foreground">{mqttStatus.topic_prefix}</div>
                </div>
                {mqttStatus.connected_at && (
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">Connected At</div>
                    <div className="text-sm text-foreground">
                      {new Date(mqttStatus.connected_at).toLocaleString()}
                    </div>
                  </div>
                )}
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Messages Published</div>
                  <div className="text-sm font-semibold text-foreground">{mqttStatus.publish_count}</div>
                </div>
              </div>

              {/* Active Topics */}
              <div>
                <h4 className="text-sm font-semibold text-foreground mb-2">
                  Active Topics ({mqttStatus.active_topics.length})
                </h4>
                <div className="max-h-48 overflow-y-auto space-y-1 p-3 bg-background rounded-lg border border-border">
                  {mqttStatus.active_topics.length > 0 ? (
                    mqttStatus.active_topics.map((topic) => (
                      <div key={topic} className="text-xs font-mono text-muted-foreground">
                        📤 {topic}
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-muted-foreground">No topics published yet</div>
                  )}
                </div>
              </div>

              {/* Last Messages */}
              <div>
                <h4 className="text-sm font-semibold text-foreground mb-2">
                  Recent Messages (Last 10)
                </h4>
                <div className="max-h-64 overflow-y-auto space-y-2">
                  {Object.entries(mqttStatus.last_messages).length > 0 ? (
                    Object.entries(mqttStatus.last_messages).map(([topic, msg]) => (
                      <div key={topic} className="p-3 bg-background rounded-lg border border-border">
                        <div className="flex items-start justify-between mb-1">
                          <div className="text-xs font-mono text-foreground font-semibold truncate flex-1">
                            {topic}
                          </div>
                          <div className="text-xs text-muted-foreground ml-2 whitespace-nowrap">
                            {new Date(msg.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                        <div className="text-xs font-mono text-muted-foreground bg-surface1 p-2 rounded overflow-x-auto">
                          {typeof msg.payload === 'string' 
                            ? msg.payload.substring(0, 200)
                            : JSON.stringify(msg.payload).substring(0, 200)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-muted-foreground p-3 bg-background rounded-lg border border-border">
                      No messages yet
                    </div>
                  )}
                </div>
              </div>

              {/* Error Display */}
              {mqttStatus.last_error && (
                <div className="p-3 bg-red-500/10 border border-red-500 rounded-lg">
                  <div className="text-sm font-semibold text-red-500 mb-1">Last Error</div>
                  <div className="text-xs text-red-400 font-mono">{mqttStatus.last_error}</div>
                </div>
              )}

              {/* HA Sensor List */}
              <div className="mt-6">
                <h4 className="text-sm font-semibold text-foreground mb-2">
                  🏠 Home Assistant Sensor'ları (Auto-Discovery)
                </h4>
                <div className="p-4 bg-background rounded-lg border border-border">
                  <div className="space-y-2 text-xs">
                    {cameras && cameras.length > 0 ? (
                      cameras.map((cam: any) => (
                        <div key={cam.id} className="p-2 bg-surface1 rounded border-l-2 border-accent">
                          <div className="font-semibold text-foreground mb-1">{cam.name}</div>
                          <div className="space-y-0.5 text-muted-foreground font-mono">
                            <div>🔴 binary_sensor.{cam.name.toLowerCase().replace(/\s+/g, '_')}_person_detected</div>
                            <div>🔢 sensor.{cam.name.toLowerCase().replace(/\s+/g, '_')}_person_count</div>
                            <div>📝 sensor.{cam.name.toLowerCase().replace(/\s+/g, '_')}_last_event</div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-muted-foreground">No cameras configured</div>
                    )}
                  </div>
                  <div className="mt-3 p-2 bg-info/10 border border-info rounded text-xs text-info">
                    💡 Bu sensor'ları Home Assistant → Settings → Devices & Services → MQTT'de bulabilirsiniz
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              Enable MQTT to see monitoring info
            </div>
          )}
        </div>
      )}

      <button
        onClick={() => onSave(config)}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('save')}
      </button>
    </div>
  );
}
