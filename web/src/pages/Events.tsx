import { h } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import { Table, TableColumn } from '../components/ui/Table';
import { Card } from '../components/ui/Card';
import {
  getScreenshots,
  getScreenshotClipUrl,
  getScreenshotCollageUrl,
  Screenshot
} from '../utils/api';

/**
 * Events page - Motion detection event history and detail view.
 *
 * Displays all motion detection events in a sortable table format,
 * plus a detail panel with collage, AI analysis, and MP4 clip.
 *
 * Fetches data from:
 * - /api/screenshots - List of detection events
 * - /api/screenshots/<id>/collage - 5-frame collage
 * - /api/screenshots/<id>/clip.mp4 - MP4 clip
 *
 * Features:
 * - Comprehensive event history table with 6 columns:
 *   * Timestamp (relative and absolute)
 *   * Status (Motion/Possible with color indicators)
 *   * Description (with detected objects)
 *   * Confidence score (with progress bar)
 *   * Threat level (color-coded: high/medium/low)
 *   * Screenshot links (to Gallery page)
 * - Auto-refresh every 30 seconds for real-time updates
 * - Loading state with animated spinner
 * - Error state with retry functionality
 * - Empty state message when no events
 * - Responsive design with table overflow handling
 * - Dark mode support throughout
 * - Striped and hoverable table rows
 * - Uses centralized API utilities for type-safe requests
 *
 * Integration:
 * - Uses getEvents() utility from api.ts (consistent with Dashboard pattern)
 * - Imports DetectionEvent interface from api.ts (single source of truth)
 * - Links to Gallery page via screenshot view links
 * - Follows established patterns from subtasks 14-12 and 14-14
 */

export function Events() {
  const [events, setEvents] = useState<Screenshot[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedEvent, setSelectedEvent] = useState<Screenshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEvents();
    // Refresh data every 30 seconds
    const interval = setInterval(fetchEvents, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchEvents = async () => {
    try {
      setError(null);

      // Use API utility function (consistent with Dashboard pattern)
      const data = await getScreenshots();
      setEvents(data.screenshots || []);
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

  const formatRelativeTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
  };

  const filteredEvents = events.filter((event) => {
    if (filterStatus === 'all') {
      return true;
    }
    const isReal = event.analysis?.gercek_hareket === true;
    return filterStatus === 'real' ? isReal : !isReal;
  });

  const columns: TableColumn<Screenshot>[] = [
    {
      key: 'timestamp',
      label: 'Time',
      width: 'w-48',
      render: (event) => (
        <div>
          <div class="font-medium text-gray-900 dark:text-gray-100">
            {formatRelativeTime(event.timestamp)}
          </div>
          <div class="text-xs text-gray-500 dark:text-gray-400">
            {formatTimestamp(event.timestamp)}
          </div>
        </div>
      )
    },
    {
      key: 'status',
      label: 'Status',
      width: 'w-32',
      render: (event) => (
        <span class={`inline-flex items-center gap-2 text-sm ${
          event.analysis?.gercek_hareket ? 'text-green-600 dark:text-green-400' : 'text-yellow-600 dark:text-yellow-400'
        }`}>
          <span class={`w-2 h-2 rounded-full ${
            event.analysis?.gercek_hareket ? 'bg-green-500' : 'bg-yellow-500'
          }`}></span>
          {event.analysis?.gercek_hareket ? 'Real' : 'Possible'}
        </span>
      )
    },
    {
      key: 'threat',
      label: 'Threat',
      width: 'w-32',
      render: (event) => (
        <span class="text-sm text-gray-600 dark:text-gray-400 capitalize">
          {event.analysis?.tehdit_seviyesi || 'unknown'}
        </span>
      )
    },
    {
      key: 'summary',
      label: 'Summary',
      render: (event) => (
        <span class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
          {event.analysis?.degisiklik_aciklamasi || 'No analysis summary'}
        </span>
      )
    }
  ];

  if (loading) {
    return (
      <div class="flex items-center justify-center min-h-screen">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p class="text-gray-600 dark:text-gray-400">Loading events...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div class="p-4">
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 class="text-red-800 dark:text-red-200 font-semibold mb-2">Error Loading Events</h3>
          <p class="text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={fetchEvents}
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
          Events
        </h1>
        <p class="text-gray-600 dark:text-gray-400">
          Motion detection event history ({events.length} total)
        </p>
      </div>

      {/* Filters */}
      <Card>
        <div class="flex flex-col md:flex-row gap-3">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus((e.target as HTMLSelectElement).value)}
            class="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
          >
            <option value="all">All statuses</option>
            <option value="real">Real motion</option>
            <option value="possible">Possible motion</option>
          </select>
        </div>
      </Card>

      {/* Events Table */}
      <Card>
        <Table
          columns={columns}
          data={filteredEvents}
          loading={loading}
          emptyMessage="No events recorded yet"
          striped
          hover
          onRowClick={(event) => setSelectedEvent(event)}
        />
      </Card>

      {/* Event Detail */}
      {selectedEvent && (
        <Card title="Event Detail">
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="space-y-4">
              <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Collage
                </h3>
                <img
                  src={getScreenshotCollageUrl(selectedEvent.id)}
                  alt="Event collage"
                  class="w-full rounded-lg border border-gray-200 dark:border-gray-700"
                />
              </div>
              <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  MP4 Clip
                </h3>
                <video
                  src={getScreenshotClipUrl(selectedEvent.id)}
                  controls
                  class="w-full rounded-lg border border-gray-200 dark:border-gray-700"
                />
                <a
                  href={getScreenshotClipUrl(selectedEvent.id)}
                  download
                  class="inline-flex mt-2 text-sm text-primary-600 dark:text-primary-400 hover:underline"
                >
                  Download MP4
                </a>
              </div>
            </div>
            <div class="space-y-4">
              <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  AI Summary
                </h3>
                <p class="text-sm text-gray-600 dark:text-gray-400">
                  {selectedEvent.analysis?.detayli_analiz || 'No AI analysis available.'}
                </p>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600 dark:text-gray-400">
                <div>
                  <span class="font-medium text-gray-900 dark:text-gray-100">Threat:</span>{' '}
                  {selectedEvent.analysis?.tehdit_seviyesi || 'unknown'}
                </div>
                <div>
                  <span class="font-medium text-gray-900 dark:text-gray-100">Confidence:</span>{' '}
                  {selectedEvent.analysis?.guven_skoru !== undefined
                    ? `${Math.round(selectedEvent.analysis.guven_skoru * 100)}%`
                    : 'n/a'}
                </div>
                <div>
                  <span class="font-medium text-gray-900 dark:text-gray-100">Objects:</span>{' '}
                  {selectedEvent.analysis?.tespit_edilen_nesneler?.join(', ') || 'n/a'}
                </div>
                <div>
                  <span class="font-medium text-gray-900 dark:text-gray-100">Detected:</span>{' '}
                  {selectedEvent.analysis?.gercek_hareket ? 'Real motion' : 'Possible motion'}
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
