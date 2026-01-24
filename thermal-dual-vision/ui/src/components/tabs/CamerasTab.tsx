/**
 * Cameras tab - Camera management and testing
 */
import React, { useState } from 'react';
import { CameraList } from '../CameraList';
import { CameraFormModal } from '../CameraFormModal';
import { testCamera } from '../../services/api';
import type { CameraTestRequest, CameraTestResponse } from '../../types/api';
import toast from 'react-hot-toast';

interface Camera {
  id: string
  name: string
  type: string
  enabled: boolean
  status: string
  rtsp_url_thermal?: string
  rtsp_url_color?: string
  detection_source: string
  stream_roles: string[]
}

export const CamerasTab: React.FC = () => {
  const [showModal, setShowModal] = useState(false);
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Camera test form (quick test without saving)
  const [cameraType, setCameraType] = useState<'color' | 'thermal' | 'dual'>('thermal');
  const [thermalUrl, setThermalUrl] = useState('');
  const [colorUrl, setColorUrl] = useState('');
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<CameraTestResponse | null>(null);

  const handleTest = async () => {
    const request: CameraTestRequest = {
      type: cameraType,
      rtsp_url_thermal: cameraType !== 'color' ? thermalUrl : undefined,
      rtsp_url_color: cameraType !== 'thermal' ? colorUrl : undefined,
    };

    if (cameraType === 'thermal' && !thermalUrl) {
      toast.error('Termal RTSP adresi gerekli');
      return;
    }
    if (cameraType === 'color' && !colorUrl) {
      toast.error('Renkli RTSP adresi gerekli');
      return;
    }
    if (cameraType === 'dual' && (!thermalUrl || !colorUrl)) {
      toast.error('İkili kamera için her iki RTSP adresi gerekli');
      return;
    }

    setTesting(true);
    setResult(null);

    try {
      const response = await testCamera(request);
      setResult(response);
      if (response.success) {
        toast.success(`Kamera testi başarılı! Gecikme: ${response.latency_ms}ms`);
      } else {
        toast.error(response.error_reason || 'Kamera testi başarısız');
      }
    } catch (error) {
      toast.error('Kamera bağlantısı test edilemedi');
    } finally {
      setTesting(false);
    }
  };

  const handleAdd = () => {
    setEditingCamera(null);
    setShowModal(true);
  };

  const handleEdit = (camera: Camera) => {
    setEditingCamera(camera);
    setShowModal(true);
  };

  const handleSave = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="space-y-8">
      {/* Camera List */}
      <div key={refreshKey}>
        <CameraList 
          onAdd={handleAdd}
          onEdit={handleEdit}
          onRefresh={() => setRefreshKey(prev => prev + 1)}
        />
      </div>

      {/* Divider */}
      <div className="border-t border-border" />

      {/* Quick Test Form */}
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Hızlı Bağlantı Testi</h3>
        <p className="text-sm text-muted mb-6">
          Kamera kaydetmeden önce RTSP bağlantısını test edin
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              Kamera Tipi
            </label>
            <select
              value={cameraType}
              onChange={(e) => setCameraType(e.target.value as typeof cameraType)}
              className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="thermal">Termal</option>
              <option value="color">Renkli</option>
              <option value="dual">İkili (Termal + Renkli)</option>
            </select>
          </div>

          {(cameraType === 'thermal' || cameraType === 'dual') && (
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Termal RTSP Adresi
              </label>
              <input
                type="text"
                value={thermalUrl}
                onChange={(e) => setThermalUrl(e.target.value)}
                placeholder="rtsp://admin:password@192.168.1.100:554/Streaming/Channels/201"
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent font-mono text-sm"
              />
            </div>
          )}

          {(cameraType === 'color' || cameraType === 'dual') && (
            <div>
              <label className="block text-sm font-medium text-text mb-2">
                Renkli RTSP Adresi
              </label>
              <input
                type="text"
                value={colorUrl}
                onChange={(e) => setColorUrl(e.target.value)}
                placeholder="rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101"
                className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent font-mono text-sm"
              />
            </div>
          )}

          <button
            onClick={handleTest}
            disabled={testing}
            className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {testing ? 'Test Ediliyor...' : 'Bağlantıyı Test Et'}
          </button>
        </div>

        {result && result.success && result.snapshot_base64 && (
          <div className="mt-6">
            <h4 className="text-sm font-medium text-text mb-2">Görüntü</h4>
            <div className="border border-border rounded-lg overflow-hidden">
              <img
                src={result.snapshot_base64}
                alt="Kamera görüntüsü"
                className="w-full h-auto"
              />
            </div>
            {result.latency_ms !== undefined && (
              <p className="text-sm text-muted mt-2">
                Gecikme: {result.latency_ms}ms
              </p>
            )}
          </div>
        )}

        {result && !result.success && (
          <div className="mt-6 p-4 bg-error bg-opacity-10 border border-error rounded-lg">
            <p className="text-sm text-error">{result.error_reason}</p>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <CameraFormModal
          camera={editingCamera}
          onClose={() => setShowModal(false)}
          onSave={handleSave}
        />
      )}
    </div>
  );
};
