import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import {
  Camera,
  HealthResponse,
  PipelineState,
  Screenshot,
  getCameras,
  getHealth,
  getPipelineStatus,
  getScreenshots,
} from '../utils/api';

const formatTime = (value?: string) => {
  if (!value) return 'Unknown';
  const date = new Date(value);
  return date.toLocaleString();
};

const normalizePipeline = (status?: string) => {
  if (!status) return { label: 'Unknown', chip: 'chip-muted' };
  const normalized = status.toLowerCase();
  if (normalized.includes('retry')) return { label: 'Retry', chip: 'chip-warn' };
  if (normalized === 'running') return { label: 'Running', chip: 'chip-ok' };
  if (normalized === 'idle' || normalized === 'stopped') return { label: 'Stopped', chip: 'chip-danger' };
  return { label: status, chip: 'chip-muted' };
};

const hasHuman = (objects?: string[]) => {
  if (!objects || objects.length === 0) return false;
  return objects.some((obj) => {
    const lowered = obj.toLowerCase();
    return lowered.includes('person') || lowered.includes('insan');
  });
};

export function Dashboard() {
  const [pipeline, setPipeline] = useState<PipelineState | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [latestEvent, setLatestEvent] = useState<Screenshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const results = await Promise.allSettled([
        getPipelineStatus(),
        getCameras(),
        getHealth(),
        getScreenshots(1),
      ]);

      const [pipelineResult, camerasResult, healthResult, screenshotsResult] = results;
      if (pipelineResult.status === 'fulfilled') {
        setPipeline(pipelineResult.value.pipeline);
      }
      if (camerasResult.status === 'fulfilled') {
        setCameras(camerasResult.value.cameras || []);
      }
      if (healthResult.status === 'fulfilled') {
        setHealth(healthResult.value);
      }
      if (screenshotsResult.status === 'fulfilled') {
        setLatestEvent((screenshotsResult.value.screenshots || [])[0] ?? null);
      }

      if (results.some((result) => result.status === 'rejected')) {
        setError('Some status feeds failed to load.');
      } else {
        setError(null);
      }
      setLoading(false);
    };

    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const { label: pipelineLabel, chip: pipelineChip } = normalizePipeline(pipeline?.status);
  const connectedCount = cameras.filter((camera) => camera.status === 'connected').length;
  const disconnectedCount = cameras.length - connectedCount;
  const aiEnabled = Boolean(health?.ai_enabled);

  const lastObjects = latestEvent?.analysis?.tespit_edilen_nesneler;
  const lastThreat = latestEvent?.analysis?.tehdit_seviyesi || 'unknown';
  const lastHuman = hasHuman(lastObjects) ? 'Yes' : 'No';
  const lastAiResult = latestEvent?.analysis?.gercek_hareket === undefined
    ? 'No data'
    : latestEvent.analysis.gercek_hareket
      ? 'Verified'
      : 'Not verified';
  const cameraLabel = cameras.length === 1 ? cameras[0].name : cameras.length > 1 ? 'Multiple' : 'Unknown';

  return (
    <div class="space-y-4">
      <div>
        <h1 class="text-lg font-semibold text-gray-200">Status</h1>
        <p class="text-sm text-muted">Operational snapshot.</p>
      </div>

      {error && (
        <Card>
          <p class="text-sm text-[#EF4444]">{error}</p>
        </Card>
      )}

      {loading && (
        <Card>
          <p class="text-sm text-muted">Loading status...</p>
        </Card>
      )}

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Pipeline">
          <div class="flex items-center justify-between">
            <span class="text-sm text-muted">State</span>
            <span class={`chip ${pipelineChip}`}>{pipelineLabel}</span>
          </div>
        </Card>

        <Card title="Cameras">
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted">Connected</span>
            <span class="text-gray-200">{connectedCount}</span>
          </div>
          <div class="flex items-center justify-between text-sm mt-2">
            <span class="text-muted">Disconnected</span>
            <span class="text-gray-200">{Math.max(disconnectedCount, 0)}</span>
          </div>
        </Card>

        <Card title="AI Status">
          <div class="flex items-center justify-between text-sm">
            <span class="text-muted">Enabled</span>
            <span class={`chip ${aiEnabled ? 'chip-info' : 'chip-muted'}`}>
              {aiEnabled ? 'Yes' : 'No'}
            </span>
          </div>
          <div class="flex items-center justify-between text-sm mt-2">
            <span class="text-muted">Last AI result</span>
            <span class={`chip ${lastAiResult === 'Verified' ? 'chip-ok' : lastAiResult === 'Not verified' ? 'chip-warn' : 'chip-muted'}`}>
              {lastAiResult}
            </span>
          </div>
        </Card>

        <Card title="Last Event">
          {latestEvent ? (
            <div class="space-y-2 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted">Camera</span>
                <span class="text-gray-200">{cameraLabel}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">Time</span>
                <span class="text-gray-200">{formatTime(latestEvent.timestamp)}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">Human</span>
                <span class="text-gray-200">{lastHuman}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted">Threat</span>
                <span class={`chip ${lastThreat === 'yuksek' ? 'chip-danger' : lastThreat === 'orta' ? 'chip-warn' : 'chip-ok'}`}>
                  {lastThreat}
                </span>
              </div>
            </div>
          ) : (
            <p class="text-sm text-muted">No events yet.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
