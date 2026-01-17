import { h } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import { Table, TableColumn } from '../components/ui/Table';
import { Card } from '../components/ui/Card';

/**
 * Events page - Complete list of motion detection events.
 *
 * Displays all motion detection events in a sortable table format,
 * showing timestamp, detection status, confidence, and analysis details.
 *
 * Features:
 * - Table view with all event details
 * - Real-time status indicators
 * - Confidence scores and threat levels
 * - Loading and error states with retry
 * - Auto-refresh every 30 seconds
 *
 * Fetches data from:
 * - /api/events - List of all detection events
 */

interface DetectionEvent {
  id: string;
  timestamp: string;
  has_screenshots: boolean;
  analysis: {
    real_motion: boolean;
    confidence_score: number;
    description: string;
    detected_objects: string[];
    threat_level?: string;
  };
}

interface EventsResponse {
  events: DetectionEvent[];
  count: number;
  timestamp: string;
}

export function Events() {
  const [events, setEvents] = useState<DetectionEvent[]>([]);
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

      const response = await fetch('/api/events');
      if (!response.ok) {
        throw new Error('Failed to fetch events');
      }

      const data: EventsResponse = await response.json();
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

  const getThreatColor = (threatLevel?: string): string => {
    switch (threatLevel) {
      case 'high':
        return 'text-red-600 dark:text-red-400';
      case 'medium':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'low':
        return 'text-green-600 dark:text-green-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const columns: TableColumn<DetectionEvent>[] = [
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
        <div class="flex items-center gap-2">
          <div
            class={`w-2 h-2 rounded-full ${
              event.analysis.real_motion ? 'bg-green-500' : 'bg-yellow-500'
            }`}
          ></div>
          <span class={`font-medium ${
            event.analysis.real_motion
              ? 'text-green-600 dark:text-green-400'
              : 'text-yellow-600 dark:text-yellow-400'
          }`}>
            {event.analysis.real_motion ? 'Motion' : 'Possible'}
          </span>
        </div>
      )
    },
    {
      key: 'description',
      label: 'Description',
      render: (event) => (
        <div class="min-w-0">
          <p class="text-gray-900 dark:text-gray-100 truncate">
            {event.analysis.description}
          </p>
          {event.analysis.detected_objects.length > 0 && (
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Objects: {event.analysis.detected_objects.join(', ')}
            </p>
          )}
        </div>
      )
    },
    {
      key: 'confidence',
      label: 'Confidence',
      width: 'w-28',
      render: (event) => (
        <div class="text-center">
          <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
            {Math.round(event.analysis.confidence_score * 100)}%
          </div>
          <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mt-1">
            <div
              class={`h-1.5 rounded-full ${
                event.analysis.confidence_score >= 0.8
                  ? 'bg-green-500'
                  : event.analysis.confidence_score >= 0.5
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${event.analysis.confidence_score * 100}%` }}
            ></div>
          </div>
        </div>
      )
    },
    {
      key: 'threat',
      label: 'Threat Level',
      width: 'w-28',
      render: (event) => (
        <div class="text-center">
          {event.analysis.threat_level ? (
            <span class={`font-medium capitalize ${getThreatColor(event.analysis.threat_level)}`}>
              {event.analysis.threat_level}
            </span>
          ) : (
            <span class="text-gray-400 dark:text-gray-600">-</span>
          )}
        </div>
      )
    },
    {
      key: 'screenshots',
      label: 'Screenshots',
      width: 'w-24',
      render: (event) => (
        <div class="text-center">
          {event.has_screenshots ? (
            <a
              href={`/gallery#${event.id}`}
              class="text-primary-600 dark:text-primary-400 hover:underline text-sm"
            >
              View
            </a>
          ) : (
            <span class="text-gray-400 dark:text-gray-600 text-sm">None</span>
          )}
        </div>
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

      {/* Events Table */}
      <Card>
        <Table
          columns={columns}
          data={events}
          loading={loading}
          emptyMessage="No events recorded yet"
          striped
          hover
        />
      </Card>
    </div>
  );
}
