/**
 * Detection tab - YOLOv8 detection settings
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import type { DetectionConfig } from '../../types/api';

interface DetectionTabProps {
  config: DetectionConfig;
  onChange: (config: DetectionConfig) => void;
  onSave: () => void;
}

export const DetectionTab: React.FC<DetectionTabProps> = ({ config, onChange, onSave }) => {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">{t('detectionSettings')}</h3>
        <p className="text-sm text-muted mb-6">
          {t('detectionDesc')}
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('model')}
          </label>
          <select
            value={config.model}
            onChange={(e) => onChange({ ...config, model: e.target.value as DetectionConfig['model'] })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="yolov8n-person">YOLOv8n-person ({t('yolo8nDesc')})</option>
            <option value="yolov8s-person">YOLOv8s-person ({t('yolo8sDesc')})</option>
            <option value="yolov9t">YOLOv9t ({t('yolo9tDesc')})</option>
            <option value="yolov9s">YOLOv9s ({t('yolo9sDesc')})</option>
          </select>
          <p className="text-xs text-muted mt-1">
            {t('modelHintThermal')}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('confidenceThreshold')}: {config.confidence_threshold.toFixed(2)}
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={config.confidence_threshold}
            onChange={(e) => onChange({ ...config, confidence_threshold: parseFloat(e.target.value) })}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted mt-1">
            <span>0.0 ({t('moreDetections')})</span>
            <span>1.0 ({t('fewerHigherConfidence')})</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('inferenceFPS')}
          </label>
          <input
            type="number"
            min="1"
            max="30"
            value={config.inference_fps}
            onChange={(e) => onChange({ ...config, inference_fps: parseInt(e.target.value) || 1 })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <p className="text-xs text-muted mt-1">
            {t('framesPerSecond')}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('nmsThreshold')}: {config.nms_iou_threshold.toFixed(2)}
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
            {t('nmsThresholdDesc')}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('inferenceResolution')}
          </label>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-muted mb-1">Width</label>
              <input
                type="number"
                min="320"
                max="1920"
                step="32"
                value={config.inference_resolution[0]}
                onChange={(e) => onChange({ 
                  ...config, 
                  inference_resolution: [parseInt(e.target.value) || 640, config.inference_resolution[1]] 
                })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">Height</label>
              <input
                type="number"
                min="320"
                max="1920"
                step="32"
                value={config.inference_resolution[1]}
                onChange={(e) => onChange({ 
                  ...config, 
                  inference_resolution: [config.inference_resolution[0], parseInt(e.target.value) || 640] 
                })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>
          </div>
          <p className="text-xs text-muted mt-1">
            {t('inferenceResolutionDesc')}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('aspectRatioMin')}: {config.aspect_ratio_min?.toFixed(2) || 0.3}
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
            {t('aspectRatioMinDesc')}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            {t('aspectRatioMax')}: {config.aspect_ratio_max?.toFixed(2) || 3.0}
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
            {t('aspectRatioMaxDesc')}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="enable-tracking"
            checked={config.enable_tracking}
            onChange={(e) => onChange({ ...config, enable_tracking: e.target.checked })}
            className="w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
          />
          <label htmlFor="enable-tracking" className="text-sm font-medium text-text">
            {t('enableTracking')}
          </label>
        </div>
      </div>

      <div className="bg-surface2 border-l-4 border-info p-4 rounded-lg">
        <h4 className="font-semibold text-text mb-2">📊 {t('modelComparison')}</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted">YOLOv8n:</span>
            <span className="text-text">⚡⚡⚡ {t('simple').split(',')[0]}, ⭐⭐⭐</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">YOLOv8s:</span>
            <span className="text-text">⚡⚡, ⭐⭐⭐⭐</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">YOLOv9t:</span>
            <span className="text-text">⚡⚡, ⭐⭐⭐⭐ 🌡️ {t('thermal')}!</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">YOLOv9s:</span>
            <span className="text-text">⚡, ⭐⭐⭐⭐⭐</span>
          </div>
        </div>
        <p className="text-xs text-muted mt-3">
          💡 {t('modelHintThermal')}
        </p>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        {t('saveDetectionSettings')}
      </button>
    </div>
  );
};
