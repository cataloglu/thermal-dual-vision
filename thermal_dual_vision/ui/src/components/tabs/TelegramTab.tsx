/**
 * Telegram tab - Telegram notification settings
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FiEye, FiEyeOff } from 'react-icons/fi';
import toast from 'react-hot-toast';
import type { TelegramConfig } from '../../types/api';
import { api } from '../../services/api';

interface TelegramTabProps {
  config: TelegramConfig;
  onChange: (config: TelegramConfig) => void;
  onSave: (nextConfig?: TelegramConfig) => void;
}

export const TelegramTab: React.FC<TelegramTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  const [showBotToken, setShowBotToken] = useState(true);
  const [chatIdInput, setChatIdInput] = useState('');
  const [testing, setTesting] = useState(false);
  const isBotMasked = config.bot_token === '***REDACTED***';
  const [botTokenDraft, setBotTokenDraft] = useState('');
  const [lastTestedToken, setLastTestedToken] = useState<string | null>(null);
  const [testSuccess, setTestSuccess] = useState(false);
  const maskedDisplay = '********';
  const tokenIsSaved = isBotMasked || Boolean(botTokenDraft);
  const tokenStatusText = isBotMasked ? t('botTokenSavedHidden') : (botTokenDraft ? t('botTokenSet') : t('botTokenNotSet'));
  const tokenStatusClass = tokenIsSaved ? 'bg-success/10 text-success border-success/40' : 'bg-error/10 text-error border-error/40';

  const isValidBotToken = (value: string) => /^\d+:[A-Za-z0-9_-]{20,}$/.test(value);
  const isValidChatId = (value: string) => /^-?\d+$/.test(value);
  const normalizeToken = (value: string) => (value === maskedDisplay ? '' : value.trim());

  const handleAddChatId = () => {
    const trimmed = chatIdInput.trim();
    if (trimmed && !isValidChatId(trimmed)) {
      toast.error(t('invalidChatId'));
      return;
    }
    if (trimmed && !config.chat_ids.includes(trimmed)) {
      onChange({ ...config, chat_ids: [...config.chat_ids, trimmed] });
      setChatIdInput('');
    }
  };

  const handleRemoveChatId = (chatId: string) => {
    onChange({ ...config, chat_ids: config.chat_ids.filter(id => id !== chatId) });
  };

  const applyPendingChatId = () => {
    const trimmed = chatIdInput.trim();
    if (!trimmed) {
      return config;
    }
    if (!isValidChatId(trimmed)) {
      toast.error(t('invalidChatId'));
      return null;
    }
    if (config.chat_ids.includes(trimmed)) {
      setChatIdInput('');
      return config;
    }
    const next = { ...config, chat_ids: [...config.chat_ids, trimmed] };
    onChange(next);
    setChatIdInput('');
    return next;
  };

  const handleSave = () => {
    const nextConfig = applyPendingChatId();
    if (!nextConfig) {
      return;
    }
    const rawToken = normalizeToken(nextConfig.bot_token || '');
    const effectiveToken = (isBotMasked && !botTokenDraft) ? '***REDACTED***' : rawToken;
    if (
      nextConfig.enabled &&
      effectiveToken &&
      effectiveToken !== '***REDACTED***' &&
      !isValidBotToken(effectiveToken)
    ) {
      toast.error(t('invalidBotToken'));
      return;
    }
    if (nextConfig.enabled && nextConfig.chat_ids.some((chatId) => !isValidChatId(chatId))) {
      toast.error(t('invalidChatId'));
      return;
    }
    if (nextConfig.enabled && effectiveToken && effectiveToken !== '***REDACTED***') {
      if (!testSuccess || lastTestedToken !== effectiveToken) {
        toast.error(t('telegramTokenTestRequired'));
        return;
      }
    }
    onSave(nextConfig);
  };

  useEffect(() => {
    if (config.bot_token && !isBotMasked) {
      setBotTokenDraft(config.bot_token);
      setLastTestedToken(config.bot_token);
      setTestSuccess(true);
    }
  }, [config.bot_token, isBotMasked]);

  const handleTest = async () => {
    const nextConfig = applyPendingChatId();
    if (!nextConfig) {
      return;
    }
    const trimmedToken = normalizeToken(botTokenDraft);
    const usingSavedToken = !trimmedToken && isBotMasked;
    if (!trimmedToken && !usingSavedToken) {
      toast.error(t('invalidBotToken'));
      return;
    }
    if (trimmedToken && !isValidBotToken(trimmedToken)) {
      toast.error(t('invalidBotToken'));
      return;
    }
    if (nextConfig.chat_ids.length === 0) {
      toast.error(t('invalidChatId'));
      return;
    }
    setTesting(true);
    try {
      const payload = { chat_ids: nextConfig.chat_ids } as { chat_ids: string[]; bot_token?: string };
      if (trimmedToken) {
        payload.bot_token = trimmedToken;
      }
      await api.testTelegram(payload);
      setTestSuccess(true);
      if (trimmedToken) {
        setLastTestedToken(trimmedToken);
        onChange({ ...nextConfig, bot_token: trimmedToken });
        onSave({ ...nextConfig, bot_token: trimmedToken });
      }
      toast.success(t('telegramTestSuccess'));
    } catch (error) {
      toast.error(t('telegramTestFailed'));
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('telegramNotifications')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('telegramDesc')}
        </p>
      </div>

      <div className="p-4 bg-info/20 border border-info/40 rounded-lg mb-4">
        <p className="text-sm text-text">
          {t('telegramOptional')}
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="telegram-enabled"
            checked={config.enabled}
            onChange={(e) => onChange({ ...config, enabled: e.target.checked })}
            className="w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
          />
          <label htmlFor="telegram-enabled" className="text-sm font-medium text-text">
            {t('enableTelegramNotifications')}
          </label>
        </div>

        {config.enabled && (
          <>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-text">
                  {t('botToken')}
                </label>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${tokenStatusClass}`}>
                  {tokenStatusText}
                </span>
              </div>
              <div className="relative">
                <input
                  type={showBotToken ? 'text' : 'password'}
                  value={botTokenDraft || (isBotMasked ? maskedDisplay : '')}
                  onFocus={() => {
                    if (isBotMasked && !botTokenDraft) {
                      setBotTokenDraft('');
                    }
                  }}
                  onChange={(e) => {
                    if (isBotMasked && !botTokenDraft && e.target.value === maskedDisplay) {
                      return;
                    }
                    setBotTokenDraft(e.target.value);
                    setTestSuccess(false);
                    onChange({ ...config, bot_token: e.target.value });
                  }}
                  placeholder={isBotMasked ? t('botTokenSet') : '123456:ABC-DEF...'}
                  className="w-full px-3 py-2 pr-10 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
                />
                <button
                  type="button"
                  onClick={() => setShowBotToken(!showBotToken)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-text"
                >
                  {showBotToken ? <FiEyeOff size={18} /> : <FiEye size={18} />}
                </button>
              </div>
              <p className="text-xs text-muted mt-1">
                Get from @BotFather on Telegram
              </p>
              <p className="text-xs text-muted mt-1">
                {(isBotMasked || botTokenDraft) ? t('botTokenSet') : t('botTokenNotSet')}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('chatIDs')}
              </label>
              <div className="flex space-x-2 mb-2">
                <input
                  type="text"
                  value={chatIdInput}
                  onChange={(e) => setChatIdInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddChatId()}
                  placeholder="Enter chat ID and press Enter"
                  className="flex-1 px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
                />
                <button
                  onClick={handleAddChatId}
                  className="px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-opacity-80 transition-colors"
                >
                  Add
                </button>
              </div>
              {config.chat_ids.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {config.chat_ids.map((chatId) => (
                    <div
                      key={chatId}
                      className="flex items-center space-x-2 px-3 py-1 bg-surface2 border border-border rounded-lg"
                    >
                      <span className="text-sm text-text">{chatId}</span>
                      <button
                        onClick={() => handleRemoveChatId(chatId)}
                        className="text-error hover:text-opacity-80"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="send-images"
                checked={config.send_images}
                onChange={(e) => onChange({ ...config, send_images: e.target.checked })}
                className="w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
              />
          <label htmlFor="send-images" className="text-sm font-medium text-text">
            {t('sendImages')} (Collage)
          </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Snapshot Quality: {config.snapshot_quality}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={config.snapshot_quality}
                onChange={(e) => onChange({ ...config, snapshot_quality: parseInt(e.target.value) })}
                className="w-full"
              />
              <p className="text-xs text-muted mt-1">
                JPEG quality for snapshots (0-100)
              </p>
            </div>

            {/* TASK 14: Rate Limit */}
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Rate Limit (seconds)
              </label>
              <input
                type="number"
                min="0"
                max="300"
                value={config.rate_limit_seconds}
                onChange={(e) => onChange({ ...config, rate_limit_seconds: parseInt(e.target.value) || 10 })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <p className="text-xs text-muted mt-1">
                Minimum wait time between same event notifications
              </p>
            </div>

            {/* TASK 15: Video Speed */}
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Video Speed: {config.video_speed}x
              </label>
              <input
                type="range"
                min="1"
                max="10"
                step="0.5"
                value={config.video_speed}
                onChange={(e) => onChange({ ...config, video_speed: parseFloat(e.target.value) })}
                className="w-full h-2 bg-surface2 rounded-lg appearance-none cursor-pointer accent-accent"
              />
              <p className="text-xs text-muted mt-1">
                Timelapse speed multiplier
              </p>
            </div>

            {/* Event Types kaldırıldı - sadece person algılıyoruz */}
            <div className="bg-info/10 border border-info/40 rounded-lg p-4">
              <p className="text-info text-sm">
                ℹ️ Sadece <strong>Person</strong> algılaması yapılıyor. Vehicle, Animal algılaması yok.
              </p>
            </div>

            {/* TASK 17: Cooldown */}
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Cooldown (seconds)
              </label>
              <input
                type="number"
                min="0"
                max="600"
                value={config.cooldown_seconds}
                onChange={(e) => onChange({ ...config, cooldown_seconds: parseInt(e.target.value) || 30 })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <p className="text-xs text-muted mt-1">
                Minimum wait time between any notifications
              </p>
            </div>

            {/* TASK 18: Max Messages Per Minute */}
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Max Messages Per Minute
              </label>
              <input
                type="number"
                min="1"
                max="60"
                value={config.max_messages_per_min}
                onChange={(e) => onChange({ ...config, max_messages_per_min: parseInt(e.target.value) || 5 })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <p className="text-xs text-muted mt-1">
                Rate limiting to prevent spam
              </p>
            </div>

            <button
              onClick={handleTest}
              disabled={testing}
              className="w-full px-4 py-2 bg-surface2 border border-border text-text rounded-lg hover:bg-surface2/80 transition-colors disabled:opacity-50"
            >
              {testing ? t('loading') + '...' : t('telegramTestSample')}
            </button>
          </>
        )}
      </div>

      <button
        onClick={handleSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveTelegramSettings')}
      </button>
    </div>
  );
};
