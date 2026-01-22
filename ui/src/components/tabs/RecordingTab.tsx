/**
 * Recording tab - Recording and retention settings
 */
import React from 'react';
import type { RecordConfig } from '../../types/api';

interface RecordingTabProps {
  config: RecordConfig;
  onChange: (config: RecordConfig) => void;
  onSave: () => void;
}

export const RecordingTab: React.FC<RecordingTabProps> = ({ config, onChange, onSave }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Kayıt Ayarları</h3>
        <p className="text-sm text-muted mb-6">
          Event bazlı kayıt ve saklama politikası ayarları
        </p>
      </div>

      {/* Important Notice */}
      <div className="bg-surface2 border-l-4 border-warning p-4 rounded-lg">
        <h3 className="font-bold text-warning mb-2">⚠️ ÖNEMLİ: İki Farklı Kayıt Türü</h3>
        <div className="space-y-3 text-sm">
          <div>
            <strong className="text-text">1. Sürekli Kayıt (7/24):</strong>
            <p className="text-muted">Her şeyi kaydeder (person olsun olmasın)</p>
            <p className="text-error">❌ KAPALI tutun (NVR zaten yapıyor!)</p>
          </div>
          <div>
            <strong className="text-text">2. Hareket Kayıtları (Event):</strong>
            <p className="text-muted">Sadece person algılandığında (collage/GIF/MP4)</p>
            <p className="text-success">✅ HER ZAMAN AÇIK (otomatik)</p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="recording-enabled"
            checked={config.enabled}
            onChange={(e) => onChange({ ...config, enabled: e.target.checked })}
            className="w-4 h-4 text-accent bg-surface2 border-border rounded focus:ring-accent"
          />
          <label htmlFor="recording-enabled" className="text-sm font-medium text-text">
            Sürekli Kayıt (7/24) - Önerilmez
          </label>
        </div>

        {config.enabled && (
          <>
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Saklama Süresi (Gün)
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={config.retention_days}
                onChange={(e) => onChange({ ...config, retention_days: parseInt(e.target.value) || 7 })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <p className="text-xs text-muted mt-1">
                Kayıtlar kaç gün saklanacak
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Disk Limiti: {config.disk_limit_percent}%
              </label>
              <input
                type="range"
                min="50"
                max="95"
                step="5"
                value={config.disk_limit_percent}
                onChange={(e) => onChange({ ...config, disk_limit_percent: parseInt(e.target.value) })}
                className="w-full h-2 bg-surface2 rounded-lg appearance-none cursor-pointer accent-accent"
              />
              <p className="text-xs text-muted mt-1">
                Maksimum disk kullanımı yüzdesi (50-95%)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Segment Uzunluğu (saniye)
              </label>
              <input
                type="number"
                min="5"
                max="60"
                value={config.record_segments_seconds}
                onChange={(e) => onChange({ ...config, record_segments_seconds: parseInt(e.target.value) || 10 })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <p className="text-xs text-muted mt-1">
                Her kayıt segmentinin uzunluğu
              </p>
            </div>

            {/* TASK 19: Cleanup Policy */}
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Cleanup Policy
              </label>
              <select
                value={config.cleanup_policy}
                onChange={(e) => onChange({ ...config, cleanup_policy: e.target.value as 'oldest_first' | 'lowest_confidence' })}
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="oldest_first">Delete Oldest First</option>
                <option value="lowest_confidence">Delete Lowest Confidence First</option>
              </select>
              <p className="text-xs text-muted mt-1">
                Which recordings to delete when disk is full
              </p>
            </div>

            {/* TASK 20: Delete Order */}
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Delete Order (drag to reorder)
              </label>
              <div className="space-y-2">
                {config.delete_order.map((type, index) => (
                  <div key={type} className="flex items-center gap-2 p-2 bg-surface2 rounded">
                    <span className="text-muted">{index + 1}.</span>
                    <span className="flex-1 capitalize text-text">{type}</span>
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        if (index === 0) return
                        const next = [...config.delete_order]
                        ;[next[index], next[index - 1]] = [next[index - 1], next[index]]
                        onChange({ ...config, delete_order: next })
                      }}
                      disabled={index === 0}
                      className="px-2 py-1 bg-surface1 border border-border text-text rounded hover:bg-surface1/80 disabled:opacity-30 text-sm"
                    >
                      ↑
                    </button>
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        if (index === config.delete_order.length - 1) return
                        const next = [...config.delete_order]
                        ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
                        onChange({ ...config, delete_order: next })
                      }}
                      disabled={index === config.delete_order.length - 1}
                      className="px-2 py-1 bg-surface1 border border-border text-text rounded hover:bg-surface1/80 disabled:opacity-30 text-sm"
                    >
                      ↓
                    </button>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted mt-1">
                Order in which media types are deleted (first = deleted first)
              </p>
            </div>
          </>
        )}
      </div>

      <button
        onClick={onSave}
        className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 transition-colors"
      >
        Kayıt Ayarlarını Kaydet
      </button>
    </div>
  );
};
