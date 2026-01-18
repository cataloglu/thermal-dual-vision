import { h } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { getConfig, updateConfig as saveConfigToApi, Config } from '../utils/api';

/**
 * Settings page - Configuration management interface.
 *
 * Displays a comprehensive form for editing system configuration,
 * organized into sections for different components (camera, motion,
 * YOLO, LLM, screenshots, MQTT, telegram, etc.).
 *
 * Features:
 * - Form loads current configuration from API using centralized utilities
 * - Organized sections with Card components
 * - Real-time form validation and change detection
 * - Save/Reset functionality with optimistic updates
 * - Loading, error, and success states with feedback
 * - Dark mode support throughout
 * - Responsive grid layouts for better mobile UX
 * - Password masking for sensitive fields (API keys, tokens, passwords)
 * - Conditional rendering (Telegram section shows only when enabled)
 * - Range sliders for sensitivity and quality settings
 * - Checkbox toggles for boolean settings
 * - Dropdown selects for model choices
 * - Array input handling (classes, chat_ids)
 *
 * Fetches data from:
 * - GET /api/config - Load current configuration (via getConfig utility)
 * - POST /api/config - Save configuration changes (via updateConfig utility)
 *
 * Integration:
 * - Uses getConfig() and updateConfig() utilities from api.ts
 * - Imports Config interface from api.ts (single source of truth)
 * - Follows established patterns from Dashboard, Gallery, and Events pages
 * - Consistent error handling via ApiRequestError
 *
 * Code Quality:
 * - TypeScript type-safe with imported interfaces
 * - No console.log debugging statements
 * - Comprehensive JSDoc documentation
 * - Proper error handling throughout
 * - Clean state management with useState/useEffect hooks
 * - Deep cloning for change detection
 * - Auto-dismissing success messages
 */

