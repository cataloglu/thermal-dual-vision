# Notification Specification - Smart Motion Detector v2

Bildirim sistemi spesifikasyonu (Scrypted Advanced Notifier'dan esinlenildi, daha iyi!)

**Hedef**: Multi-platform, rule-based, akıllı bildirimler

---

## 🎯 Notification Flow

```
Person Detection
  ↓
Event Created (DB)
  ↓
Notification Rules Check
  ↓
Send to Multiple Platforms:
  ├─ Telegram (instant)
  ├─ MQTT (Home Assistant)
  ├─ Pushover (mobile)
  └─ Webhook (custom)
```

---

## 📱 Supported Platforms

### 1. **Telegram** (Phase 12 - MVP)
```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "...",
    "chat_ids": ["123456"],
    "priority": "normal"
  }
}
```

**Gönderilecek**:
- Text message
- Collage image
- GIF animation
- MP4 video link

---

### 2. **MQTT** (Phase 12+ - HA için)
```json
{
  "mqtt": {
    "enabled": true,
    "host": "core-mosquitto",
    "port": 1883,
    "username": null,
    "password": null,
    "topic_prefix": "thermal_vision"
  }
}
```

**HA Add-on Auto-Discovery**:
- HA Supervisor üzerinden MQTT bilgileri otomatik çekilir (`services: mqtt:need`).
- Mosquitto add-on çalışıyorsa host/port/user/pass otomatik set edilir.
- Kullanıcı adı/parola boş ise sistem **anonim** bağlanır (broker izin veriyorsa).

**HA'da kullanımı**:
```yaml
binary_sensor:
  - platform: mqtt
    name: "Ön Kapı Person"
    state_topic: "thermal_vision/camera/cam-1/person"
    payload_on: "ON"
    payload_off: "OFF"
    off_delay: 30
```

---

### 3. **Pushover** (Phase 12+ - Opsiyonel)
```json
{
  "pushover": {
    "enabled": true,
    "user_key": "...",
    "api_token": "...",
    "priority": 1,
    "sound": "siren"
  }
}
```

---

### 4. **Webhook** (Phase 12+ - Custom)
```json
{
  "webhook": {
    "enabled": true,
    "url": "http://custom-server/api/alert",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer ..."
    }
  }
}
```

---

## 🎯 Rule-Based Notifications (Scrypted Advanced Tarzı)

**Config**:
```json
{
  "notification_rules": [
    {
      "id": "rule-1",
      "name": "Gece Kritik Alarm",
      "enabled": true,
      "conditions": {
        "time_range": {
          "start": "23:00",
          "end": "06:00"
        },
        "cameras": ["cam-1", "cam-2"],
        "zones": ["Giriş", "Bahçe"],
        "confidence_min": 0.7,
        "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
      },
      "actions": {
        "telegram": {
          "enabled": true,
          "priority": "critical",
          "sound": true,
          "message_template": "🚨 GECE ALARM: {camera_name}"
        },
        "mqtt": {
          "enabled": true,
          "topic": "thermal/critical_alarm"
        },
        "webhook": {
          "enabled": true,
          "url": "http://ha:8123/api/webhook/critical"
        }
      }
    },
    {
      "id": "rule-2",
      "name": "Gündüz Normal",
      "enabled": true,
      "conditions": {
        "time_range": {
          "start": "08:00",
          "end": "22:00"
        },
        "confidence_min": 0.5
      },
      "actions": {
        "telegram": {
          "enabled": true,
          "priority": "normal",
          "sound": false
        },
        "mqtt": {
          "enabled": true
        }
      }
    }
  ]
}
```

---

## 🔔 Interactive Notifications (Telegram)

**Telegram Bot API** ile:
```python
# Send with inline buttons
bot.send_photo(
    chat_id=chat_id,
    photo=collage,
    caption="🚨 Ön Kapı - Person Detected",
    reply_markup={
        "inline_keyboard": [
            [
                {"text": "📹 View Live", "url": "http://nvr/live/cam-1"},
                {"text": "🔕 Snooze 1h", "callback_data": "snooze_1h"}
            ],
            [
                {"text": "✅ Dismiss", "callback_data": "dismiss"}
            ]
        ]
    }
)
```

**Kullanıcı**:
- View Live → Canlı görüntü açılır
- Snooze 1h → 1 saat bildirim gelmez
- Dismiss → Bildirimi kapat

---

## 📊 Notification Priority Levels

### 1. **Normal**
```
Gündüz, düşük confidence
→ Sessiz bildirim
→ Banner göster
```

### 2. **High**
```
Gece, orta confidence
→ Ses çıkar
→ Banner + vibration
```

### 3. **Critical**
```
Gece, yüksek confidence, şüpheli davranış
→ Alarm sesi
→ Banner + vibration + LED
→ Bypass "Do Not Disturb"
```

---

## 🎯 MQTT Topics (HA İçin)

**Per Camera**:
```
thermal/camera/{camera_id}/motion → true/false
thermal/camera/{camera_id}/person → true/false
thermal/camera/{camera_id}/confidence → 0.85
thermal/camera/{camera_id}/snapshot → base64
thermal/camera/{camera_id}/zone → "Giriş Yolu"
thermal/camera/{camera_id}/threat_level → 0.9
```

**Global**:
```
thermal/system/status → online/offline
thermal/system/cameras_online → 5
thermal/events/latest → event_id
```

---

## 📋 Implementation Priority

**Phase 12** (MVP):
1. ✅ Telegram (basic)
2. ✅ MQTT (HA için kritik!)

**Phase 13+** (Post-MVP):
3. ⏳ Rule-based notifications
4. ⏳ Multiple notifiers (Pushover, webhook)
5. ⏳ Interactive actions (buttons)
6. ⏳ Priority levels
7. ⏳ Snooze functionality

---

## 🏆 Scrypted Advanced Notifier vs Bizimki

| Özellik | Scrypted Advanced | Bizimki (Planlanan) |
|---------|-------------------|---------------------|
| Telegram | ✅ | ✅ |
| MQTT | ✅ | ✅ |
| Rule-based | ✅ | ✅ |
| Multiple notifiers | ✅ | ✅ |
| Interactive buttons | ✅ | ✅ |
| Snooze | ✅ | ✅ |
| **AI Prompt Templates** | ❌ | ✅ 🔥 |
| **Threat Level Scoring** | ❌ | ✅ 🔥 |
| **Turkish Language** | ❌ | ✅ 🔥 |

**3 özellik bizde daha iyi!** 🏆

---

**Kaynak**: Scrypted Advanced Notifier (GitHub: apocaliss92)
