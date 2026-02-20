/**
 * AI tab - OpenAI integration settings
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FiEye, FiEyeOff } from 'react-icons/fi';
import toast from 'react-hot-toast';
import type { AIConfig } from '../../types/api';
import { api } from '../../services/api';
import apiClient from '../../services/api';

interface EventItem {
  id: string
  camera_id?: string
  camera_name?: string
  timestamp: string
  collage_url?: string | null
}

interface AITestResult {
  result?: string
  summary?: string
  error?: string
  prompt?: string
  image_url?: string
  [key: string]: unknown
}

interface AITabProps {
  config: AIConfig;
  onChange: (config: AIConfig) => void;
  onSave: () => void;
}

export const AITab: React.FC<AITabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  const [showApiKey, setShowApiKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const isKeyMasked = config.api_key === '***REDACTED***';
  const [apiKeyDraft, setApiKeyDraft] = useState('');
  const [lastTestedKey, setLastTestedKey] = useState<string | null>(null);
  const [testSuccess, setTestSuccess] = useState(false);
  useEffect(() => {
    if (config.api_key && !isKeyMasked) {
      setApiKeyDraft(config.api_key);
      setLastTestedKey(config.api_key);
      setTestSuccess(true);
    }
  }, [config.api_key, isKeyMasked]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [cameras, setCameras] = useState<{ id: string; name: string }[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string>('');
  const [aiTestLoading, setAiTestLoading] = useState(false);
  const [aiTestResult, setAiTestResult] = useState<AITestResult | null>(null);
  const [aiTestError, setAiTestError] = useState<string | null>(null);

  const templatePreview = () => {
    if (config.prompt_template === 'custom') {
      return config.custom_prompt || t('promptPreviewCustomEmpty');
    }
    return t('aiPromptPreviewDefault');
  };

  const handleSave = () => {
    if (
      config.enabled &&
      config.api_key &&
      config.api_key !== '***REDACTED***' &&
      !config.api_key.startsWith('sk-')
    ) {
      toast.error(t('invalidApiKey'));
      return;
    }
    if (config.enabled && config.api_key && config.api_key !== '***REDACTED***') {
      if (!testSuccess || lastTestedKey !== config.api_key) {
        toast.error(t('aiKeyTestRequired'));
        return;
      }
    }
    onSave();
  };

  const loadEvents = async () => {
    setEventsLoading(true);
    setEventsError(null);
    try {
      const [eventsRes, camerasRes] = await Promise.all([
        api.getEvents({ page: 1, page_size: 20 }),
        api.getCameras(),
      ]);
      const eventList = Array.isArray(eventsRes?.events) ? eventsRes.events : [];
      setEvents(eventList);
      setCameras(camerasRes.cameras || []);
      if (!selectedEventId && eventList.length > 0) {
        setSelectedEventId(eventList[0].id);
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: { message?: string } } }; message?: string }
      setEventsError(err?.response?.data?.detail?.message ?? err?.message ?? t('error'));
    } finally {
      setEventsLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  useEffect(() => {
    setAiTestResult(null);
    setAiTestError(null);
  }, [selectedEventId]);

  const handleTestEvent = async () => {
    if (!selectedEventId) return;
    setAiTestLoading(true);
    setAiTestError(null);
    setAiTestResult(null);
    try {
      const result = await api.testAiEvent(selectedEventId);
      setAiTestResult(result);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: { message?: string } } }; message?: string }
      setAiTestError(err?.response?.data?.detail?.message ?? err?.message ?? t('error'));
    } finally {
      setAiTestLoading(false);
    }
  };

  const selectedEvent = events.find((event) => event.id === selectedEventId);
  const selectedEventImage = selectedEvent?.collage_url || null;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('aiIntegration')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('aiIntegrationDesc')}
        </p>
      </div>

      <div className="p-4 bg-surface2 border-l-4 border-info rounded-lg mb-4">
        <p className="text-sm text-text font-medium">
          ℹ️ {t('aiIntegrationNoteTitle')}
        </p>
        <p className="text-xs text-muted mt-1">
          {t('aiIntegrationNoteDesc')}
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="ai-enabled"
            checked={config.enabled}
            onChange={(e) => onChange({ ...config, enabled: e.target.checked })}
            className="w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
          />
          <label htmlFor="ai-enabled" className="text-sm font-medium text-text">
            {t('enableAISummaries')}
          </label>
        </div>

        {config.enabled && (
          <>
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('apiKey')}
              </label>
              <div className="relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={apiKeyDraft}
                  onChange={(e) => {
                    setApiKeyDraft(e.target.value);
                    setTestSuccess(false);
                    onChange({ ...config, api_key: e.target.value });
                  }}
                  placeholder={isKeyMasked ? t('apiKeySet') : t('aiApiKeyPlaceholder')}
                  className="w-full px-3 py-2 pr-10 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-text"
                >
                  {showApiKey ? <FiEyeOff size={18} /> : <FiEye size={18} />}
                </button>
              </div>
              <p className="text-xs text-muted mt-1">
                {t('aiApiKeyLabel')}
              </p>
              <p className="text-xs text-muted mt-1">
                {(isKeyMasked || apiKeyDraft) ? t('apiKeySet') : t('apiKeyNotSet')}
              </p>
              
              {/* Test Button */}
              <button
                onClick={async () => {
                  if (!apiKeyDraft || apiKeyDraft === '***REDACTED***') {
                    alert(t('aiApiKeyRequired'));
                    return;
                  }
                  setTesting(true);
                  setTestResult(null);
                  try {
                    const response = await apiClient.post('ai/test', { 
                      api_key: apiKeyDraft, 
                      model: config.model 
                    });
                    const data = response.data;
                    setTestResult(data);
                    if (data.success) {
                      setTestSuccess(true);
                      setLastTestedKey(apiKeyDraft);
                      onChange({ ...config, api_key: apiKeyDraft });
                      // Do NOT auto-save; user must click Save explicitly
                    }
                  } catch (error: any) {
                    setTestResult({ success: false, message: error.message });
                  } finally {
                    setTesting(false);
                  }
                }}
                disabled={testing || !apiKeyDraft}
                className="w-full px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors disabled:opacity-50 mt-2"
              >
                {testing ? t('loading') + '...' : t('test')}
              </button>
              
              {/* Test Result */}
              {testResult && (
                <div className={`mt-2 p-3 rounded-lg ${testResult.success ? 'bg-success/10 border border-success/50' : 'bg-error/10 border border-error/50'}`}>
                  <p className={`text-sm ${testResult.success ? 'text-success' : 'text-error'}`}>
                    {testResult.success ? '✅ ' + t('success') : '❌ ' + t('error')}: {testResult.message}
                  </p>
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Model
              </label>
              <select
                value={config.model}
                onChange={(e) => onChange({ ...config, model: e.target.value })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="gpt-4o">gpt-4o ({t('recommended')})</option>
                <option value="gpt-4o-mini">gpt-4o-mini (ucuz)</option>
                <option value="gpt-4-vision-preview">gpt-4-vision-preview (eski)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('promptTemplate')}
              </label>
              <select
                value={config.prompt_template}
                onChange={(e) => onChange({ ...config, prompt_template: e.target.value as AIConfig['prompt_template'] })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="default">default (color/thermal)</option>
                <option value="custom">custom</option>
              </select>
            </div>

            <div className="p-3 rounded-lg border border-border bg-surface2">
              <p className="text-xs text-muted mb-2">{t('promptPreview')}</p>
              <pre className="text-xs text-text whitespace-pre-wrap">{templatePreview()}</pre>
              <p className="text-xs text-muted mt-2">{t('promptLanguageHint')}</p>
            </div>

            {config.prompt_template === 'custom' && (
              <div>
                <label className="block text-sm font-medium text-text mb-2">
                  {t('customPrompt')}
                </label>
                <textarea
                  value={config.custom_prompt}
                  onChange={(e) => onChange({ ...config, custom_prompt: e.target.value })}
                  placeholder={t('customPromptPlaceholder')}
                  rows={5}
                  className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
                />
                <p className="text-xs text-muted mt-1">{t('promptVarsHint')}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('temperature')} ({config.temperature.toFixed(1)})
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={config.temperature}
                onChange={(e) => onChange({ ...config, temperature: parseFloat(e.target.value) })}
                className="w-full"
              />
              <p className="text-xs text-muted mt-1">{t('creativityHint')}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('maxTokens')}
              </label>
              <input
                type="number"
                min="100"
                max="4000"
                value={config.max_tokens}
                onChange={(e) => onChange({ ...config, max_tokens: parseInt(e.target.value) || 1000 })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('timeout')} ({t('seconds')})
              </label>
              <input
                type="number"
                min="5"
                max="120"
                value={config.timeout}
                onChange={(e) => onChange({ ...config, timeout: parseInt(e.target.value) || 30 })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
          </>
        )}
      </div>

      {config.enabled && (
        <div className="p-4 rounded-lg border border-border bg-surface2">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div>
              <p className="text-sm font-medium text-text">{t('aiEventTestTitle')}</p>
              <p className="text-xs text-muted">{t('aiEventTestDesc')}</p>
            </div>
            <button
              onClick={loadEvents}
              disabled={eventsLoading}
              className="px-3 py-1 text-xs bg-surface1/80 text-text rounded-lg hover:bg-surface1 transition-colors disabled:opacity-50"
            >
              {eventsLoading ? t('loading') + '...' : t('refresh')}
            </button>
          </div>

          {eventsError && (
            <p className="text-xs text-error mb-3">{eventsError}</p>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-muted mb-2">
                {t('aiEventSelect')}
              </label>
              <select
                value={selectedEventId}
                onChange={(e) => setSelectedEventId(e.target.value)}
                className="w-full px-3 py-2 bg-surface1 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              >
                {events.length === 0 && (
                  <option value="">{t('aiEventNoEvents')}</option>
                )}
                {events.map((event) => {
                  const cameraName = cameras.find((c: { id: string }) => c.id === event.camera_id)?.name || event.camera_id;
                  return (
                    <option key={event.id} value={event.id}>
                      {new Date(event.timestamp).toLocaleString()} • {cameraName}
                    </option>
                  );
                })}
              </select>

              <button
                onClick={handleTestEvent}
                disabled={!selectedEventId || aiTestLoading}
                className="mt-3 w-full px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors disabled:opacity-50"
              >
                {aiTestLoading ? t('loading') + '...' : t('aiEventRun')}
              </button>

              {aiTestError && (
                <p className="text-xs text-error mt-2">{aiTestError}</p>
              )}
            </div>

            <div>
              <p className="text-xs text-muted mb-2">{t('aiEventImage')}</p>
              {selectedEventImage ? (
                <img
                  src={api.resolveApiPath(selectedEventImage)}
                  alt={t('aiEventImage')}
                  className="w-full rounded-lg border border-border object-contain bg-surface1"
                />
              ) : (
                <div className="text-xs text-muted border border-dashed border-border rounded-lg p-3 bg-surface1">
                  {t('aiEventNoImage')}
                </div>
              )}
            </div>
          </div>

          {aiTestResult?.summary && (
            <div className="mt-4 space-y-3">
              <div>
                <p className="text-xs text-muted mb-2">{t('aiEventPrompt')}</p>
                <pre className="text-xs text-text whitespace-pre-wrap bg-surface1 border border-border rounded-lg p-3">
                  {aiTestResult.prompt}
                </pre>
              </div>
              <div>
                <p className="text-xs text-muted mb-2">{t('aiEventResult')}</p>
                <pre className="text-sm text-text whitespace-pre-wrap bg-surface1 border border-border rounded-lg p-3">
                  {aiTestResult.summary}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      <button
        onClick={handleSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveAISettings')}
      </button>
    </div>
  );
};
