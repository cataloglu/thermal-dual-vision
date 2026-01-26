/**
 * Detection tab - YOLOv8 detection settings
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import type { DetectionConfig } from '../../types/api';

interface DetectionTabProps {
  config: DetectionConfig;
  onChange: (config: DetectionConfig) => void;
  onSave: () => void;
}

export const DetectionTab: React.FC<DetectionTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('detectionSettingsTitle')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('detectionSettingsDesc')}
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
          <div>{t('perfSummaryModel', { value: config.model })}</div>
          <div>{t('perfSummaryFps', { value: config.inference_fps })}</div>
          <div>
            {t('perfSummaryResolution', {
              width: config.inference_resolution[0],
              height: config.inference_resolution[1],
            })}
          </div>
          <div>{t('perfSummaryConfidence', { value: config.confidence_threshold.toFixed(2) })}</div>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('detectionNmsLabel', { value: config.nms_iou_threshold.toFixed(2) })}
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={config.nms_iou_threshold}
            onChange={(e) => onChange({ ...config, nms_iou_threshold: parseFloat(e.target.value) })}
            className="w-full"
          />
          <p className="text-xs text-muted mt-1">
            {t('detectionNmsHint')}
          </p>
        </div>

        {/* Aspect Ratio - TASK 12 */}
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('detectionAspectRatioMinLabel', { value: config.aspect_ratio_min?.toFixed(2) || 0.3 })}
          </label>
          <input
            type="range"
            min="0.05"
            max="1.0"
            step="0.05"
            value={config.aspect_ratio_min || 0.3}
            onChange={(e) => onChange({ ...config, aspect_ratio_min: parseFloat(e.target.value) })}
            className="w-full"
          />
          <p className="text-xs text-muted mt-1">
            {t('detectionAspectRatioMinHint')}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('detectionAspectRatioMaxLabel', { value: config.aspect_ratio_max?.toFixed(2) || 3.0 })}
          </label>
          <input
            type="range"
            min="1.0"
            max="5.0"
            step="0.1"
            value={config.aspect_ratio_max || 3.0}
            onChange={(e) => onChange({ ...config, aspect_ratio_max: parseFloat(e.target.value) })}
            className="w-full"
          />
          <p className="text-xs text-muted mt-1">
            {t('detectionAspectRatioMaxHint')}
          </p>
        </div>

        {/* Enable Tracking - TASK 13 */}
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="enable-tracking"
            checked={config.enable_tracking}
            onChange={(e) => onChange({ ...config, enable_tracking: e.target.checked })}
            className="w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
          />
          <label htmlFor="enable-tracking" className="text-sm font-medium text-text">
            {t('detectionEnableTracking')}
          </label>
        </div>
      </div>

      {/* Model Comparison Info */}
      <div className="bg-surface2 border-l-4 border-info p-4 rounded-lg">
        <h4 className="font-semibold text-text mb-2">📊 {t('detectionModelComparisonTitle')}</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted">YOLOv8n:</span>
            <span className="text-text">{t('detectionModelCompareYolov8n')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">YOLOv8s:</span>
            <span className="text-text">{t('detectionModelCompareYolov8s')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">YOLOv9t:</span>
            <span className="text-text">{t('detectionModelCompareYolov9t')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">YOLOv9s:</span>
            <span className="text-text">{t('detectionModelCompareYolov9s')}</span>
          </div>
        </div>
        <p className="text-xs text-muted mt-3">
          💡 {t('detectionModelComparisonHint')}
        </p>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('detectionSaveSettings')}
      </button>
    </div>
  );
};
