import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { CameraWizard } from '../components/cameras/CameraWizard';
import { Card } from '../components/ui/Card';
import { getCameras, Camera } from '../utils/api';

export function Cameras() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);

  const fetchCameras = async () => {
    try {
      setError(null);
      const response = await getCameras();
      setCameras(response.cameras || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const statusClass = (status: string) => {
    switch (status) {
      case 'connected':
        return 'text-green-600 dark:text-green-400';
      case 'retrying':
        return 'text-yellow-600 dark:text-yellow-400';
      default:
        return 'text-red-600 dark:text-red-400';
    }
  };

  if (loading) {
    return (
      <div class="flex items-center justify-center min-h-screen">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p class="text-gray-600 dark:text-gray-400">Loading cameras...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div class="p-4">
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 class="text-red-800 dark:text-red-200 font-semibold mb-2">Error Loading Cameras</h3>
          <p class="text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={fetchCameras}
            class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div class="space-y-6">
      <div class="flex items-start justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Cameras</h1>
          <p class="text-gray-600 dark:text-gray-400">Registered cameras and connection status</p>
        </div>
        <button
          onClick={() => setWizardOpen(true)}
          class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
        >
          Add camera
        </button>
      </div>

      {wizardOpen && (
        <CameraWizard
          onClose={() => setWizardOpen(false)}
          onSaved={() => {
            fetchCameras();
          }}
        />
      )}

      {cameras.length === 0 ? (
        <Card>
          <div class="text-center py-8 text-gray-500 dark:text-gray-400">No cameras configured.</div>
        </Card>
      ) : (
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {cameras.map((camera) => (
            <Card key={camera.id}>
              <div class="flex items-start justify-between">
                <div>
                  <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{camera.name}</h3>
                  <p class="text-sm text-gray-500 dark:text-gray-400 capitalize">{camera.type}</p>
                </div>
                <span class={`text-sm font-medium ${statusClass(camera.status)}`}>
                  {camera.status}
                </span>
              </div>
              {camera.last_error && (
                <p class="mt-2 text-sm text-red-600 dark:text-red-400">Last error: {camera.last_error}</p>
              )}
              <div class="mt-4">
                <a
                  href={`/cameras/${camera.id}`}
                  class="text-sm text-primary-600 dark:text-primary-400 hover:underline"
                >
                  View details
                </a>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
