/**
 * API service for Smart Motion Detector v2
 */
import axios from 'axios';
import type { Settings, CameraTestRequest, CameraTestResponse, Zone } from '../types/api';

const resolveIngressApiBase = () => {
  const path = window.location.pathname || '';
  const cleanPath = path.replace(/\/index\.html$/, '').replace(/\/+$/, '');

  const ingressMatch = cleanPath.match(/(\/api\/hassio_ingress\/[^/]+)/);
  if (ingressMatch) {
    return `${ingressMatch[1]}/api`;
  }

  return '/api';
};

// Use injected config from Nginx sub_filter (Frigate style),
// but fall back to ingress path detection when needed.
const getBaseUrl = () => {
  // @ts-ignore
  if (window.env && window.env.API_URL) {
    // @ts-ignore
    const envUrl = window.env.API_URL as string;

    if (envUrl.startsWith('http')) {
      return envUrl;
    }

    if (envUrl !== '/api') {
      return envUrl;
    }

    return resolveIngressApiBase();
  }

  if (import.meta.env.DEV) {
    return import.meta.env.VITE_API_URL ?? '/api';
  }

  return resolveIngressApiBase();
};

const API_BASE_URL = getBaseUrl();

const joinApiUrl = (path: string) => {
  const normalized = path.startsWith('/') ? path.slice(1) : path;
  
  if (API_BASE_URL.startsWith('http')) {
    return `${API_BASE_URL.replace(/\/+$/, '')}/${normalized}`;
  }
  
  // Ensure we don't double slash if API_BASE_URL ends with /
  const separator = API_BASE_URL.endsWith('/') ? '' : '/';
  return `${API_BASE_URL}${separator}${normalized}`;
};

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Dedupe 502 toasts - avoid spamming when backend/addon is starting
let last502Toast = 0;
const FIVE_SEC = 5000;
apiClient.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 502) {
      const now = Date.now();
      if (now - last502Toast < FIVE_SEC) {
        err._suppressToast = true;
      } else {
        last502Toast = now;
      }
    }
    return Promise.reject(err);
  }
);

// Health & System
export const getHealth = async () => {
  const response = await apiClient.get('health');
  return response.data;
};

export const getSystemInfo = async () => {
  const response = await apiClient.get('system/info');
  return response.data;
};

export const getLogs = async (lines = 200) => {
  const response = await apiClient.get('logs', { params: { lines } });
  return response.data;
};

export const clearLogs = async () => {
  const response = await apiClient.post('logs/clear');
  return response.data;
};

// Settings
export const getSettings = async (): Promise<Settings> => {
  const response = await apiClient.get<Settings>('settings');
  return response.data;
};

export const updateSettings = async (settings: Partial<Settings>): Promise<Settings> => {
  const response = await apiClient.put<Settings>('settings', settings);
  return response.data;
};

export const getDefaultSettings = async (): Promise<Settings> => {
  const response = await apiClient.get<Settings>('settings/defaults');
  return response.data;
};

export const resetSettings = async (): Promise<Settings> => {
  const response = await apiClient.post<Settings>('settings/reset');
  return response.data;
};

// Cameras
export const getCameras = async () => {
  const response = await apiClient.get('cameras');
  return response.data;
};

export const createCamera = async (payload: Record<string, unknown>) => {
  const response = await apiClient.post('cameras', payload);
  return response.data;
};

export const updateCamera = async (cameraId: string, payload: Record<string, unknown>) => {
  const response = await apiClient.put(`cameras/${cameraId}`, payload);
  return response.data;
};

export const deleteCamera = async (cameraId: string): Promise<{ deleted: boolean }> => {
  const response = await apiClient.delete(`cameras/${cameraId}`);
  // Backend returns 204 No Content (no body)
  return response.status === 204 ? { deleted: true } : (response.data ?? { deleted: true });
};

export const getRecordingStatus = async (cameraId: string) => {
  const response = await apiClient.get(`cameras/${cameraId}/record`);
  return response.data;
};

