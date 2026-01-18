import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import api, { Config } from '../utils/api';

type TabKey = 'general' | 'motion' | 'rtsp' | 'ai' | 'notifications';

const tabs: { key: TabKey; label: string }[] = [
  { key: 'general', label: 'General' },
  { key: 'motion', label: 'Motion' },
  { key: 'rtsp', label: 'RTSP' },
  { key: 'ai', label: 'AI' },
  { key: 'notifications', label: 'Notifications' },
];

export function Settings() {
  const [config, setConfig] = useState<Config | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('general');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getConfig();
        setConfig(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load config');
      }
    };
    load();
  }, []);

  const updateSection = (section: keyof Config, field: string, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      [section]: {
        ...config[section],
        [field]: value,
      },
    });
  };

  const save = async () => {
    if (!config) return;
    try {
      setSaving(true);
      setError(null);
      const updated = await api.updateConfig(config);
      setConfig(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (!config) {
    return (
      <div class="space-y-4">
        <h1 class="text-lg font-semibold text-gray-200">Settings</h1>
        <Card>
          <p class="text-sm text-muted">Loading configuration...</p>
        </Card>
      </div>
    );
  }

  return (
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-lg font-semibold text-gray-200">Settings</h1>
          <p class="text-sm text-muted">Runtime configuration.</p>
        </div>
        <Button onClick={save} loading={saving}>Save</Button>
      </div>

      {error && (
        <Card>
          <p class="text-sm text-[#EF4444]">{error}</p>
        </Card>
      )}

      <Card>
        <div class="flex gap-2 flex-wrap">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              class={`chip ${activeTab === tab.key ? 'chip-info' : 'chip-muted'}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </Card>

      {activeTab === 'general' && (
        <Card title="General">
          <div class="grid gap-3 md:grid-cols-2">
            <label class="text-xs text-muted">
              Bind host
              <input
                class="input mt-1"
                value={config.general.bind_host}
                onInput={(e) => updateSection('general', 'bind_host', (e.target as HTMLInputElement).value)}
              />
            </label>
            <label class="text-xs text-muted">
              HTTP port
              <input
                class="input mt-1"
                type="number"
                value={config.general.http_port}
                onInput={(e) => updateSection('general', 'http_port', Number((e.target as HTMLInputElement).value))}
              />
            </label>
            <label class="text-xs text-muted md:col-span-2">
              Timezone
              <input
                class="input mt-1"
                value={config.general.timezone}
                onInput={(e) => updateSection('general', 'timezone', (e.target as HTMLInputElement).value)}
              />
            </label>
          </div>
        </Card>
      )}

      {activeTab === 'motion' && (
        <Card title="Motion">
          <div class="grid gap-3 md:grid-cols-2">
            <label class="text-xs text-muted">
              Sensitivity (1-10)
              <input
                class="input mt-1"
                type="number"
                min="1"
                max="10"
                value={config.motion.sensitivity}
                onInput={(e) => updateSection('motion', 'sensitivity', Number((e.target as HTMLInputElement).value))}
              />
            </label>
            <label class="text-xs text-muted">
              Min area
              <input
                class="input mt-1"
                type="number"
                value={config.motion.min_area}
                onInput={(e) => updateSection('motion', 'min_area', Number((e.target as HTMLInputElement).value))}
              />
            </label>
            <label class="text-xs text-muted">
              Cooldown (s)
              <input
                class="input mt-1"
                type="number"
                value={config.motion.cooldown_seconds}
                onInput={(e) => updateSection('motion', 'cooldown_seconds', Number((e.target as HTMLInputElement).value))}
              />
            </label>
          </div>
        </Card>
      )}

      {activeTab === 'rtsp' && (
        <Card title="RTSP">
          <div class="grid gap-3 md:grid-cols-2">
            <label class="text-xs text-muted md:col-span-2">
              RTSP URL (masked)
              <input
                class="input mt-1"
                type="password"
                value={config.camera.url}
                onInput={(e) => updateSection('camera', 'url', (e.target as HTMLInputElement).value)}
              />
            </label>
            <label class="text-xs text-muted">
              FPS
              <input
                class="input mt-1"
                type="number"
                value={config.camera.fps}
                onInput={(e) => updateSection('camera', 'fps', Number((e.target as HTMLInputElement).value))}
              />
            </label>
          </div>
        </Card>
      )}

      {activeTab === 'ai' && (
        <Card title="AI">
          <div class="grid gap-3 md:grid-cols-2">
            <label class="text-xs text-muted">
              Enabled
              <select
                class="input mt-1"
                value={config.llm.enabled ? 'true' : 'false'}
                onChange={(e) => updateSection('llm', 'enabled', (e.target as HTMLSelectElement).value === 'true')}
              >
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </label>
            <label class="text-xs text-muted md:col-span-2">
              OpenAI key (masked)
              <input
                class="input mt-1"
                type="password"
                value={config.llm.api_key}
                onInput={(e) => updateSection('llm', 'api_key', (e.target as HTMLInputElement).value)}
              />
            </label>
            <label class="text-xs text-muted">
              Model
              <input
                class="input mt-1"
                value={config.llm.model}
                onInput={(e) => updateSection('llm', 'model', (e.target as HTMLInputElement).value)}
              />
            </label>
            <label class="text-xs text-muted">
              Max tokens
              <input
                class="input mt-1"
                type="number"
                value={config.llm.max_tokens}
                onInput={(e) => updateSection('llm', 'max_tokens', Number((e.target as HTMLInputElement).value))}
              />
            </label>
          </div>
        </Card>
      )}

      {activeTab === 'notifications' && (
        <Card title="Notifications (Telegram)">
          <div class="grid gap-3 md:grid-cols-2">
            <label class="text-xs text-muted">
              Enabled
              <select
                class="input mt-1"
                value={config.telegram.enabled ? 'true' : 'false'}
                onChange={(e) => updateSection('telegram', 'enabled', (e.target as HTMLSelectElement).value === 'true')}
              >
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            </label>
            <label class="text-xs text-muted md:col-span-2">
              Bot token (masked)
              <input
                class="input mt-1"
                type="password"
                value={config.telegram.bot_token}
                onInput={(e) => updateSection('telegram', 'bot_token', (e.target as HTMLInputElement).value)}
              />
            </label>
            <label class="text-xs text-muted md:col-span-2">
              Chat IDs (comma-separated)
              <input
                class="input mt-1"
                value={config.telegram.chat_ids.join(',')}
                onInput={(e) => updateSection('telegram', 'chat_ids', (e.target as HTMLInputElement).value.split(',').map((id) => id.trim()).filter(Boolean))}
              />
            </label>
          </div>
        </Card>
      )}
    </div>
  );
}
