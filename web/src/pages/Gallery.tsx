import { h } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import { Card } from '../components/ui/Card';
import { getScreenshots, Screenshot, ScreenshotsResponse } from '../utils/api';

/**
 * Gallery page - Grid view of saved motion detection screenshots.
 *
 * Displays a responsive grid of screenshot thumbnails from detection events.
 * Each screenshot shows the peak moment of the detection, with timestamp
 * and detection status overlay.
 *
 * Features:
 * - Responsive grid layout (1-4 columns based on screen size)
 * - Click to view full-size image in modal
 * - Navigate between before/early/peak/late/after images in modal
 * - Loading and error states with retry
 * - Real-time detection status indicators
 * - Auto-refresh capability
 * - Dark mode support
 *
 * Fetches data from:
 * - /api/screenshots - List of all screenshot sets
 * - /api/screenshots/<id>/<type> - Individual images
 */

type ImageType = 'before' | 'early' | 'peak' | 'late' | 'after';

export function Gallery() {
  const [screenshots, setScreenshots] = useState<Screenshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<ImageType>('peak');

  useEffect(() => {
    fetchScreenshots();
  }, []);

  const fetchScreenshots = async () => {
    try {
      setError(null);
      setLoading(true);

      // Fetch screenshots using API utility
      const data = await getScreenshots();
      setScreenshots(data.screenshots || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const openModal = (id: string) => {
    setSelectedId(id);
    setSelectedType('peak');
  };

  const closeModal = () => {
    setSelectedId(null);
  };

  const getImageUrl = (id: string, type: ImageType): string => {
    return `/api/screenshots/${id}/${type}`;
  };

  const selectedScreenshot = screenshots.find(s => s.id === selectedId);

  if (loading) {
    return (
      <div class="flex items-center justify-center min-h-screen">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p class="text-gray-600 dark:text-gray-400">Loading gallery...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div class="p-4">
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 class="text-red-800 dark:text-red-200 font-semibold mb-2">Error Loading Gallery</h3>
          <p class="text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={fetchScreenshots}
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
      {/* Page Header */}
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Gallery
        </h1>
        <p class="text-gray-600 dark:text-gray-400">
          Browse motion detection screenshots ({screenshots.length} total)
        </p>
      </div>

      {/* Screenshot Grid */}
      {screenshots.length === 0 ? (
        <Card>
          <div class="text-center py-12 text-gray-500 dark:text-gray-400">
            <svg
              class="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <p class="text-lg font-medium mb-2">No Screenshots Yet</p>
            <p class="text-sm">Screenshots will appear here when motion is detected</p>
          </div>
        </Card>
      ) : (
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {screenshots.map((screenshot) => (
            <div
              key={screenshot.id}
              class="group relative bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 overflow-hidden cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => openModal(screenshot.id)}
            >
              {/* Screenshot Image */}
              <div class="aspect-video bg-gray-900 relative overflow-hidden">
                <img
                  src={getImageUrl(screenshot.id, 'peak')}
                  alt={`Screenshot from ${formatTimestamp(screenshot.timestamp)}`}
                  class="w-full h-full object-cover"
                  loading="lazy"
                />

                {/* Overlay with detection status */}
                <div class="absolute top-2 right-2">
                  {screenshot.analysis?.gercek_hareket ? (
                    <span class="px-2 py-1 bg-green-600 text-white text-xs font-semibold rounded">
                      Motion
                    </span>
                  ) : (
                    <span class="px-2 py-1 bg-yellow-600 text-white text-xs font-semibold rounded">
                      Possible
                    </span>
                  )}
                </div>

                {/* Hover overlay */}
                <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-opacity flex items-center justify-center">
                  <svg
                    class="w-12 h-12 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"
                    />
                  </svg>
                </div>
              </div>

              {/* Screenshot Info */}
              <div class="p-3">
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                  {formatTimestamp(screenshot.timestamp)}
                </p>
                {screenshot.analysis?.degisiklik_aciklamasi && (
                  <p class="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                    {screenshot.analysis.degisiklik_aciklamasi}
                  </p>
                )}
                {screenshot.analysis?.guven_skoru !== undefined && (
                  <div class="mt-2 text-xs text-gray-500 dark:text-gray-500">
                    Confidence: {Math.round(screenshot.analysis.guven_skoru * 100)}%
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for full-size view */}
      {selectedId && selectedScreenshot && (
        <div
          class="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
          onClick={closeModal}
        >
          <div
            class="relative bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Screenshot Details
                </h3>
                <p class="text-sm text-gray-600 dark:text-gray-400">
                  {formatTimestamp(selectedScreenshot.timestamp)}
                </p>
              </div>
              <button
                onClick={closeModal}
                class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <svg
                  class="w-6 h-6 text-gray-600 dark:text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Modal Body */}
            <div class="p-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 140px)' }}>
              {/* Image Type Selector */}
              <div class="flex gap-2 mb-4">
                {selectedScreenshot.has_before && (
                  <button
                    onClick={() => setSelectedType('before')}
                    class={`px-4 py-2 rounded-lg font-medium transition-colors ${
                      selectedType === 'before'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    Before
                  </button>
                )}
                {selectedScreenshot.has_early && (
                  <button
                    onClick={() => setSelectedType('early')}
                    class={`px-4 py-2 rounded-lg font-medium transition-colors ${
                      selectedType === 'early'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    Early
                  </button>
                )}
                {selectedScreenshot.has_peak && (
                  <button
                    onClick={() => setSelectedType('peak')}
                    class={`px-4 py-2 rounded-lg font-medium transition-colors ${
                      selectedType === 'peak'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    Peak
                  </button>
                )}
                {selectedScreenshot.has_late && (
                  <button
                    onClick={() => setSelectedType('late')}
                    class={`px-4 py-2 rounded-lg font-medium transition-colors ${
                      selectedType === 'late'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    Late
                  </button>
                )}
                {selectedScreenshot.has_after && (
                  <button
                    onClick={() => setSelectedType('after')}
                    class={`px-4 py-2 rounded-lg font-medium transition-colors ${
                      selectedType === 'after'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    After
                  </button>
                )}
              </div>

              {/* Full-size Image */}
              <div class="bg-gray-900 rounded-lg overflow-hidden mb-4">
                <img
                  src={getImageUrl(selectedId, selectedType)}
                  alt={`${selectedType} screenshot`}
                  class="w-full h-auto"
                />
              </div>

              {/* Analysis Details */}
              {selectedScreenshot.analysis && (
                <div class="space-y-3">
                  <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span class="text-gray-600 dark:text-gray-400">Status:</span>
                      <span class={`ml-2 font-medium ${
                        selectedScreenshot.analysis.gercek_hareket
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-yellow-600 dark:text-yellow-400'
                      }`}>
                        {selectedScreenshot.analysis.gercek_hareket ? 'Real Motion' : 'Possible Motion'}
                      </span>
                    </div>
                    {selectedScreenshot.analysis.guven_skoru !== undefined && (
                      <div>
                        <span class="text-gray-600 dark:text-gray-400">Confidence:</span>
                        <span class="ml-2 font-medium text-gray-900 dark:text-gray-100">
                          {Math.round(selectedScreenshot.analysis.guven_skoru * 100)}%
                        </span>
                      </div>
                    )}
                    {selectedScreenshot.analysis.tehdit_seviyesi && (
                      <div>
                        <span class="text-gray-600 dark:text-gray-400">Threat Level:</span>
                        <span class="ml-2 font-medium text-gray-900 dark:text-gray-100 capitalize">
                          {selectedScreenshot.analysis.tehdit_seviyesi}
                        </span>
                      </div>
                    )}
                    {selectedScreenshot.analysis.tespit_edilen_nesneler && selectedScreenshot.analysis.tespit_edilen_nesneler.length > 0 && (
                      <div>
                        <span class="text-gray-600 dark:text-gray-400">Objects:</span>
                        <span class="ml-2 font-medium text-gray-900 dark:text-gray-100">
                          {selectedScreenshot.analysis.tespit_edilen_nesneler.join(', ')}
                        </span>
                      </div>
                    )}
                  </div>

                  {selectedScreenshot.analysis.degisiklik_aciklamasi && (
                    <div>
                      <p class="text-sm text-gray-600 dark:text-gray-400 mb-1">Description:</p>
                      <p class="text-sm text-gray-900 dark:text-gray-100">
                        {selectedScreenshot.analysis.degisiklik_aciklamasi}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
