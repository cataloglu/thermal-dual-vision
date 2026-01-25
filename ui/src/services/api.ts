/**
 * API service for Smart Motion Detector v2
 */
import axios from 'axios';
import type { Settings, CameraTestRequest, CameraTestResponse, Zone } from '../types/api';

const resolveIngressApiBase = () => {
  const path = window.location.pathname || '';
  const cleanPath = path.replace(/\/index\.html$/, '').replace(/\/+$/, '');

  if (!cleanPath || cleanPath === '/') {
    return '/api';
  }

  return `${cleanPath}/api`;
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

export const deleteCamera = async (cameraId: string) => {
  const response = await apiClient.delete(`cameras/${cameraId}`);
  return response.data;
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

export const getCameraSnapshotUrl = (cameraId: string) =>
  joinApiUrl(`cameras/${cameraId}/snapshot`);

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

export const deleteZone = async (zoneId: string) => {
  const response = await apiClient.delete(`zones/${zoneId}`);
  return response.data;
};

// Live Streams
export const getLiveStreams = async () => {
  const response = await apiClient.get('live');
  return response.data;
};

export const api = {
  getHealth,
  getSystemInfo,
  getLogs,
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
  getLiveStreams,
  getCameraSnapshotUrl,
  getCameraZones,
  createCameraZone,
  deleteZone,
};

export default apiClient;
