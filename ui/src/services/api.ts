/**
 * API service for Smart Motion Detector v2
 */
import axios from 'axios';
import type { Settings, CameraTestRequest, CameraTestResponse, Zone } from '../types/api';

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health & System
export const getHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

// Settings
export const getSettings = async (): Promise<Settings> => {
  const response = await apiClient.get<Settings>('/settings');
  return response.data;
};

export const updateSettings = async (settings: Partial<Settings>): Promise<Settings> => {
  const response = await apiClient.put<Settings>('/settings', settings);
  return response.data;
};

// Cameras
export const getCameras = async () => {
  const response = await apiClient.get('/cameras');
  return response.data;
};

export const testCamera = async (request: CameraTestRequest): Promise<CameraTestResponse> => {
  const response = await apiClient.post<CameraTestResponse>('/cameras/test', request);
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
  const response = await apiClient.get('/events', { params });
  return response.data;
};

export const getEvent = async (eventId: string) => {
  const response = await apiClient.get(`/events/${eventId}`);
  return response.data;
};

export const deleteEvent = async (eventId: string) => {
  const response = await apiClient.delete(`/events/${eventId}`);
  return response.data;
};

export const getCameraSnapshotUrl = (cameraId: string) => `/api/cameras/${cameraId}/snapshot`;

export const getCameraZones = async (cameraId: string): Promise<{ zones: Zone[] }> => {
  const response = await apiClient.get(`/cameras/${cameraId}/zones`);
  return response.data;
};

export const createCameraZone = async (
  cameraId: string,
  zone: { name: string; mode: Zone['mode']; polygon: Zone['polygon']; enabled?: boolean }
): Promise<Zone> => {
  const response = await apiClient.post(`/cameras/${cameraId}/zones`, zone);
  return response.data;
};

export const deleteZone = async (zoneId: string) => {
  const response = await apiClient.delete(`/zones/${zoneId}`);
  return response.data;
};

// Live Streams
export const getLiveStreams = async () => {
  const response = await apiClient.get('/live');
  return response.data;
};

export const api = {
  getHealth,
  getSettings,
  updateSettings,
  getCameras,
  testCamera,
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
