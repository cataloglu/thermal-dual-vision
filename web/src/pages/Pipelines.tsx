import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import {
  getPipelineStatus,
  startPipeline,
  stopPipeline,
  restartPipeline,
  getConfig,
  updateConfig,
  Config,
} from '../utils/api';

export function Pipelines() {
  const [status, setStatus] = useState<string>('unknown');
  const [detail, setDetail] = useState<string | undefined>();
  const [config, setConfig] = useState<Config | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      const response = await getPipelineStatus();
      setStatus(response.pipeline.status || 'unknown');
      setDetail(response.pipeline.detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pipeline status');
    }
  };

  const loadConfig = async () => {
    try {
      const data = await getConfig();
      setConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load config');
    }
  };

  useEffect(() => {
    loadStatus();
    loadConfig();
  }, []);

  const updateRetryPolicy = async () => {
    if (!config) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateConfig(config);
      setConfig(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update config');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div class="space-y-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Pipelines</h1>
        <p class="text-gray-600 dark:text-gray-400">Manage pipeline lifecycle and retry policy.</p>
      </div>

      {error && (
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      <Card title="Pipeline Status">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-gray-500 dark:text-gray-400">State</div>
            <div class="text-lg font-semibold text-gray-900 dark:text-gray-100">{status}</div>
            {detail && <div class="text-sm text-gray-500 dark:text-gray-400">{detail}</div>}
          </div>
          <div class="flex gap-2">
            <button
              onClick={async () => {
                await startPipeline();
                loadStatus();
              }}
              class="px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg"
            >
              Start
            </button>
            <button
              onClick={async () => {
                await stopPipeline();
                loadStatus();
              }}
              class="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg"
            >
              Stop
            </button>
            <button
              onClick={async () => {
                await restartPipeline();
                loadStatus();
              }}
              class="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg"
            >
              Restart
            </button>
          </div>
        </div>
      </Card>

      <Card title="Retry / Backoff Settings">
        {config ? (
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="text-sm text-gray-600 dark:text-gray-400">Initial delay (sec)</label>
              <input
                type="number"
                value={config.retry_policy.initial_delay}
                onInput={(e) =>
                  setConfig({
                    ...config,
                    retry_policy: {
                      ...config.retry_policy,
                      initial_delay: Number((e.target as HTMLInputElement).value),
                    },
                  })
                }
                class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
            <div>
              <label class="text-sm text-gray-600 dark:text-gray-400">Max delay (sec)</label>
              <input
                type="number"
                value={config.retry_policy.max_delay}
                onInput={(e) =>
                  setConfig({
                    ...config,
                    retry_policy: {
                      ...config.retry_policy,
                      max_delay: Number((e.target as HTMLInputElement).value),
                    },
                  })
                }
                class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
            <div>
              <label class="text-sm text-gray-600 dark:text-gray-400">Multiplier</label>
              <input
                type="number"
                value={config.retry_policy.multiplier}
                onInput={(e) =>
                  setConfig({
                    ...config,
                    retry_policy: {
                      ...config.retry_policy,
                      multiplier: Number((e.target as HTMLInputElement).value),
                    },
                  })
                }
                class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
            <div>
              <label class="text-sm text-gray-600 dark:text-gray-400">Jitter</label>
              <input
                type="number"
                value={config.retry_policy.jitter}
                onInput={(e) =>
                  setConfig({
                    ...config,
                    retry_policy: {
                      ...config.retry_policy,
                      jitter: Number((e.target as HTMLInputElement).value),
                    },
                  })
                }
                class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
            <div>
              <label class="text-sm text-gray-600 dark:text-gray-400">Max retries</label>
              <input
                type="number"
                value={config.retry_policy.max_retries ?? ''}
                onInput={(e) =>
                  setConfig({
                    ...config,
                    retry_policy: {
                      ...config.retry_policy,
                      max_retries: (e.target as HTMLInputElement).value
                        ? Number((e.target as HTMLInputElement).value)
                        : null,
                    },
                  })
                }
                class="w-full mt-1 px-3 py-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
              />
            </div>
          </div>
        ) : (
          <div class="text-sm text-gray-500 dark:text-gray-400">Loading retry policy...</div>
        )}
        <div class="mt-4">
          <button
            onClick={updateRetryPolicy}
            disabled={saving || !config}
            class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save settings'}
          </button>
        </div>
      </Card>
    </div>
  );
}
