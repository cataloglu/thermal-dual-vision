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
        <h3 className="text-lg font-medium text-text mb-4">Algılama Ayarları</h3>
        <p className="text-sm text-muted mb-6">
          YOLOv8 kişi algılama modeli ve çıkarım parametrelerini yapılandırın
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
            <option value="yolov8n-person">YOLOv8n-person (Hızlı, 5+ kamera)</option>
            <option value="yolov8s-person">YOLOv8s-person (Doğru, 1-4 kamera)</option>
            <option value="yolov9t">YOLOv9t (Thermal optimize, önerilen)</option>
            <option value="yolov9s">YOLOv9s (En doğru, 1-3 kamera)</option>
          </select>
          <p className="text-xs text-muted mt-1">
            YOLOv9 thermal kameralar için optimize edilmiştir (PGI teknolojisi)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Güven Eşiği: {config.confidence_threshold.toFixed(2)}
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
            <span>0.0 (Daha fazla algılama)</span>
            <span>1.0 (Daha az, yüksek güven)</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Çıkarım FPS
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
            Saniyede kaç kare işlenecek (1-30)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-text mb-2">
            NMS IoU Eşiği: {config.nms_iou_threshold.toFixed(2)}
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
            Non-Maximum Suppression eşiği (genellikle 0.45)
          </p>
        </div>
      </div>

      {/* Model Comparison Info */}
      <div className="bg-surface2 border-l-4 border-info p-4 rounded-lg">
        <h4 className="font-semibold text-text mb-2">📊 Model Karşılaştırma</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted">YOLOv8n:</span>
            <span className="text-text">⚡⚡⚡ Hızlı, ⭐⭐⭐ İyi</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">YOLOv8s:</span>
            <span className="text-text">⚡⚡ Orta, ⭐⭐⭐⭐ Yüksek</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">YOLOv9t:</span>
            <span className="text-text">⚡⚡ Orta, ⭐⭐⭐⭐ Yüksek 🌡️ Thermal!</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">YOLOv9s:</span>
            <span className="text-text">⚡ Yavaş, ⭐⭐⭐⭐⭐ En İyi</span>
          </div>
        </div>
        <p className="text-xs text-muted mt-3">
          💡 Thermal kameralar için YOLOv9t önerilir (bilgi kaybı önler)
        </p>
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        Algılama Ayarlarını Kaydet
      </button>
    </div>
  );
};
