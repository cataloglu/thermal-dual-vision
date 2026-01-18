import { h } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import { Table, TableColumn } from '../components/ui/Table';
import { Card } from '../components/ui/Card';
import { getEvents, SystemEvent } from '../utils/api';

/**
 * Events page - Complete list of motion detection events.
 *
 * Displays all motion detection events in a sortable table format,
 * showing timestamp, detection status, confidence, and analysis details.
 *
 * Fetches data from:
 * - /api/events - List of all detection events
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
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterSource, setFilterSource] = useState<string>('all');
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
      const data = await getEvents();
      setEvents(data.events || []);
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

  const columns: TableColumn<SystemEvent>[] = [
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
      key: 'event_type',
      label: 'Type',
      width: 'w-40',
      render: (event) => (
        <span class="font-medium text-gray-900 dark:text-gray-100">
          {event.event_type}
        </span>
      )
    },
    {
      key: 'source',
      label: 'Source',
      width: 'w-32',
      render: (event) => (
        <span class="text-sm text-gray-600 dark:text-gray-400">{event.source}</span>
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
            value={filterType}
            onChange={(e) => setFilterType((e.target as HTMLSelectElement).value)}
            class="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
          >
            <option value="all">All types</option>
            {[...new Set(events.map((event) => event.event_type))].map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
          <select
            value={filterSource}
            onChange={(e) => setFilterSource((e.target as HTMLSelectElement).value)}
            class="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
          >
            <option value="all">All sources</option>
            {[...new Set(events.map((event) => event.source))].map((source) => (
              <option key={source} value={source}>{source}</option>
            ))}
          </select>
        </div>
      </Card>

      {/* Events Table */}
      <Card>
        <Table
          columns={columns}
          data={events.filter((event) => {
            if (filterType !== 'all' && event.event_type !== filterType) return false;
            if (filterSource !== 'all' && event.source !== filterSource) return false;
            return true;
          })}
          loading={loading}
          emptyMessage="No events recorded yet"
          striped
          hover
        />
      </Card>
    </div>
  );
}
