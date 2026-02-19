/**
 * API service for Smart Motion Detector v2
 */
import axios from 'axios';
import type { Settings, CameraTestRequest, CameraTestResponse, Zone } from '../types/api';

/** Ingress base path (e.g. /api/hassio_ingress/TOKEN). HA addon Ingress full destek. */
export const getIngressBase = (): string => {
  const path = window.location.pathname || '';
  const m = path.match(/(\/api\/hassio_ingress\/[^/]+)/);
  return m ? m[1] : '';
};

const resolveIngressApiBase = (): string => {
  const base = getIngressBase();
  return base ? `${base}/api` : '/api';
};

// Nginx sub_filter injects API_URL; pathname fallback for Ingress
const getBaseUrl = (): string => {
  // @ts-ignore
  const envUrl = window.env?.API_URL as string | undefined;
  if (envUrl?.startsWith('http')) return envUrl;
  if (envUrl && envUrl !== '/api') return envUrl;
  if (import.meta.env.DEV) return import.meta.env.VITE_API_URL ?? '/api';
  return resolveIngressApiBase();
};

/**
 * Her API/media URL icin Ingress prefix saglar. Tum img src, video src, href'ler icin kullan.
 * Backend /api/... dondurse bile Ingress modda /api/hassio_ingress/TOKEN/api/... olur.
 */
export const resolveApiPath = (path: string | null | undefined): string => {
  if (!path || typeof path !== 'string') return '';
  const base = getIngressBase();
  if (!base) return path;
  if (path.startsWith(base)) return path;
  return base + (path.startsWith('/') ? path : '/' + path);
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
  rejected?: boolean;
}) => {
  const response = await apiClient.get('events', { params });
  return response.data;
};

export const analyzeVideo = async (params: { event_id?: string; path?: string }) => {
  const response = await apiClient.post('video/analyze', params);
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

export const getLiveSnapshotUrl = (cameraId: string) =>
  joinApiUrl(`live/${cameraId}.jpg`);

export const getLiveWebRTCUrl = (cameraId: string) =>
  joinApiUrl(`live/${cameraId}/webrtc`);

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

// Camera Status Monitor
export const getCamerasStatus = async () => {
  const response = await apiClient.get('cameras/status');
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
  resolveApiPath,
  getIngressBase,
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
  analyzeVideo,
  deleteEvent,
  bulkDeleteEvents,
  deleteEventsFiltered,
  getCamerasStatus,
  getLiveStreams,
  getLiveWebRTCUrl,
  getCameraSnapshotUrl,
  getCameraZones,
  createCameraZone,
  updateZone,
  deleteZone,
  getMqttStatus,
};

export default apiClient;
