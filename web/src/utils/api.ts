/**
 * API Utility Module
 *
 * Provides a centralized fetch wrapper for making API requests
 * with error handling, base URL handling for HA ingress path,
 * and TypeScript interfaces for all API responses.
 *
 * Features:
 * - Automatic JSON serialization/deserialization
 * - Error handling with descriptive messages
 * - Base URL handling for Home Assistant ingress
 * - TypeScript interfaces for type safety
 */

// ============================================================================
// TypeScript Interfaces for API Responses
// ============================================================================

/**
 * System status response from /api/status
 */
export interface SystemStatus {
  status: string;
  uptime_seconds: number;
  components: {
    camera?: string;
    detector?: string;
    motion_detection?: string;
    mqtt?: string;
    [key: string]: string | undefined;
  };
}

/**
 * System statistics response from /api/stats
 */
export interface SystemStats {
  total_detections: number;
  real_detections: number;
  false_positives: number;
  last_detection?: string;
}

/**
 * Detection event analysis details
 */
export interface EventDetection {
  real_motion?: boolean;
  confidence_score?: number;
  description?: string;
  detected_objects?: string[];
  threat_level?: string;
  recommended_action?: string;
  detailed_analysis?: string;
  processing_time?: number;
}

export interface EventItem {
  id: string;
  timestamp: string;
  camera_name?: string;
  event_type?: string;
  detection?: EventDetection;
  retry_count?: number;
}

/**
 * Events list response from /api/events
 */
export interface EventsResponse {
  events: EventItem[];
  total?: number;
  count?: number;
}

/**
 * Screenshot metadata from /api/screenshots
 */
export interface Screenshot {
  id: string;
  timestamp: string;
  has_before: boolean;
  has_early: boolean;
  has_peak: boolean;
  has_late: boolean;
  has_after: boolean;
  analysis?: {
    gercek_hareket?: boolean;
    guven_skoru?: number;
    degisiklik_aciklamasi?: string;
    tespit_edilen_nesneler?: string[];
    tehdit_seviyesi?: string;
    detayli_analiz?: string;
    processing_time?: number;
  };
}

/**
 * Screenshots list response from /api/screenshots
 */
export interface ScreenshotsResponse {
  screenshots: Screenshot[];
  total?: number;
}

/**
 * Configuration sections
 */
export interface CameraConfig {
  url: string;
  fps: number;
  resolution: [number, number];
}

export interface MotionConfig {
  sensitivity: number;
  min_area: number;
  cooldown_seconds: number;
}

export interface YoloConfig {
  model: string;
  confidence: number;
  classes: string[];
}

export interface LLMConfig {
  api_key: string;
  enabled: boolean;
  model: string;
  max_tokens: number;
  timeout: number;
}

export interface ScreenshotConfig {
  window_seconds: number;
  quality: number;
  max_stored: number;
  buffer_seconds: number;
}

export interface MQTTConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  topic_prefix: string;
  discovery: boolean;
  discovery_prefix: string;
  qos: number;
}

export interface TelegramConfig {
  enabled: boolean;
  bot_token: string;
  chat_ids: string[];
  rate_limit_seconds: number;
  send_images: boolean;
  video_speed: number;
  event_types: string[];
  cooldown_seconds: number;
  max_messages_per_min: number;
  snapshot_quality: number;
}

export interface RetryPolicyConfig {
  initial_delay: number;
  max_delay: number;
  multiplier: number;
  jitter: number;
  max_retries?: number | null;
}

export interface GeneralConfig {
  bind_host: string;
  http_port: number;
  timezone: string;
}

/**
 * Full configuration response from /api/config
 */
export interface Config {
  camera: CameraConfig;
  motion: MotionConfig;
  yolo: YoloConfig;
  llm: LLMConfig;
  screenshots: ScreenshotConfig;
  mqtt: MQTTConfig;
  telegram: TelegramConfig;
  retry_policy: RetryPolicyConfig;
  general: GeneralConfig;
  log_level: string;
}

export interface Camera {
  id: string;
  name: string;
  type: 'color' | 'thermal' | 'dual';
  rtsp_url_color: string;
  rtsp_url_thermal: string;
  channel_color?: number;
  channel_thermal?: number;
  status: string;
  last_error?: string;
  last_frame_ts?: number;
  event_count?: number;
}

