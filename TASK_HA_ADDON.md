# 🏠 GÖREV: Home Assistant Entegrasyonu ve Add-on Yapısı

Bu belge, "Thermal Dual Vision" projesinin Home Assistant (HA) ekosistemine tam entegrasyonu ve HA OS üzerinde "Add-on" olarak çalışabilmesi için gereken teknik adımları içerir.

---

## 🎯 HEDEFLER
1.  **MQTT Entegrasyonu:** Olayların (insan tespiti, AI özeti) HA'ya iletilmesi.
2.  **HA Discovery:** Kameraların ve sensörlerin HA tarafında otomatik oluşması.
3.  **Add-on Uyumluluğu:** Projenin HA Supervisor altında tek tıkla kurulabilir hale gelmesi.

---

## 🚀 GÖREV 1: Backend - MQTT Servisi

**Eksik:** Kodda `mqtt` servisi yok.
**Yapılacak:** `paho-mqtt` kütüphanesi kullanılarak bir servis yazılmalı.

### 1.1. Gereksinimler
*   `requirements.txt` dosyasına `paho-mqtt>=1.6.1` ekle.
*   `app/models/config.py` içine `MqttConfig` modeli ekle:
    ```python
    class MqttConfig(BaseModel):
        enabled: bool = False
        host: str = "core-mosquitto"  # HA default host
        port: int = 1883
        username: Optional[str] = None
        password: Optional[str] = None
        topic_prefix: str = "thermal_vision"
    ```

### 1.2. Servis İmplementasyonu (`app/services/mqtt.py`)
*   **Bağlantı:** Thread-safe client oluştur. Koptuğunda otomatik reconnect yapmalı.
*   **Discovery:** HA'nın `homeassistant/binary_sensor/.../config` topic'lerine JSON payload basmalı.
    *   **Binary Sensor:** Hareket algılandı mı?
    *   **Sensor:** Son AI özeti.
    *   **Switch:** Algılama açık/kapalı.
*   **Event Push:** `DetectorWorker` ve `AIService` içinden `mqtt_service.publish()` çağrılmalı.

---

## 🚀 GÖREV 2: HA Add-on Konfigürasyonu

Home Assistant'ın bu projeyi "Add-on" olarak tanıması için kök dizinde `ha-addon/` klasörü oluşturulmalı.

### 2.1. `ha-addon/config.yaml`
```yaml
name: "Thermal Dual Vision"
version: "2.1.0"
slug: "thermal_dual_vision"
description: "AI supported thermal & color person detection system"
url: "https://github.com/..."
arch:
  - aarch64
  - amd64
startup: application
boot: auto
map:
  - "config:rw"
  - "media:rw"
ports:
  8000/tcp: 8000
  5173/tcp: 5173
  1984/tcp: 1984
options:
  log_level: info
schema:
  log_level: str
```

### 2.2. `ha-addon/Dockerfile`
*   Mevcut `Dockerfile.api` ve `Dockerfile.ui` birleştirilmeli veya s6-overlay kullanılarak tek container içinde (Multi-process) çalıştırılmalı.
*   HA Add-on'ları genelde tek container çalışır.
*   **Öneri:** `nginx` ile frontend ve backend'i tek portta sunan, `supervisord` ile tüm processleri (api, worker, go2rtc) yöneten bir Dockerfile hazırla.

### 2.3. `ha-addon/run.sh`
*   Container başladığında:
    1.  HA options'larını (`options.json`) okuyup uygulamanın `config.json` dosyasına yazan bir script.
    2.  Supervisor'ı başlat.

---

## 🚀 GÖREV 3: Frontend - MQTT Ayarları

### 3.1. Settings Sayfası
*   `ui/src/pages/Settings.tsx` sayfasına "Home Assistant / MQTT" sekmesi ekle.
*   Alanlar: Host, Port, User, Pass, Enabled (Toggle).
*   "Test Connection" butonu ekle.

---

## ✅ KONTROL LİSTESİ (DOD)

- [ ] `requirements.txt` içinde `paho-mqtt` var.
- [ ] Backend'de `app/services/mqtt.py` dosyası çalışıyor.
- [ ] Bir olay olduğunda MQTT Explorer ile `thermal_vision/events` topic'inde veri görülüyor.
- [ ] `ha-addon/` klasöründe `config.yaml` ve `Dockerfile` hazır.
- [ ] UI üzerinden MQTT ayarları kaydedilebiliyor.
