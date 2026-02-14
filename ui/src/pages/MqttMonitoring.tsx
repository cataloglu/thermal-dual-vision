import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { LoadingState } from '../components/LoadingState';

interface MqttStatus {
  enabled: boolean;
  connected: boolean;
  broker: string;
  topic_prefix: string;
  availability_topic: string;
  connected_at: string | null;
  active_topics: string[];
  publish_count: number;
  last_messages: Record<string, { payload: string; timestamp: string }>;
  last_error: string | null;
}

export function MqttMonitoring() {
  const { t } = useTranslation();
  const [mqttStatus, setMqttStatus] = useState<MqttStatus | null>(null);
  const [cameras, setCameras] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusData, camerasData] = await Promise.all([
          api.getMqttStatus(),
          api.getCameras(),
        ]);
        setMqttStatus(statusData);
        setCameras(camerasData.cameras || []);
      } catch (error) {
        console.error('Failed to fetch MQTT data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <LoadingState />;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text mb-2">📡 MQTT Monitoring</h1>
        <p className="text-muted">Home Assistant MQTT entegrasyon durumu ve sensor'lar</p>
      </div>

      {!mqttStatus?.enabled ? (
        <div className="bg-surface1 border border-border rounded-lg p-12 text-center">
          <p className="text-muted mb-4">MQTT devre dışı</p>
          <p className="text-sm text-muted">Settings → MQTT'den aktif edin</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Connection Status */}
          <div className="bg-card p-6 rounded-lg border border-border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-foreground">Bağlantı Durumu</h3>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                mqttStatus.connected 
                  ? 'bg-green-500/20 text-green-500'
                  : 'bg-red-500/20 text-red-500'
              }`}>
                {mqttStatus.connected ? '🟢 Bağlı' : '🔴 Bağlı Değil'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 bg-background rounded border border-border">
                <div className="text-xs text-muted-foreground mb-1">Broker</div>
                <div className="text-sm font-mono text-foreground">{mqttStatus.broker}</div>
              </div>
              <div className="p-3 bg-background rounded border border-border">
                <div className="text-xs text-muted-foreground mb-1">Topic Prefix</div>
                <div className="text-sm font-mono text-foreground">{mqttStatus.topic_prefix}</div>
              </div>
              {mqttStatus.connected_at && (
                <div className="p-3 bg-background rounded border border-border">
                  <div className="text-xs text-muted-foreground mb-1">Bağlandı</div>
                  <div className="text-sm text-foreground">
                    {new Date(mqttStatus.connected_at).toLocaleString('tr-TR')}
                  </div>
                </div>
              )}
              <div className="p-3 bg-background rounded border border-border">
                <div className="text-xs text-muted-foreground mb-1">Gönderilen Mesaj</div>
                <div className="text-sm font-semibold text-foreground">{mqttStatus.publish_count}</div>
              </div>
            </div>
          </div>

          {/* Home Assistant Sensors */}
          <div className="bg-card p-6 rounded-lg border border-border">
            <h3 className="text-lg font-medium text-foreground mb-4">
              🏠 Home Assistant Sensor'ları
            </h3>
            <div className="space-y-3">
              {cameras.length > 0 ? (
                cameras.map((cam: any) => (
                  <div key={cam.id} className="p-4 bg-background rounded-lg border-l-4 border-accent">
                    <div className="font-semibold text-foreground mb-2">{cam.name}</div>
                    <div className="space-y-1 text-xs font-mono text-muted-foreground">
                      <div>🔴 binary_sensor.{cam.name.toLowerCase().replace(/\s+/g, '_')}_person_detected</div>
                      <div>🔢 sensor.{cam.name.toLowerCase().replace(/\s+/g, '_')}_person_count</div>
                      <div>📝 sensor.{cam.name.toLowerCase().replace(/\s+/g, '_')}_last_event</div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-muted-foreground text-center py-4">Kamera yok</div>
              )}
            </div>
            <div className="mt-4 p-3 bg-info/10 border border-info rounded-lg text-xs text-info">
              💡 Bu sensor'ları Home Assistant → Settings → Devices & Services → MQTT'de bulabilirsiniz
            </div>
          </div>

          {/* Active Topics */}
          <div className="bg-card p-6 rounded-lg border border-border">
            <h3 className="text-lg font-medium text-foreground mb-4">
              📤 Aktif Topic'ler ({mqttStatus.active_topics.length})
            </h3>
            <div className="max-h-64 overflow-y-auto space-y-1">
              {mqttStatus.active_topics.length > 0 ? (
                mqttStatus.active_topics.map((topic) => (
                  <div key={topic} className="p-2 bg-background rounded text-xs font-mono text-muted-foreground">
                    📤 {topic}
                  </div>
                ))
              ) : (
                <div className="text-muted-foreground text-center py-4">Henüz topic yok</div>
              )}
            </div>
          </div>

          {/* Recent Messages */}
          <div className="bg-card p-6 rounded-lg border border-border">
            <h3 className="text-lg font-medium text-foreground mb-4">
              📨 Son Mesajlar (Son 10)
            </h3>
            <div className="max-h-96 overflow-y-auto space-y-2">
              {Object.entries(mqttStatus.last_messages).length > 0 ? (
                Object.entries(mqttStatus.last_messages).map(([topic, msg]) => (
                  <div key={topic} className="p-3 bg-background rounded-lg border border-border">
                    <div className="flex items-start justify-between mb-2">
                      <div className="text-xs font-mono text-foreground font-semibold truncate flex-1">
                        {topic}
                      </div>
                      <div className="text-xs text-muted-foreground ml-2 whitespace-nowrap">
                        {new Date(msg.timestamp).toLocaleTimeString('tr-TR')}
                      </div>
                    </div>
                    <div className="text-xs font-mono text-muted-foreground bg-surface1 p-2 rounded overflow-x-auto">
                      {typeof msg.payload === 'string' 
                        ? msg.payload.substring(0, 200)
                        : JSON.stringify(msg.payload).substring(0, 200)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-muted-foreground text-center py-4">Henüz mesaj yok</div>
              )}
            </div>
          </div>

          {/* Error Display */}
          {mqttStatus.last_error && (
            <div className="bg-card p-6 rounded-lg border border-error">
              <div className="text-sm font-semibold text-error mb-2">Son Hata</div>
              <div className="text-xs text-error font-mono bg-error/10 p-3 rounded">
                {mqttStatus.last_error}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
