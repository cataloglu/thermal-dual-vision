/**
 * API service for Smart Motion Detector v2
 */
import axios from 'axios';
import type { Settings, CameraTestRequest, CameraTestResponse } from '../types/api';

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
  getLiveStreams,
};

export default apiClient;
