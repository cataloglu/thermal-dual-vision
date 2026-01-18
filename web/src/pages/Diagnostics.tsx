import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import { getHealth, getLogsTail, getMetrics, HealthResponse, LogsTailResponse, MetricsResponse } from '../utils/api';

export function Diagnostics() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [logs, setLogs] = useState<LogsTailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDiagnostics = async () => {
    try {
      setError(null);
      const [healthData, metricsData, logsData] = await Promise.all([
        getHealth(),
        getMetrics(),
        getLogsTail(200),
      ]);
      setHealth(healthData);
      setMetrics(metricsData);
      setLogs(logsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load diagnostics');
    }
  };

  useEffect(() => {
    loadDiagnostics();
  }, []);

  return (
    <div class="space-y-6">
      <div class="flex items-start justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Diagnostics</h1>
          <p class="text-gray-600 dark:text-gray-400">Logs, health, and system info.</p>
        </div>
        <button
          onClick={loadDiagnostics}
          class="px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      <Card title="Health / Ready">
        {health ? (
          <div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <div>Status: {health.status}</div>
            <div>AI Enabled: {health.ai_enabled ? 'true' : 'false'}</div>
            <div>Pipeline: {health.pipeline?.status}</div>
          </div>
        ) : (
          <div class="text-sm text-gray-500 dark:text-gray-400">Loading health...</div>
        )}
      </Card>

      <Card title="System Metrics">
        {metrics ? (
          <div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <div>Uptime: {Math.round(metrics.uptime_seconds)}s</div>
            <div>Events count: {metrics.events_count}</div>
            <div>Pipeline: {metrics.pipeline?.status}</div>
          </div>
        ) : (
          <div class="text-sm text-gray-500 dark:text-gray-400">Loading metrics...</div>
        )}
      </Card>

      <Card title="Logs (tail)">
        {logs ? (
          <pre class="text-xs whitespace-pre-wrap text-gray-700 dark:text-gray-300">
            {logs.lines.join('\n')}
          </pre>
        ) : (
          <div class="text-sm text-gray-500 dark:text-gray-400">Loading logs...</div>
        )}
      </Card>
    </div>
  );
}