export interface CamerasResponse {
  cameras: Camera[];
}

export interface CameraTestResponse {
  ok: boolean;
  snapshot?: string;
  error?: string;
}

export interface PipelineState {
  status: string;
  detail?: string;
  updated_at?: number;
}

export interface PipelineStatusResponse {
  pipeline: PipelineState;
}
/**
 * Health response from /api/health
 */
export interface HealthResponse {
  status: string;
  ai_enabled?: boolean;
  pipeline?: PipelineState;
  components?: Record<string, any>;
}

/**
 * Logs tail response from /api/logs/tail
 */
export interface LogsTailResponse {
  lines: string[];
}

/**
 * Metrics response from /api/metrics
 */
export interface MetricsResponse {
  uptime_seconds: number;
  events_count: number;
  pipeline?: PipelineState;
}
/**
 * Generic error response from API
 */
export interface ApiError {
  error: string;
  details?: string;
}

// ============================================================================
// API Client Configuration
// ============================================================================

/**
 * Get the base URL for API requests.
 *
 * In development, Vite proxies /api requests to the Flask backend.
 * In production, the Flask backend serves the frontend and handles
 * Home Assistant ingress path automatically.
 *
 * @returns Base URL for API requests (empty string for relative URLs)
 */
function getBaseUrl(): string {
  // Always use relative URLs - Vite proxy handles dev, Flask handles prod
  return '';
}

// ============================================================================
// API Client Methods
// ============================================================================

/**
 * Custom error class for API errors
 */
export class ApiRequestError extends Error {
  public status: number;
  public statusText: string;
  public details?: string;

  constructor(message: string, status: number, statusText: string, details?: string) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.statusText = statusText;
    this.details = details;
  }
}

/**
 * Make an API request with error handling.
 *
 * @param endpoint - API endpoint (e.g., '/api/status')
 * @param options - Fetch options
 * @returns Promise with parsed JSON response
 * @throws ApiRequestError if request fails
 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${getBaseUrl()}${endpoint}`;

  // Set default headers
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Parse response body
    let data: any;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    // Check if request was successful
    if (!response.ok) {
      const errorMessage = typeof data === 'object' && data.error
        ? data.error
        : `Request failed: ${response.status} ${response.statusText}`;
      const errorDetails = typeof data === 'object' && data.details
        ? data.details
        : undefined;

      throw new ApiRequestError(
        errorMessage,
        response.status,
        response.statusText,
        errorDetails
      );
    }

    return data as T;
  } catch (error) {
    // Re-throw ApiRequestError as-is
    if (error instanceof ApiRequestError) {
      throw error;
    }

    // Handle network errors
    if (error instanceof TypeError) {
      throw new ApiRequestError(
        'Network error: Unable to connect to server',
        0,
        'Network Error'
      );
    }

    // Handle other errors
    throw new ApiRequestError(
      error instanceof Error ? error.message : 'Unknown error occurred',
      0,
      'Unknown Error'
    );
  }
}

/**
 * Make a GET request to the API.
 *
 * @param endpoint - API endpoint (e.g., '/api/status')
 * @returns Promise with parsed JSON response
 */
export async function get<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, {
    method: 'GET',
  });
}

/**
 * Make a POST request to the API.
 *
 * @param endpoint - API endpoint (e.g., '/api/config')
 * @param body - Request body (will be JSON stringified)
 * @returns Promise with parsed JSON response
 */
export async function post<T>(endpoint: string, body: any): Promise<T> {
  return request<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Make a DELETE request to the API.
 *
 * @param endpoint - API endpoint (e.g., '/api/screenshots/123')
 * @returns Promise with parsed JSON response
 */
export async function del<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, {
    method: 'DELETE',
  });
}

// ============================================================================
// Convenience API Methods
// ============================================================================

/**
 * Fetch system status from /api/status
 */
export async function getStatus(): Promise<SystemStatus> {
  return get<SystemStatus>('/api/status');
}

/**
 * Fetch system statistics from /api/stats
 */
export async function getStats(): Promise<SystemStats> {
  return get<SystemStats>('/api/stats');
}

/**
 * Fetch detection events from /api/events
 *
 * @param limit - Maximum number of events to return
 */
