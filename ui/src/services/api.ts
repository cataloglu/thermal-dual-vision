/**
 * API service for Smart Motion Detector v2
 */
import axios from 'axios';
import type { Settings, CameraTestRequest, CameraTestResponse } from '../types/api';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getSettings = async (): Promise<Settings> => {
  const response = await api.get<Settings>('/settings');
  return response.data;
};

export const updateSettings = async (settings: Partial<Settings>): Promise<Settings> => {
  const response = await api.put<Settings>('/settings', settings);
  return response.data;
};

export const testCamera = async (request: CameraTestRequest): Promise<CameraTestResponse> => {
  const response = await api.post<CameraTestResponse>('/cameras/test', request);
  return response.data;
};

export default api;
