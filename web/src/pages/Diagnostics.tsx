import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import api, { HealthResponse, LogsTailResponse, MetricsResponse } from '../utils/api';

export function Diagnostics() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [logs, setLogs] = useState<LogsTailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDiagnostics = async () => {
    try {
      setError(null);
      const [healthData, metricsData, logsData] = await Promise.all([
        api.getHealth(),
        api.getMetrics(),
        api.getLogsTail(200),
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
    const interval = setInterval(loadDiagnostics, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div class="space-y-4">
      <div>
        <h1 class="text-lg font-semibold text-gray-200 mb-1">Diagnostics</h1>
        <p class="text-sm text-muted">Read-only health, metrics, and logs.</p>
      </div>

      {error && (
        <Card>
          <p class="text-sm text-[#EF4444]">{error}</p>
        </Card>
      )}

      <Card title="Health / Ready">
        {health ? (
          <div class="space-y-2 text-sm text-gray-300">
            <div>Status: {health.status}</div>
            <div>AI Enabled: {health.ai_enabled ? 'true' : 'false'}</div>
            <div>Pipeline: {health.pipeline?.status}</div>
          </div>
        ) : (
          <div class="text-sm text-muted">Loading health...</div>
        )}
      </Card>

      <Card title="System Metrics">
        {metrics ? (
          <div class="space-y-2 text-sm text-gray-300">
            <div>Uptime: {Math.round(metrics.uptime_seconds)}s</div>
            <div>Events count: {metrics.events_count}</div>
            <div>Pipeline: {metrics.pipeline?.status}</div>
          </div>
        ) : (
          <div class="text-sm text-muted">Loading metrics...</div>
        )}
      </Card>

      <Card title="Logs (tail)">
        {logs ? (
          <pre class="text-xs whitespace-pre-wrap text-gray-300">
            {logs.lines.join('\n')}
          </pre>
        ) : (
          <div class="text-sm text-muted">Loading logs...</div>
        )}
      </Card>
    </div>
  );
}