export async function getEvents(limit?: number): Promise<EventsResponse> {
  const url = limit ? `/api/events?limit=${limit}` : '/api/events';
  return get<EventsResponse>(url);
}

/**
 * Fetch screenshots from /api/screenshots
 */
export async function getScreenshots(limit?: number): Promise<ScreenshotsResponse> {
  const url = limit ? `/api/screenshots?limit=${limit}` : '/api/screenshots';
  return get<ScreenshotsResponse>(url);
}

export function getScreenshotCollageUrl(id: string): string {
  return `/api/screenshots/${id}/collage`;
}

export function getScreenshotClipUrl(id: string): string {
  return `/api/screenshots/${id}/clip.mp4`;
}

/**
 * Fetch configuration from /api/config
 */
export async function getConfig(): Promise<Config> {
  return get<Config>('/api/config');
}

export async function getCameras(): Promise<CamerasResponse> {
  return get<CamerasResponse>('/api/cameras');
}

export async function getCamera(id: string): Promise<Camera> {
  return get<Camera>(`/api/cameras/${id}`);
}

export async function createCamera(payload: Partial<Camera>): Promise<Camera> {
  return post<Camera>('/api/cameras', payload);
}

export async function testCameraPayload(payload: Partial<Camera>): Promise<CameraTestResponse> {
  return post<CameraTestResponse>('/api/cameras/test', payload);
}

export async function getPipelineStatus(): Promise<PipelineStatusResponse> {
  return get<PipelineStatusResponse>('/api/pipeline/status');
}

export async function getHealth(): Promise<HealthResponse> {
  return get<HealthResponse>('/api/health');
}

export async function getMetrics(): Promise<MetricsResponse> {
  return get<MetricsResponse>('/api/metrics');
}

export async function getLogsTail(lines: number = 200): Promise<LogsTailResponse> {
  return get<LogsTailResponse>(`/api/logs/tail?lines=${lines}`);
}

export async function startPipeline(): Promise<{ started: boolean }> {
  return post<{ started: boolean }>('/api/pipeline/start', {});
}

export async function stopPipeline(): Promise<{ stopped: boolean }> {
  return post<{ stopped: boolean }>('/api/pipeline/stop', {});
}

export async function restartPipeline(): Promise<{ restarted: boolean }> {
  return post<{ restarted: boolean }>('/api/pipeline/restart', {});
}

export async function getTelegramSettings(): Promise<TelegramConfig> {
  return get<TelegramConfig>('/api/notifications/telegram');
}

export async function updateTelegramSettings(payload: Partial<TelegramConfig>): Promise<TelegramConfig> {
  return post<TelegramConfig>('/api/notifications/telegram', payload);
}

export async function sendTelegramTestMessage(): Promise<{ sent: boolean }> {
  return post<{ sent: boolean }>('/api/notifications/telegram/test-message', {});
}

export async function sendTelegramTestSnapshot(cameraId: string): Promise<{ sent: boolean }> {
  return post<{ sent: boolean }>('/api/notifications/telegram/test-snapshot', { camera_id: cameraId });
}
/**
 * Update configuration via /api/config
 *
 * @param config - New configuration object
 */
export async function updateConfig(config: Config): Promise<Config> {
  return post<Config>('/api/config', config);
}

/**
 * Delete a screenshot by ID
 *
 * @param id - Screenshot ID
 */
export async function deleteScreenshot(id: string): Promise<{ success: boolean }> {
  return del<{ success: boolean }>(`/api/screenshots/${id}`);
}

// ============================================================================
// Export default API client object
// ============================================================================

/**
 * Default API client object with all methods
 */
export const api = {
  get,
  post,
  del,
  getStatus,
  getStats,
  getEvents,
  getScreenshots,
  getScreenshotCollageUrl,
  getScreenshotClipUrl,
  getConfig,
  updateConfig,
  deleteScreenshot,
  getCameras,
  getCamera,
  createCamera,
  testCameraPayload,
  getPipelineStatus,
  getHealth,
  getMetrics,
  getLogsTail,
  startPipeline,
  stopPipeline,
  restartPipeline,
  getTelegramSettings,
  updateTelegramSettings,
  sendTelegramTestMessage,
  sendTelegramTestSnapshot,
};

export default api;
