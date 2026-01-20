/**
 * Thermal tab - Thermal image enhancement settings
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { ThermalConfig } from '../../types/api';

interface ThermalTabProps {
  config: ThermalConfig;
  onChange: (config: ThermalConfig) => void;
  onSave: () => void;
}

export const ThermalTab: React.FC<ThermalTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('thermalEnhancement')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('thermalDesc')}
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="enable-enhancement"
            checked={config.enable_enhancement}
            onChange={(e) => onChange({ ...config, enable_enhancement: e.target.checked })}
            className="w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
          />
          <label htmlFor="enable-enhancement" className="text-sm font-medium text-text">
            {t('enableThermalEnhancement')}
          </label>
        </div>

        {config.enable_enhancement && (
          <>
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Enhancement Method
              </label>
              <select
                value={config.enhancement_method}
                onChange={(e) => onChange({ ...config, enhancement_method: e.target.value as ThermalConfig['enhancement_method'] })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="clahe">CLAHE (Recommended)</option>
                <option value="histogram">Histogram Equalization</option>
                <option value="none">None</option>
              </select>
              <p className="text-xs text-muted mt-1">
                CLAHE provides best results for thermal images
              </p>
            </div>

            {config.enhancement_method === 'clahe' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-text mb-2">
                    CLAHE Clip Limit: {config.clahe_clip_limit.toFixed(1)}
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
                  <p className="text-xs text-muted mt-1">
                    Controls contrast enhancement strength (default: 2.0)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text mb-2">
                    CLAHE Tile Size
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
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
                        placeholder="Width"
                      />
                    </div>
                    <div>
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
                        placeholder="Height"
                      />
                    </div>
                  </div>
                  <p className="text-xs text-muted mt-1">
                    Grid size for local histogram equalization (default: 8x8)
                  </p>
                </div>
              </>
            )}
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
