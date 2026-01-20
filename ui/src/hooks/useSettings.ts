/**
 * Custom hook for settings management
 */
import { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../services/api';
import type { Settings } from '../types/api';
import toast from 'react-hot-toast';

export const useSettings = () => {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSettings();
      setSettings(data);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: { message?: string } } }; message?: string };
      const errorMsg = error.response?.data?.detail?.message || error.message || 'Failed to load settings';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async (updates: Partial<Settings>) => {
    try {
      const data = await updateSettings(updates);
      setSettings(data);
      toast.success('Settings saved successfully');
      return true;
    } catch (err) {
      const error = err as { response?: { data?: { detail?: { message?: string } } }; message?: string };
      const errorMsg = error.response?.data?.detail?.message || error.message || 'Failed to save settings';
      toast.error(errorMsg);
      return false;
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  return {
    settings,
    loading,
    error,
    loadSettings,
    saveSettings,
  };
};
