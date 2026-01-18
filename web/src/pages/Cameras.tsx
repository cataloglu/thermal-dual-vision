import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import { Camera, getCameras } from '../utils/api';

export function Cameras() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setError(null);
        const data = await getCameras();
        setCameras(data.cameras || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load cameras');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div class="space-y-4">
      <div>
        <h1 class="text-lg font-semibold text-gray-200">Cameras</h1>
        <p class="text-sm text-muted">Status and configuration access.</p>
      </div>

      {error && (
        <Card>
          <p class="text-sm text-[#EF4444]">{error}</p>
        </Card>
      )}

      {loading && (
        <Card>
          <p class="text-sm text-muted">Loading cameras...</p>
        </Card>
      )}

      <Card title="Camera list" actions={
        <a class="text-xs text-[#38BDF8]" href="/settings">
          Open configuration
        </a>
      }>
        {cameras.length === 0 ? (
          <p class="text-sm text-muted">No cameras configured.</p>
        ) : (
          <div class="grid gap-3 md:grid-cols-2">
            {cameras.map((camera) => (
              <div key={camera.id} class="border border-[#1F2937] rounded p-3 bg-[#111827]">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-sm font-semibold text-gray-200">{camera.name}</p>
                    <p class="text-xs text-muted uppercase">{camera.type}</p>
                  </div>
                  <span class={`chip ${camera.status === 'connected' ? 'chip-ok' : camera.status === 'retrying' ? 'chip-warn' : 'chip-danger'}`}>
                    {camera.status}
                  </span>
                </div>
                <div class="mt-3 text-xs text-muted">
                  Last frame: {camera.last_frame_ts ? new Date(camera.last_frame_ts * 1000).toLocaleString() : 'unknown'}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
