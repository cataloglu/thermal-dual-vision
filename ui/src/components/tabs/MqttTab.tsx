import { useSettings } from '../../hooks/useSettings';
import { LoadingState } from '../LoadingState';
import { useTranslation } from 'react-i18next';

export function MqttTab() {
  const MASKED_VALUE = '***REDACTED***'
  // Fix: use saveSettings instead of updateSettings
  const { settings, saveSettings, loading } = useSettings();
  const { t } = useTranslation();

  if (loading || !settings) return <LoadingState />;

  const handleMqttChange = (key: string, value: any) => {
    saveSettings({
      mqtt: {
        ...settings.mqtt,
        [key]: value
      }
    });
  };

  const hasPassword = Boolean(settings.mqtt.password)
  const passwordValue =
    settings.mqtt.password === MASKED_VALUE ? '' : settings.mqtt.password || ''

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
              onClick={() => handleMqttChange('enabled', !settings.mqtt.enabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                settings.mqtt.enabled ? 'bg-primary' : 'bg-muted'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings.mqtt.enabled ? 'translate-x-6' : 'translate-x-1'
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
                value={settings.mqtt.host}
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
                value={settings.mqtt.port}
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
                value={settings.mqtt.username || ''}
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
                onChange={(e) => handleMqttChange('password', e.target.value)}
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
                value={settings.mqtt.topic_prefix}
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
    </div>
  );
}