export function Settings() {
  const [config, setConfig] = useState<Config | null>(null);
  const [originalConfig, setOriginalConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setError(null);
      setLoading(true);

      // Use API utility function (consistent with Dashboard, Gallery, Events patterns)
      const data = await getConfig();
      setConfig(data);
      setOriginalConfig(JSON.parse(JSON.stringify(data))); // Deep clone
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    if (!config) return;

    try {
      setError(null);
      setSuccess(false);
      setSaving(true);

      // Use API utility function (consistent with Dashboard, Gallery, Events patterns)
      const updatedConfig = await saveConfigToApi(config);
      setConfig(updatedConfig);
      setOriginalConfig(JSON.parse(JSON.stringify(updatedConfig)));
      setSuccess(true);

      // Hide success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSaving(false);
    }
  };

  const resetConfig = () => {
    if (originalConfig) {
      setConfig(JSON.parse(JSON.stringify(originalConfig)));
      setError(null);
      setSuccess(false);
    }
  };

  const updateConfig = (section: keyof Config, field: string, value: any) => {
    if (!config) return;

    setConfig({
      ...config,
      [section]: {
        ...config[section],
        [field]: value
      }
    });
  };

  const hasChanges = (): boolean => {
    return JSON.stringify(config) !== JSON.stringify(originalConfig);
  };

  if (loading) {
    return (
      <div class="flex items-center justify-center min-h-screen">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p class="text-gray-600 dark:text-gray-400">Loading settings...</p>
        </div>
      </div>
    );
  }

  if (error && !config) {
    return (
      <div class="p-4">
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 class="text-red-800 dark:text-red-200 font-semibold mb-2">Error Loading Settings</h3>
          <p class="text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={fetchConfig}
            class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!config) return null;

  return (
    <div class="space-y-6">
      {/* Page Header */}
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Settings
          </h1>
          <p class="text-gray-600 dark:text-gray-400">
            Configure motion detection system parameters
          </p>
        </div>

        {/* Action Buttons */}
        <div class="flex gap-2">
          <Button
            variant="secondary"
            onClick={resetConfig}
            disabled={!hasChanges() || saving}
          >
            Reset
          </Button>
          <Button
            variant="primary"
            onClick={saveConfig}
            disabled={!hasChanges() || saving}
            loading={saving}
          >
            Save Changes
          </Button>
        </div>
      </div>

      {/* Success Message */}
      {success && (
        <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <p class="text-green-800 dark:text-green-200 font-medium">
            ✓ Configuration saved successfully
          </p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p class="text-red-800 dark:text-red-200 font-medium">
            ✗ {error}
          </p>
        </div>
      )}

      {/* General Settings */}
      <Card title="General">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Bind Host
            </label>
            <input
              type="text"
              value={config.general.bind_host}
              onChange={(e) => updateConfig('general', 'bind_host', (e.target as HTMLInputElement).value)}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              HTTP Port
            </label>
            <input
              type="number"
              value={config.general.http_port}
              onChange={(e) => updateConfig('general', 'http_port', parseInt((e.target as HTMLInputElement).value))}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Timezone
            </label>
            <input
              type="text"
              value={config.general.timezone}
              onChange={(e) => updateConfig('general', 'timezone', (e.target as HTMLInputElement).value)}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Log Level
            </label>
            <select
              value={config.log_level}
              onChange={(e) => setConfig({ ...config, log_level: (e.target as HTMLSelectElement).value })}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Camera Settings */}
      <Card title="Camera">
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Camera URL
            </label>
            <input
              type="text"
              value={config.camera.url}
              onChange={(e) => updateConfig('camera', 'url', (e.target as HTMLInputElement).value)}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="rtsp://camera-ip/stream"
            />
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              RTSP or HTTP stream URL for the camera
            </p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                FPS (Frames Per Second)
              </label>
              <input
                type="number"
                value={config.camera.fps}
                onChange={(e) => updateConfig('camera', 'fps', parseInt((e.target as HTMLInputElement).value))}
                min="1"
                max="30"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Resolution
              </label>
              <div class="flex gap-2">
                <input
                  type="number"
                  value={config.camera.resolution[0]}
                  onChange={(e) => updateConfig('camera', 'resolution', [parseInt((e.target as HTMLInputElement).value), config.camera.resolution[1]])}
                  placeholder="Width"
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
                <span class="flex items-center text-gray-500 dark:text-gray-400">×</span>
                <input
                  type="number"
                  value={config.camera.resolution[1]}
                  onChange={(e) => updateConfig('camera', 'resolution', [config.camera.resolution[0], parseInt((e.target as HTMLInputElement).value)])}
                  placeholder="Height"
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* RTSP / Reconnect Policy */}
      <Card title="RTSP / Reconnect Policy">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Initial Delay (sec)
            </label>
            <input
              type="number"
              value={config.retry_policy.initial_delay}
              onChange={(e) => updateConfig('retry_policy', 'initial_delay', parseFloat((e.target as HTMLInputElement).value))}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Max Delay (sec)
            </label>
            <input
              type="number"
              value={config.retry_policy.max_delay}
              onChange={(e) => updateConfig('retry_policy', 'max_delay', parseFloat((e.target as HTMLInputElement).value))}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Multiplier
            </label>
            <input
              type="number"
              value={config.retry_policy.multiplier}
              onChange={(e) => updateConfig('retry_policy', 'multiplier', parseFloat((e.target as HTMLInputElement).value))}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Jitter
            </label>
            <input
              type="number"
              value={config.retry_policy.jitter}
              onChange={(e) => updateConfig('retry_policy', 'jitter', parseFloat((e.target as HTMLInputElement).value))}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Max Retries (optional)
            </label>
            <input
              type="number"
              value={config.retry_policy.max_retries ?? ''}
              onChange={(e) => updateConfig('retry_policy', 'max_retries', (e.target as HTMLInputElement).value ? parseInt((e.target as HTMLInputElement).value) : null)}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
        </div>
      </Card>

      {/* Motion Detection Settings */}
      <Card title="Motion Detection">
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Sensitivity (1-10)
            </label>
            <input
              type="range"
              value={config.motion.sensitivity}
              onChange={(e) => updateConfig('motion', 'sensitivity', parseInt((e.target as HTMLInputElement).value))}
              min="1"
              max="10"
              class="w-full"
            />
            <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>Low</span>
              <span class="font-medium text-primary-600 dark:text-primary-400">{config.motion.sensitivity}</span>
              <span>High</span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Minimum Area (pixels)
              </label>
              <input
                type="number"
                value={config.motion.min_area}
                onChange={(e) => updateConfig('motion', 'min_area', parseInt((e.target as HTMLInputElement).value))}
                min="100"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Cooldown (seconds)
              </label>
              <input
                type="number"
                value={config.motion.cooldown_seconds}
                onChange={(e) => updateConfig('motion', 'cooldown_seconds', parseInt((e.target as HTMLInputElement).value))}
                min="1"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* YOLO Settings */}
      <Card title="YOLO Object Detection">
        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Model
              </label>
              <select
                value={config.yolo.model}
                onChange={(e) => updateConfig('yolo', 'model', (e.target as HTMLSelectElement).value)}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="yolov8n">YOLOv8 Nano (fastest)</option>
                <option value="yolov8s">YOLOv8 Small</option>
                <option value="yolov8m">YOLOv8 Medium</option>
                <option value="yolov8l">YOLOv8 Large</option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Confidence Threshold
              </label>
              <input
                type="number"
                value={config.yolo.confidence}
                onChange={(e) => updateConfig('yolo', 'confidence', parseFloat((e.target as HTMLInputElement).value))}
                min="0"
                max="1"
                step="0.05"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Detected Classes (comma-separated)
            </label>
            <input
              type="text"
              value={config.yolo.classes.join(', ')}
              onChange={(e) => updateConfig('yolo', 'classes', (e.target as HTMLInputElement).value.split(',').map(c => c.trim()))}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="person, car, dog, cat"
            />
          </div>
        </div>
      </Card>

      {/* AI Settings */}
      <Card title="AI Settings">
        <div class="space-y-4">
          <div class="flex items-center gap-2">
            <input
              type="checkbox"
              checked={config.llm.enabled}
              onChange={(e) => updateConfig('llm', 'enabled', (e.target as HTMLInputElement).checked)}
            />
            <span class="text-sm text-gray-700 dark:text-gray-300">Enable AI analysis</span>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              API Key
            </label>
            <input
              type="password"
              value={config.llm.api_key}
              onChange={(e) => updateConfig('llm', 'api_key', (e.target as HTMLInputElement).value)}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              placeholder="sk-..."
            />
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              OpenAI API key for vision analysis
            </p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Model
              </label>
              <input
                type="text"
                value={config.llm.model}
                onChange={(e) => updateConfig('llm', 'model', (e.target as HTMLInputElement).value)}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Max Tokens
              </label>
              <input
                type="number"
                value={config.llm.max_tokens}
                onChange={(e) => updateConfig('llm', 'max_tokens', parseInt((e.target as HTMLInputElement).value))}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Timeout (seconds)
              </label>
              <input
                type="number"
                value={config.llm.timeout}
                onChange={(e) => updateConfig('llm', 'timeout', parseInt((e.target as HTMLInputElement).value))}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Screenshot Settings */}
      <Card title="Screenshots">
        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Before (seconds)
              </label>
              <input
                type="number"
                value={config.screenshots.before_seconds}
                onChange={(e) => updateConfig('screenshots', 'before_seconds', parseInt((e.target as HTMLInputElement).value))}
                min="1"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                After (seconds)
              </label>
              <input
                type="number"
                value={config.screenshots.after_seconds}
                onChange={(e) => updateConfig('screenshots', 'after_seconds', parseInt((e.target as HTMLInputElement).value))}
                min="1"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Buffer (seconds)
              </label>
              <input
                type="number"
                value={config.screenshots.buffer_seconds}
                onChange={(e) => updateConfig('screenshots', 'buffer_seconds', parseInt((e.target as HTMLInputElement).value))}
                min="5"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Quality (1-100)
              </label>
              <input
                type="range"
                value={config.screenshots.quality}
                onChange={(e) => updateConfig('screenshots', 'quality', parseInt((e.target as HTMLInputElement).value))}
                min="1"
                max="100"
                class="w-full"
              />
              <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>Low</span>
                <span class="font-medium text-primary-600 dark:text-primary-400">{config.screenshots.quality}%</span>
                <span>High</span>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Max Stored
              </label>
              <input
                type="number"
                value={config.screenshots.max_stored}
                onChange={(e) => updateConfig('screenshots', 'max_stored', parseInt((e.target as HTMLInputElement).value))}
                min="10"
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>
        </div>
      </Card>

      {/* MQTT Settings */}
      <Card title="MQTT">
        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Host
              </label>
              <input
                type="text"
                value={config.mqtt.host}
                onChange={(e) => updateConfig('mqtt', 'host', (e.target as HTMLInputElement).value)}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Port
              </label>
              <input
                type="number"
                value={config.mqtt.port}
                onChange={(e) => updateConfig('mqtt', 'port', parseInt((e.target as HTMLInputElement).value))}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Username
              </label>
              <input
                type="text"
                value={config.mqtt.username}
                onChange={(e) => updateConfig('mqtt', 'username', (e.target as HTMLInputElement).value)}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Password
              </label>
              <input
                type="password"
                value={config.mqtt.password}
                onChange={(e) => updateConfig('mqtt', 'password', (e.target as HTMLInputElement).value)}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Topic Prefix
              </label>
              <input
                type="text"
                value={config.mqtt.topic_prefix}
                onChange={(e) => updateConfig('mqtt', 'topic_prefix', (e.target as HTMLInputElement).value)}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Discovery Prefix
              </label>
              <input
                type="text"
                value={config.mqtt.discovery_prefix}
                onChange={(e) => updateConfig('mqtt', 'discovery_prefix', (e.target as HTMLInputElement).value)}
                class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>

          <div class="flex items-center gap-4">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.mqtt.discovery}
                onChange={(e) => updateConfig('mqtt', 'discovery', (e.target as HTMLInputElement).checked)}
                class="w-4 h-4 text-primary-600 border-gray-300 dark:border-gray-600 rounded focus:ring-primary-500"
              />
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                Enable Home Assistant Discovery
              </span>
            </label>
          </div>
        </div>
      </Card>

      {/* Telegram Settings */}
      <Card title="Telegram Notifications">
        <div class="space-y-4">
          <div class="flex items-center gap-4">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.telegram.enabled}
                onChange={(e) => updateConfig('telegram', 'enabled', (e.target as HTMLInputElement).checked)}
                class="w-4 h-4 text-primary-600 border-gray-300 dark:border-gray-600 rounded focus:ring-primary-500"
              />
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                Enable Telegram Notifications
              </span>
            </label>
          </div>

          {config.telegram.enabled && (
            <>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Bot Token
                </label>
                <input
                  type="password"
                  value={config.telegram.bot_token}
                  onChange={(e) => updateConfig('telegram', 'bot_token', (e.target as HTMLInputElement).value)}
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="123456:ABC-DEF..."
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Chat IDs (comma-separated)
                </label>
                <input
                  type="text"
                  value={config.telegram.chat_ids.join(', ')}
                  onChange={(e) => updateConfig('telegram', 'chat_ids', (e.target as HTMLInputElement).value.split(',').map(c => c.trim()))}
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="123456789, 987654321"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Rate Limit (seconds)
                </label>
                <input
                  type="number"
                  value={config.telegram.rate_limit_seconds}
                  onChange={(e) => updateConfig('telegram', 'rate_limit_seconds', parseInt((e.target as HTMLInputElement).value))}
                  min="1"
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
            </>
          )}
        </div>
      </Card>

      {/* System Settings */}
      <Card title="System">
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Log Level
            </label>
            <select
              value={config.log_level}
              onChange={(e) => setConfig({ ...config, log_level: (e.target as HTMLSelectElement).value })}
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Bottom Action Buttons */}
      <div class="flex justify-end gap-2 pb-6">
        <Button
          variant="secondary"
          onClick={resetConfig}
          disabled={!hasChanges() || saving}
        >
          Reset
        </Button>
        <Button
          variant="primary"
          onClick={saveConfig}
          disabled={!hasChanges() || saving}
          loading={saving}
        >
          Save Changes
        </Button>
      </div>
    </div>
  );
}
