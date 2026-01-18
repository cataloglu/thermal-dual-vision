import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import { Table, TableColumn } from '../components/ui/Table';
import {
  Screenshot,
  getCameras,
  getScreenshotClipUrl,
  getScreenshotCollageUrl,
  getScreenshots,
} from '../utils/api';

const formatTime = (value?: string) => {
  if (!value) return 'Unknown';
  const date = new Date(value);
  return date.toLocaleString();
};

const threatClass = (value?: string) => {
  if (value === 'yuksek') return 'chip-danger';
  if (value === 'orta') return 'chip-warn';
  return 'chip-ok';
};

const hasHuman = (objects?: string[]) => {
  if (!objects || objects.length === 0) return null;
  return objects.some((obj) => {
    const lowered = obj.toLowerCase();
    return lowered.includes('person') || lowered.includes('insan');
  });
};

export function Events() {
  const [events, setEvents] = useState<Screenshot[]>([]);
  const [selected, setSelected] = useState<Screenshot | null>(null);
  const [cameraLabel, setCameraLabel] = useState<string>('Unknown');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const results = await Promise.allSettled([
        getScreenshots(),
        getCameras(),
      ]);

      const [screenshotsResult, camerasResult] = results;
      if (screenshotsResult.status === 'fulfilled') {
        const list = screenshotsResult.value.screenshots || [];
        setEvents(list);
        setSelected(list[0] ?? null);
      }
      if (camerasResult.status === 'fulfilled') {
        const cams = camerasResult.value.cameras || [];
        const label = cams.length === 1 ? cams[0].name : cams.length > 1 ? 'Multiple' : 'Unknown';
        setCameraLabel(label);
      }

      if (results.some((result) => result.status === 'rejected')) {
        setError('Failed to load some event feeds.');
      } else {
        setError(null);
      }
      setLoading(false);
    };

    load();
  }, []);

  const columns: TableColumn<Screenshot>[] = [
    {
      key: 'timestamp',
      label: 'Time',
      width: 'w-48',
      render: (event) => (
        <span class="text-sm text-gray-200">{formatTime(event.timestamp)}</span>
      )
    },
    {
      key: 'camera',
      label: 'Camera',
      width: 'w-36',
      render: () => (
        <span class="text-sm text-gray-300">{cameraLabel}</span>
      )
    },
    {
      key: 'type',
      label: 'Event type',
      width: 'w-32',
      render: () => (
        <span class="text-sm text-gray-300">motion</span>
      )
    },
    {
      key: 'ai',
      label: 'Human',
      width: 'w-28',
      render: (event) => {
        const human = hasHuman(event.analysis?.tespit_edilen_nesneler);
        const label = human === null ? 'Unknown' : human ? 'Yes' : 'No';
        const chip = human === null ? 'chip-muted' : human ? 'chip-ok' : 'chip-warn';
        return <span class={`chip ${chip}`}>{label}</span>;
      }
    },
    {
      key: 'threat',
      label: 'Threat',
      width: 'w-32',
      render: (event) => (
        <span class={`chip ${threatClass(event.analysis?.tehdit_seviyesi)}`}>
          {event.analysis?.tehdit_seviyesi || 'unknown'}
        </span>
      )
    }
  ];

  return (
    <div class="space-y-4">
      <div>
        <h1 class="text-lg font-semibold text-gray-200">Events</h1>
        <p class="text-sm text-muted">Primary event timeline.</p>
      </div>

      {error && (
        <Card>
          <p class="text-sm text-[#EF4444]">{error}</p>
        </Card>
      )}

      {loading && (
        <Card>
          <p class="text-sm text-muted">Loading events...</p>
        </Card>
      )}

      <Card title="Event list">
        <Table
          columns={columns}
          data={events}
          emptyMessage="No events recorded."
          onRowClick={setSelected}
        />
      </Card>

      {selected && (
        <Card title="Event detail">
          <div class="grid gap-4 lg:grid-cols-2">
            <div class="space-y-3">
              <div>
                <p class="text-xs uppercase text-muted mb-2">Collage</p>
                <img
                  src={getScreenshotCollageUrl(selected.id)}
                  alt="Event collage"
                  class="w-full rounded border border-[#1F2937]"
                />
              </div>
              <div>
                <p class="text-xs uppercase text-muted mb-2">MP4</p>
                <video
                  src={getScreenshotClipUrl(selected.id)}
                  controls
                  class="w-full rounded border border-[#1F2937]"
                />
                <a
                  class="text-xs text-[#38BDF8] mt-2 inline-block"
                  href={getScreenshotClipUrl(selected.id)}
                  download
                >
                  Download MP4
                </a>
              </div>
            </div>
            <div class="space-y-3">
              <div>
                <p class="text-xs uppercase text-muted mb-2">AI summary</p>
                <p class="text-sm text-gray-300">
                  {selected.analysis?.detayli_analiz
                    || selected.analysis?.degisiklik_aciklamasi
                    || 'No AI analysis.'}
                </p>
              </div>
              <div class="grid gap-2 text-sm text-gray-300">
                <div class="flex items-center justify-between">
                  <span class="text-muted">Timestamp</span>
                  <span>{formatTime(selected.timestamp)}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-muted">Pipeline latency</span>
                  <span>
                    {selected.analysis?.processing_time !== undefined
                      ? `${selected.analysis.processing_time}s`
                      : 'Unknown'}
                  </span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-muted">Retry count</span>
                  <span>Unknown</span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
