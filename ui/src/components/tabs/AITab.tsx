/**
 * AI tab - OpenAI integration settings
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FiEye, FiEyeOff } from 'react-icons/fi';
import type { AIConfig } from '../../types/api';

interface AITabProps {
  config: AIConfig;
  onChange: (config: AIConfig) => void;
  onSave: () => void;
}

export const AITab: React.FC<AITabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  const [showApiKey, setShowApiKey] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('aiIntegration')}</h3>
        <p className="text-sm text-muted mb-6">
          Configure OpenAI integration for event summaries (optional)
        </p>
      </div>

      <div className="p-4 bg-surface2 border-l-4 border-info rounded-lg mb-4">
        <p className="text-sm text-text font-medium">
          ℹ️ AI entegrasyonu opsiyoneldir. Sistem AI olmadan da çalışır.
        </p>
        <p className="text-xs text-muted mt-1">
          AI sadece event'lere açıklama ekler, filtreleme yapmaz.
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
            Enable AI Summaries
          </label>
        </div>

        {config.enabled && (
          <>
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                API Key
              </label>
              <div className="relative">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={config.api_key === '***REDACTED***' ? '' : config.api_key}
                  onChange={(e) => onChange({ ...config, api_key: e.target.value })}
                  placeholder={config.api_key === '***REDACTED***' ? 'API key is set' : 'sk-...'}
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
                OpenAI API key (starts with sk-)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Model
              </label>
              <input
                type="text"
                value={config.model}
                onChange={(e) => onChange({ ...config, model: e.target.value })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <p className="text-xs text-muted mt-1">
                OpenAI model name (e.g., gpt-4, gpt-3.5-turbo)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Max Tokens
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
                Timeout (seconds)
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

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveAISettings')}
      </button>
    </div>
  );
};
