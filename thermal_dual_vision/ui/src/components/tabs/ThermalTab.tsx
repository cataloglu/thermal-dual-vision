/**
 * Thermal tab - Thermal image enhancement settings
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import type { ThermalConfig } from '../../types/api';

interface ThermalTabProps {
  config: ThermalConfig;
  onChange: (config: ThermalConfig) => void;
  onSave: () => void;
}

export const ThermalTab: React.FC<ThermalTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const enhancementStatus = config.enable_enhancement ? t('enabled') : t('disabled');
  const methodLabel =
    config.enhancement_method === 'histogram'
      ? t('histogram')
      : config.enhancement_method === 'none'
        ? t('none')
        : 'CLAHE';
  
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('thermalEnhancement')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('thermalDesc')}
        </p>
      </div>

      <div className="bg-surface2 border-l-4 border-info p-4 rounded-lg">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h4 className="font-semibold text-text">{t('perfShortcutTitle')}</h4>
            <p className="text-xs text-muted mt-1">{t('perfShortcutDesc')}</p>
          </div>
          <button
            onClick={() => navigate('/settings?tab=performance')}
            className="px-3 py-2 bg-surface1 border border-border text-text rounded-lg hover:bg-surface1/80 transition-colors text-sm"
          >
            {t('perfShortcutButton')}
          </button>
        </div>
        <div className="mt-3 text-xs text-muted space-y-1">
          <div>{t('thermalSummaryStatus', { value: enhancementStatus })}</div>
          <div>{t('thermalSummaryMethod', { value: methodLabel })}</div>
        </div>
      </div>

      <div className="space-y-4">
        {!config.enable_enhancement && (
          <p className="text-xs text-muted">{t('thermalAdvancedHint')}</p>
        )}

        {config.enable_enhancement && (
          <>
            {config.enhancement_method === 'clahe' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-text mb-2">
                    {t('claheClipLimit')}: {config.clahe_clip_limit.toFixed(1)}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    step="0.5"
                    value={config.clahe_clip_limit}
                    onChange={(e) => onChange({ ...config, clahe_clip_limit: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text mb-2">
                    {t('claheGridSize')}
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <input
                      type="number"
                      min="4"
                      max="16"
                      value={config.clahe_tile_size[0]}
                      onChange={(e) => onChange({ 
                        ...config, 
                        clahe_tile_size: [parseInt(e.target.value) || 8, config.clahe_tile_size[1]] 
                      })}
                      className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
                    />
                    <input
                      type="number"
                      min="4"
                      max="16"
                      value={config.clahe_tile_size[1]}
                      onChange={(e) => onChange({ 
                        ...config, 
                        clahe_tile_size: [config.clahe_tile_size[0], parseInt(e.target.value) || 8] 
                      })}
                      className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                {t('gaussianBlur')}
              </label>
              <div className="grid grid-cols-2 gap-4">
                <input
                  type="number"
                  min="1"
                  max="9"
                  step="2"
                  value={config.gaussian_blur_kernel[0]}
                  onChange={(e) => onChange({ 
                    ...config, 
                    gaussian_blur_kernel: [parseInt(e.target.value) || 3, config.gaussian_blur_kernel[1]] 
                  })}
                  className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
                />
                <input
                  type="number"
                  min="1"
                  max="9"
                  step="2"
                  value={config.gaussian_blur_kernel[1]}
                  onChange={(e) => onChange({ 
                    ...config, 
                    gaussian_blur_kernel: [config.gaussian_blur_kernel[0], parseInt(e.target.value) || 3] 
                  })}
                  className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            </div>
          </>
        )}
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveThermalSettings')}
      </button>
    </div>
  );
};
