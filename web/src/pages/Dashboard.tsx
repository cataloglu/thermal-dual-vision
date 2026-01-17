import { h } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import { Card } from '../components/ui/Card';

/**
 * Dashboard page - System overview with stats and recent detections.
 *
 * Displays:
 * - System status indicators
 * - Key statistics cards (total detections, active time, etc.)
 * - Recent motion detection events
 *
 * Fetches data from:
 * - /api/status - System health and component states
 * - /api/stats - Detection statistics
 * - /api/events?limit=5 - Recent events
 */

interface SystemStatus {
  status: string;
  uptime_seconds: number;
  components: {
    camera: string;
    detector: string;
    mqtt: string;
  };
}

interface SystemStats {
  total_detections: number;
  real_detections: number;
  false_positives: number;
  last_detection?: string;
}

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

export function Dashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [events, setEvents] = useState<DetectionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
    // Refresh data every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setError(null);

      // Fetch all data in parallel
      const [statusRes, statsRes, eventsRes] = await Promise.all([
        fetch('/api/status'),
        fetch('/api/stats'),
        fetch('/api/events?limit=5')
      ]);

      if (!statusRes.ok || !statsRes.ok || !eventsRes.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const [statusData, statsData, eventsData] = await Promise.all([
        statusRes.json(),
        statsRes.json(),
        eventsRes.json()
      ]);

      setStatus(statusData);
      setStats(statsData);
      setEvents(eventsData.events || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  const getStatusColor = (componentStatus: string): string => {
    switch (componentStatus) {
      case 'online':
      case 'connected':
      case 'active':
        return 'bg-green-500';
      case 'offline':
      case 'disconnected':
      case 'inactive':
        return 'bg-red-500';
      default:
        return 'bg-yellow-500';
    }
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

  if (loading) {
    return (
      <div class="flex items-center justify-center min-h-screen">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p class="text-gray-600 dark:text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div class="p-4">
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <h3 class="text-red-800 dark:text-red-200 font-semibold mb-2">Error Loading Dashboard</h3>
          <p class="text-red-600 dark:text-red-400">{error}</p>
          <button
            onClick={fetchDashboardData}
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
          Dashboard
        </h1>
        <p class="text-gray-600 dark:text-gray-400">
          Motion detection system overview
        </p>
      </div>

      {/* System Status */}
      <Card title="System Status">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Overall Status */}
          <div>
            <div class="flex items-center gap-2 mb-1">
              <div class={`w-3 h-3 rounded-full ${status?.status === 'running' ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">System</span>
            </div>
            <p class="text-lg font-semibold text-gray-900 dark:text-gray-100 capitalize">
              {status?.status || 'Unknown'}
            </p>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Uptime: {status ? formatUptime(status.uptime_seconds) : '-'}
            </p>
          </div>

          {/* Camera Status */}
          <div>
            <div class="flex items-center gap-2 mb-1">
              <div class={`w-3 h-3 rounded-full ${getStatusColor(status?.components.camera || 'unknown')}`}></div>
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Camera</span>
            </div>
            <p class="text-lg font-semibold text-gray-900 dark:text-gray-100 capitalize">
              {status?.components.camera || 'Unknown'}
            </p>
          </div>

          {/* MQTT Status */}
          <div>
            <div class="flex items-center gap-2 mb-1">
              <div class={`w-3 h-3 rounded-full ${getStatusColor(status?.components.mqtt || 'unknown')}`}></div>
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">MQTT</span>
            </div>
            <p class="text-lg font-semibold text-gray-900 dark:text-gray-100 capitalize">
              {status?.components.mqtt || 'Unknown'}
            </p>
          </div>
        </div>
      </Card>

      {/* Statistics Cards */}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <div class="text-center">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              Total Detections
            </p>
            <p class="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {stats?.total_detections || 0}
            </p>
          </div>
        </Card>

        <Card>
          <div class="text-center">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              Real Motion
            </p>
            <p class="text-3xl font-bold text-green-600 dark:text-green-400">
              {stats?.real_detections || 0}
            </p>
          </div>
        </Card>

        <Card>
          <div class="text-center">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              False Positives
            </p>
            <p class="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
              {stats?.false_positives || 0}
            </p>
          </div>
        </Card>

        <Card>
          <div class="text-center">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              Accuracy
            </p>
            <p class="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {stats?.total_detections
                ? Math.round((stats.real_detections / stats.total_detections) * 100)
                : 0}%
            </p>
          </div>
        </Card>
      </div>

      {/* Recent Events */}
      <Card
        title="Recent Events"
        actions={
          <a
            href="/events"
            class="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            View All
          </a>
        }
      >
        {events.length === 0 ? (
          <div class="text-center py-8 text-gray-500 dark:text-gray-400">
            No recent events
          </div>
        ) : (
          <div class="space-y-3">
            {events.map((event) => (
              <div
                key={event.id}
                class="flex items-start gap-4 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                {/* Status Indicator */}
                <div class="flex-shrink-0 mt-1">
                  <div
                    class={`w-2 h-2 rounded-full ${
                      event.analysis.real_motion
                        ? 'bg-green-500'
                        : 'bg-yellow-500'
                    }`}
                  ></div>
                </div>

                {/* Event Details */}
                <div class="flex-1 min-w-0">
                  <div class="flex items-start justify-between gap-2 mb-1">
                    <p class="font-medium text-gray-900 dark:text-gray-100">
                      {event.analysis.real_motion ? 'Motion Detected' : 'Possible Motion'}
                    </p>
                    <span class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {formatTimestamp(event.timestamp)}
                    </span>
                  </div>

                  <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {event.analysis.description}
                  </p>

                  <div class="flex flex-wrap items-center gap-2 text-xs">
                    <span class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                      Confidence: {Math.round(event.analysis.confidence_score * 100)}%
                    </span>
                    {event.analysis.threat_level && (
                      <span class={`px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 font-medium ${getThreatColor(event.analysis.threat_level)}`}>
                        Threat: {event.analysis.threat_level}
                      </span>
                    )}
                    {event.analysis.detected_objects.length > 0 && (
                      <span class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                        Objects: {event.analysis.detected_objects.join(', ')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
