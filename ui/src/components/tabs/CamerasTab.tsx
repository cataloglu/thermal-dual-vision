/**
 * Cameras tab - Camera test functionality
 */
import React, { useState } from 'react';
import { testCamera } from '../../services/api';
import type { CameraTestRequest, CameraTestResponse } from '../../types/api';
import toast from 'react-hot-toast';

export const CamerasTab: React.FC = () => {
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
      toast.error('Thermal RTSP URL is required');
      return;
    }
    if (cameraType === 'color' && !colorUrl) {
      toast.error('Color RTSP URL is required');
      return;
    }
    if (cameraType === 'dual' && (!thermalUrl || !colorUrl)) {
      toast.error('Both RTSP URLs are required for dual camera');
      return;
    }

    setTesting(true);
    setResult(null);

    try {
      const response = await testCamera(request);
      setResult(response);
      if (response.success) {
        toast.success(`Camera test successful! Latency: ${response.latency_ms}ms`);
      } else {
        toast.error(response.error_reason || 'Camera test failed');
      }
    } catch (error) {
      toast.error('Failed to test camera connection');
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-text mb-4">Camera Test</h3>
        <p className="text-sm text-muted mb-6">
          Test RTSP camera connection and capture snapshot
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Camera Type
          </label>
          <select
            value={cameraType}
            onChange={(e) => setCameraType(e.target.value as typeof cameraType)}
            className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="thermal">Thermal</option>
            <option value="color">Color</option>
            <option value="dual">Dual (Thermal + Color)</option>
          </select>
        </div>

        {(cameraType === 'thermal' || cameraType === 'dual') && (
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              Thermal RTSP URL
            </label>
            <input
              type="text"
              value={thermalUrl}
              onChange={(e) => setThermalUrl(e.target.value)}
              placeholder="rtsp://admin:password@192.168.1.100:554/Streaming/Channels/201"
              className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>
        )}

        {(cameraType === 'color' || cameraType === 'dual') && (
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              Color RTSP URL
            </label>
            <input
              type="text"
              value={colorUrl}
              onChange={(e) => setColorUrl(e.target.value)}
              placeholder="rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101"
              className="w-full px-3 py-2 bg-surface2 border border-border rounded-lg text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-accent"
            />
          </div>
        )}

        <button
          onClick={handleTest}
          disabled={testing}
          className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {testing ? 'Testing...' : 'Test Connection'}
        </button>
      </div>

      {result && result.success && result.snapshot_base64 && (
        <div className="mt-6">
          <h4 className="text-sm font-medium text-text mb-2">Snapshot</h4>
          <div className="border border-border rounded-lg overflow-hidden">
            <img
              src={result.snapshot_base64}
              alt="Camera snapshot"
              className="w-full h-auto"
            />
          </div>
          {result.latency_ms !== undefined && (
            <p className="text-sm text-muted mt-2">
              Latency: {result.latency_ms}ms
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
  );
};
