/**
 * Custom hook for settings management
 */
import { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../services/api';
import type { Settings } from '../types/api';
import toast from 'react-hot-toast';

const MASKED_VALUE = '***REDACTED***'

const mergeMaskedSecrets = (data: Settings, updates: Partial<Settings>) => {
  const merged = { ...data }
  if (updates.ai?.api_key && data.ai?.api_key === MASKED_VALUE) {
    merged.ai = { ...data.ai, api_key: updates.ai.api_key }
  }
  if (updates.telegram?.bot_token && data.telegram?.bot_token === MASKED_VALUE) {
    merged.telegram = { ...data.telegram, bot_token: updates.telegram.bot_token }
  }
  if (
    updates.mqtt?.password &&
    updates.mqtt.password !== MASKED_VALUE &&
    data.mqtt?.password === MASKED_VALUE
  ) {
    merged.mqtt = { ...data.mqtt, password: updates.mqtt.password }
  }
  return merged
}

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
      const merged = mergeMaskedSecrets(data, updates);
      setSettings(merged);
      toast.success('Settings saved successfully');
      return merged;
    } catch (err) {
      const error = err as { response?: { data?: { detail?: { message?: string } } }; message?: string };
      const errorMsg = error.response?.data?.detail?.message || error.message || 'Failed to save settings';
      toast.error(errorMsg);
      return null;
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
