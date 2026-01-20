/**
 * Detection tab - YOLOv8 detection settings
 */
import React from 'react';
import type { DetectionConfig } from '../../types/api';

interface DetectionTabProps {
  config: DetectionConfig;
  onChange: (config: DetectionConfig) => void;
  onSave: () => void;
}

export const DetectionTab: React.FC<DetectionTabProps> = ({ config, onChange, onSave }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Detection Settings</h3>
        <p className="text-sm text-muted mb-6">
          Configure YOLOv8 person detection model and inference parameters
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Model
          </label>
          <select
            value={config.model}
            onChange={(e) => onChange({ ...config, model: e.target.value as DetectionConfig['model'] })}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="yolov8n-person">YOLOv8n-person (Fast, Edge devices)</option>
            <option value="yolov8s-person">YOLOv8s-person (Accurate, Server)</option>
          </select>
          <p className="text-xs text-muted mt-1">
            n = faster, s = more accurate
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Confidence Threshold: {config.confidence_threshold.toFixed(2)}
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
            <span>0.0 (More detections)</span>
            <span>1.0 (Fewer, higher confidence)</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Inference FPS
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
            How many frames per second to process (1-30)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            NMS IoU Threshold: {config.nms_iou_threshold.toFixed(2)}
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
            Non-Maximum Suppression threshold (typically 0.45)
          </p>
        </div>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        Save Detection Settings
      </button>
    </div>
  );
};
