import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import {
  getTelegramSettings,
  updateTelegramSettings,
  sendTelegramTestMessage,
  sendTelegramTestSnapshot,
  getCameras,
  TelegramConfig,
  Camera,
} from '../utils/api';

const EVENT_OPTIONS = [
  { id: 'motion_detected', label: 'Motion detected' },
  { id: 'ai_verified', label: 'AI verified' },
  { id: 'system_error', label: 'System error' },
  { id: 'pipeline_reconnect', label: 'Pipeline reconnect' },
  { id: 'pipeline_down', label: 'Pipeline down' },
];

export function Notifications() {
  const [settings, setSettings] = useState<TelegramConfig | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [cameraId, setCameraId] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchSettings();
    fetchCameras();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await getTelegramSettings();
      setSettings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    }
  };

  const fetchCameras = async () => {
    try {
      const data = await getCameras();
      setCameras(data.cameras || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cameras');
    }
  };

  const updateSettings = (field: keyof TelegramConfig, value: any) => {
    if (!settings) return;
    setSettings({ ...settings, [field]: value });
  };

  const toggleEvent = (eventId: string) => {
    if (!settings) return;
    const current = new Set(settings.event_types || []);
    if (current.has(eventId)) {
      current.delete(eventId);
    } else {
      current.add(eventId);
    }
    updateSettings('event_types', Array.from(current));
  };

  const saveSettings = async () => {
    if (!settings) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateTelegramSettings(settings);
      setSettings(updated);
      setSuccess('Settings saved');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const sendTestMessage = async () => {
    setError(null);
    setSuccess(null);
    try {
      await sendTelegramTestMessage();
      setSuccess('Test message sent');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send test message');
    }
  };

  const sendTestSnapshot = async () => {
    if (!cameraId) {
      setError('Select a camera first');
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      await sendTelegramTestSnapshot(cameraId);
      setSuccess('Test snapshot sent');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send test snapshot');
    }
  };

  if (!settings) {
    return (
      <div class="flex items-center justify-center min-h-screen">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p class="text-gray-600 dark:text-gray-400">Loading notifications...</p>
        </div>
      </div>
    );
  }

  return (
    <div class="space-y-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Notifications</h1>
        <p class="text-gray-600 dark:text-gray-400">Configure Telegram alerts and tests.</p>
      </div>

      {error && (
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
          {error}
        </div>
      )}
      {success && (
        <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 text-green-700 dark:text-green-300">
          {success}
        </div>
      )}

      <Card title="Telegram Settings">
        <div class="space-y-4">
          <div class="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings.enabled}
              onChange={(e) => updateSettings('enabled', (e.target as HTMLInputElement).checked)}
            />
            <span class="text-sm text-gray-700 dark:text-gray-300">Enable Telegram notifications</span>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Bot Token
            </label>
            <input
              type="password"
              value={settings.bot_token}
              onChange={(e) => updateSettings('bot_token', (e.target as HTMLInputElement).value)}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Chat IDs (comma-separated)
            </label>
            <input
              type="text"
              value={settings.chat_ids.join(', ')}
              onChange={(e) => updateSettings('chat_ids', (e.target as HTMLInputElement).value.split(',').map((id) => id.trim()))}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Event Types
            </label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
              {EVENT_OPTIONS.map((option) => (
                <label key={option.id} class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <input
                    type="checkbox"
                    checked={settings.event_types?.includes(option.id)}
                    onChange={() => toggleEvent(option.id)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Cooldown (sec)
              </label>
              <input
                type="number"
                value={settings.cooldown_seconds}
                onChange={(e) => updateSettings('cooldown_seconds', parseInt((e.target as HTMLInputElement).value))}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Max messages / min
              </label>
              <input
                type="number"
                value={settings.max_messages_per_min}
                onChange={(e) => updateSettings('max_messages_per_min', parseInt((e.target as HTMLInputElement).value))}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Include snapshot
              </label>
              <input
                type="checkbox"
                checked={settings.send_images}
                onChange={(e) => updateSettings('send_images', (e.target as HTMLInputElement).checked)}
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Snapshot quality
              </label>
              <input
                type="number"
                value={settings.snapshot_quality}
                onChange={(e) => updateSettings('snapshot_quality', parseInt((e.target as HTMLInputElement).value))}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>
          <button
            onClick={saveSettings}
            disabled={saving}
            class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save settings'}
          </button>
        </div>
      </Card>

      <Card title="Test Tools">
        <div class="space-y-3">
          <button
            onClick={sendTestMessage}
            class="px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg"
          >
            Send test message
          </button>
          <div class="flex flex-col md:flex-row gap-2">
            <select
              value={cameraId}
              onChange={(e) => setCameraId((e.target as HTMLSelectElement).value)}
              class="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
            >
              <option value="">Select camera</option>
              {cameras.map((camera) => (
                <option key={camera.id} value={camera.id}>
                  {camera.name}
                </option>
              ))}
            </select>
            <button
              onClick={sendTestSnapshot}
              class="px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg"
            >
              Send test snapshot
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}