export const startRecording = async (cameraId: string) => {
  const response = await apiClient.post(`cameras/${cameraId}/record/start`);
  return response.data;
};

export const stopRecording = async (cameraId: string) => {
  const response = await apiClient.post(`cameras/${cameraId}/record/stop`);
  return response.data;
};

export const testCamera = async (request: CameraTestRequest): Promise<CameraTestResponse> => {
  const response = await apiClient.post<CameraTestResponse>('cameras/test', request);
  return response.data;
};

export const testTelegram = async (payload: { bot_token?: string; chat_ids: string[]; event_id?: string }) => {
  const response = await apiClient.post('telegram/test', payload);
  return response.data;
};

export const testAiEvent = async (eventId: string) => {
  const response = await apiClient.post('ai/test-event', { event_id: eventId });
  return response.data;
};

// Events
export const getEvents = async (params: {
  page?: number;
  page_size?: number;
  camera_id?: string;
  date?: string;
  confidence?: number;
}) => {
  const response = await apiClient.get('events', { params });
  return response.data;
};

export const getEvent = async (eventId: string) => {
  const response = await apiClient.get(`events/${eventId}`);
  return response.data;
};

export const deleteEvent = async (eventId: string) => {
  const response = await apiClient.delete(`events/${eventId}`);
  return response.data;
};

export const bulkDeleteEvents = async (eventIds: string[]) => {
  const response = await apiClient.post('events/bulk-delete', { event_ids: eventIds });
  return response.data;
};

export const deleteEventsFiltered = async (filters: {
  camera_id?: string;
  date?: string;
  min_confidence?: number;
}) => {
  const response = await apiClient.post('events/clear', filters);
  return response.data;
};

export const getCameraSnapshotUrl = (cameraId: string) =>
  joinApiUrl(`cameras/${cameraId}/snapshot`);

export const getLiveStreamUrl = (cameraId: string) =>
  joinApiUrl(`live/${cameraId}.mjpeg`);

export const getCameraZones = async (cameraId: string): Promise<{ zones: Zone[] }> => {
  const response = await apiClient.get(`cameras/${cameraId}/zones`);
  return response.data;
};

export const createCameraZone = async (
  cameraId: string,
  zone: { name: string; mode: Zone['mode']; polygon: Zone['polygon']; enabled?: boolean }
): Promise<Zone> => {
  const response = await apiClient.post(`cameras/${cameraId}/zones`, zone);
  return response.data;
};

export const updateZone = async (
  zoneId: string,
  payload: { name?: string; enabled?: boolean; mode?: Zone['mode']; polygon?: Zone['polygon'] }
): Promise<Zone> => {
  const response = await apiClient.put<Zone>(`zones/${zoneId}`, payload);
  return response.data;
};

export const deleteZone = async (zoneId: string) => {
  const response = await apiClient.delete(`zones/${zoneId}`);
  return response.data;
};

// Live Streams
export const getLiveStreams = async () => {
  const response = await apiClient.get('live');
  return response.data;
};

// MQTT Monitoring
export const getMqttStatus = async () => {
  const response = await apiClient.get('mqtt/status');
  return response.data;
};

export const api = {
  getHealth,
  getSystemInfo,
  getLogs,
  clearLogs,
  getSettings,
  updateSettings,
  getDefaultSettings,
  resetSettings,
  getCameras,
  createCamera,
  updateCamera,
  deleteCamera,
  getRecordingStatus,
  startRecording,
  stopRecording,
  testCamera,
  testTelegram,
  testAiEvent,
  getEvents,
  getEvent,
  deleteEvent,
  bulkDeleteEvents,
  deleteEventsFiltered,
  getLiveStreams,
  getCameraSnapshotUrl,
  getCameraZones,
  createCameraZone,
  updateZone,
  deleteZone,
  getMqttStatus,
};

export default apiClient;
