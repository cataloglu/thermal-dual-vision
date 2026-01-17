import { h } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import { Card } from '../components/ui/Card';

/**
 * LiveView page - Display live MJPEG camera stream.
 *
 * Shows real-time video feed from the motion detector camera.
 * The MJPEG stream is served from the /api/stream endpoint.
 *
 * Features:
 * - Automatic stream loading
 * - Error handling with retry mechanism
 * - Loading state indicator
 * - Responsive container that maintains aspect ratio
 *
 * The stream reconnects automatically on error with exponential backoff.
 */

export function LiveView() {
  const [streamUrl, setStreamUrl] = useState<string>('/api/stream');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState<number>(0);

  /**
   * Handle stream load success.
   * Called when the stream image starts loading successfully.
   */
  const handleStreamLoad = () => {
    setLoading(false);
    setError(null);
    setRetryCount(0);
  };

  /**
   * Handle stream error.
   * Implements exponential backoff for reconnection attempts.
   */
  const handleStreamError = () => {
    setLoading(false);
    setError('Failed to load camera stream');

    // Exponential backoff: 2s, 4s, 8s, 16s, max 30s
    const delay = Math.min(2000 * Math.pow(2, retryCount), 30000);

    setTimeout(() => {
      setRetryCount(prev => prev + 1);
      setLoading(true);
      setError(null);
      // Force reload by adding timestamp to URL
      setStreamUrl(`/api/stream?t=${Date.now()}`);
    }, delay);
  };

  /**
   * Manual retry function for user-triggered reconnection.
   */
  const handleRetry = () => {
    setRetryCount(0);
    setLoading(true);
    setError(null);
    setStreamUrl(`/api/stream?t=${Date.now()}`);
  };

  return (
    <div class="space-y-6">
      {/* Page Header */}
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Live View
        </h1>
        <p class="text-gray-600 dark:text-gray-400">
          Real-time camera stream from motion detector
        </p>
      </div>

      {/* Stream Container */}
      <Card>
        <div class="relative bg-gray-900 rounded-lg overflow-hidden">
          {/* Loading Indicator */}
          {loading && (
            <div class="absolute inset-0 flex items-center justify-center bg-gray-900 z-10">
              <div class="text-center">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
                <p class="text-gray-400">Connecting to camera...</p>
                {retryCount > 0 && (
                  <p class="text-sm text-gray-500 mt-2">
                    Retry attempt {retryCount}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div class="absolute inset-0 flex items-center justify-center bg-gray-900 z-10">
              <div class="text-center p-6">
                <div class="text-red-500 mb-4">
                  <svg
                    class="w-16 h-16 mx-auto"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <h3 class="text-white font-semibold mb-2">Stream Unavailable</h3>
                <p class="text-gray-400 mb-4">{error}</p>
                <button
                  onClick={handleRetry}
                  class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
                >
                  Retry Connection
                </button>
              </div>
            </div>
          )}

          {/* MJPEG Stream */}
          <img
            src={streamUrl}
            alt="Live camera stream"
            class="w-full h-auto"
            onLoad={handleStreamLoad}
            onError={handleStreamError}
            style={{ minHeight: '400px' }}
          />
        </div>

        {/* Stream Info */}
        <div class="mt-4 flex items-center justify-between text-sm">
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span class="text-gray-600 dark:text-gray-400">
              {loading ? 'Connecting...' : error ? 'Disconnected' : 'Live'}
            </span>
          </div>
          <div class="text-gray-500 dark:text-gray-400">
            MJPEG Stream
          </div>
        </div>
      </Card>

      {/* Info Card */}
      <Card title="Stream Information">
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-600 dark:text-gray-400">Source:</span>
            <span class="text-gray-900 dark:text-gray-100 font-medium">/api/stream</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600 dark:text-gray-400">Format:</span>
            <span class="text-gray-900 dark:text-gray-100 font-medium">MJPEG</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-600 dark:text-gray-400">Status:</span>
            <span class={`font-medium ${
              loading
                ? 'text-yellow-600 dark:text-yellow-400'
                : error
                ? 'text-red-600 dark:text-red-400'
                : 'text-green-600 dark:text-green-400'
            }`}>
              {loading ? 'Connecting' : error ? 'Error' : 'Connected'}
            </span>
          </div>
        </div>
      </Card>
    </div>
  );
}
