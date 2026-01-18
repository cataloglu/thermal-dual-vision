import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { route } from 'preact-router';
import { Card } from '../components/ui/Card';
import { getCamera, Camera } from '../utils/api';

interface CameraDetailProps {
  id?: string;
}

export function CameraDetail({ id }: CameraDetailProps) {
  const [camera, setCamera] = useState<Camera | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCamera = async () => {
    if (!id) {
      setError('Camera not found');
      setLoading(false);
      return;
    }
    try {
      setError(null);
      const data = await getCamera(id);
      setCamera(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCamera();
  }, [id]);

  if (loading) {
    return (
      <div class="flex items-center justify-center min-h-screen">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p class="text-gray-600 dark:text-gray-400">Loading camera...</p>
        </div>
      </div>
    );
  }

  if (error || !camera) {
    return (
      <div class="p-4">
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 class="text-red-800 dark:text-red-200 font-semibold mb-2">Camera Not Found</h3>
          <p class="text-red-600 dark:text-red-400">{error || 'Missing camera details'}</p>
          <button
            onClick={() => route('/cameras')}
            class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Back to Cameras
          </button>
        </div>
      </div>
    );
  }

  return (
    <div class="space-y-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">{camera.name}</h1>
        <p class="text-gray-600 dark:text-gray-400 capitalize">Type: {camera.type}</p>
      </div>

      <Card title="Status">
        <p class="text-sm text-gray-600 dark:text-gray-400">State: {camera.status}</p>
        {camera.last_error && (
          <p class="text-sm text-red-600 dark:text-red-400 mt-2">Last error: {camera.last_error}</p>
        )}
        {camera.last_frame_ts && (
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Last frame: {new Date(camera.last_frame_ts * 1000).toLocaleString()}
          </p>
        )}
      </Card>

      <Card title="RTSP Settings">
        <div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <div>
            <span class="font-medium text-gray-700 dark:text-gray-300">Color URL:</span>{' '}
            {camera.rtsp_url_color || '—'}
          </div>
          <div>
            <span class="font-medium text-gray-700 dark:text-gray-300">Thermal URL:</span>{' '}
            {camera.rtsp_url_thermal || '—'}
          </div>
          <div>
            <span class="font-medium text-gray-700 dark:text-gray-300">Color Channel:</span>{' '}
            {camera.channel_color ?? '—'}
          </div>
          <div>
            <span class="font-medium text-gray-700 dark:text-gray-300">Thermal Channel:</span>{' '}
            {camera.channel_thermal ?? '—'}
          </div>
        </div>
      </Card>
    </div>
  );
}
