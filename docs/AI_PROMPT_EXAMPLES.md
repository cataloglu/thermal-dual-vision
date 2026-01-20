# AI Prompt Examples - Smart Motion Detector v2

Kamera bazında hazır prompt örnekleri (5 kamera için)

**Kullanım**: Kopyala-yapıştır, kendi kameran için düzenle

---

## 🏠 Senin Kameralar İçin Hazır Prompt'lar

### 📹 Kamera 1: Ön Kapı
```
Bu ön kapı kamerası görüntüsü.

Analiz et:
1. Kaç kişi var?
2. Ziyaretçi mi (postacı, kurye, misafir) yoksa şüpheli kişi mi?
3. Kapıya ne kadar yaklaştı? (uzak, yakın, kapıda)
4. Ne yapıyor? (zil çalıyor, bekliyor, geçiyor)
5. Tehdit seviyesi: Düşük/Orta/Yüksek

Kısa ve net Türkçe cevap ver (max 5 satır).
```

**Kullanım Senaryosu**:
- Gündüz: Ziyaretçi tespiti
- Gece: Şüpheli kişi tespiti

---

### 📹 Kamera 2: Sol Bahçe
```
Bu sol bahçe kamerası görüntüsü. Komşu sınırına yakın alan.

Analiz et:
1. Kaç kişi var?
2. Bahçe sınırı içinde mi dışında mı?
3. Komşudan mı geliyor yoksa dışarıdan mı?
4. Ne yapıyor? (geçiyor, duruyor, bahçeye giriyor)
5. Tehdit seviyesi: Düşük/Orta/Yüksek

Kısa ve net Türkçe cevap ver (max 5 satır).
```

**Kullanım Senaryosu**:
- Komşu vs yabancı ayrımı
- Bahçe sınırı kontrolü

---

### 📹 Kamera 3: Sağ Bahçe
```
Bu sağ bahçe kamerası görüntüsü.

Analiz et:
1. Kaç kişi var?
2. Bahçede mi yoksa sokakta mı?
3. Ne yapıyor? (yürüyor, duruyor, etrafa bakıyor)
4. Şüpheli davranış var mı? (saklanıyor, etrafa bakıyor)
5. Tehdit seviyesi: Düşük/Orta/Yüksek

Kısa ve net Türkçe cevap ver (max 5 satır).
```

---

### 📹 Kamera 4: Arka Bahçe
```
Bu arka bahçe kamerası görüntüsü. 
ÖNEMLI: Gece burada kimse olmamalı!

Analiz et:
1. Kaç kişi var?
2. Neden burada? (normal kullanım mı, izinsiz giriş mi)
3. Davranış: Normal mi şüpheli mi?
4. Arka kapıya yaklaşıyor mu?
5. Tehdit seviyesi: Düşük/Orta/Yüksek

Eğer gece ise tehdit seviyesini artır!
Kısa ve net Türkçe cevap ver (max 5 satır).
```

**Özel**: Gece vurgusu!

---

### 📹 Kamera 5: Garaj/Otopark
```
Bu garaj/otopark kamerası görüntüsü.

Analiz et:
1. Kaç kişi var?
2. Araç var mı? Hangi renk/tip?
3. Kişi ne yapıyor? (arabaya biniyor, iniyor, yürüyor)
4. Garaj kapısı açık mı kapalı mı?
5. Şüpheli durum var mı?

Kısa ve net Türkçe cevap ver (max 5 satır).
```

**Özel**: Araç tespiti!

---

## 🎯 UI'da Nasıl Olacak?

### Global AI Tab:
```
┌─────────────────────────────────────────┐
│ 🤖 AI SETTINGS                          │
│                                         │
│ [✓] Enable AI                           │
│                                         │
│ Prompt Template (Global):               │
│ ● Security Focused                      │
│ ○ Simple                                │
│ ○ Custom                                │
│                                         │
│ Custom Prompt (Global):                 │
│ [Tüm kameralar için varsayılan_____]    │
│                                         │
│ ℹ️ Her kamera kendi prompt'unu         │
│    override edebilir                    │
│                                         │
│ [Save]                                  │
└─────────────────────────────────────────┘
```

---

### Camera Edit (Per-Camera):
```
┌─────────────────────────────────────────┐
│ 📹 EDIT CAMERA: Ön Kapı                 │
│                                         │
│ Name: [Ön Kapı_______]                  │
│ Type: [Dual ▼]                          │
│                                         │
│ ─────────────────────────────────────   │
│                                         │
│ 🤖 AI Prompt (Optional):                │
│ [ ] Use custom prompt for this camera  │
│                                         │
│ [Hazır Şablonlar ▼]                     │
│   - Ön Kapı (ziyaretçi tespiti)        │
│   - Arka Bahçe (gece vurgusu)          │
│   - Garaj (araç tespiti)               │
│   - Custom (kendin yaz)                │
│                                         │
│ Custom Prompt:                          │
│ [Bu ön kapı kamerası. Ziyaretçi mi     │
│  yoksa şüpheli kişi mi analiz et.___]  │
│                                         │
│ [Preview AI Response] ← Test butonu    │
│                                         │
│ [Save Camera]                           │
└─────────────────────────────────────────┘
```

---

## 🔥 Avantajlar

**Kamera bazında prompt**:
1. ✅ Her kamera için context
2. ✅ Ön kapı vs arka bahçe farklı değerlendirilir
3. ✅ Kullanıcı özelleştirebilir
4. ✅ Hazır şablonlar (kopyala-yapıştır)
5. ✅ Preview test (AI'ya sor, cevabı gör)

**Scrypted'de YOK!** 🏆

---

## 📋 Database Schema (Güncelleme)

**Camera tablosu**:
```python
class Camera(Base):
    # ...
    ai_prompt_override: Optional[str]  # YENİ!
    use_custom_prompt: bool = False  # YENİ!
```

---

## 🎯 Implementation (Phase 11: AI Integration)

```python
def get_ai_prompt(camera, event):
    """Get AI prompt for camera."""
    
    # 1. Camera-level custom prompt (highest priority)
    if camera.use_custom_prompt and camera.ai_prompt_override:
        base_prompt = camera.ai_prompt_override
    
    # 2. Global custom prompt
    elif config.ai.custom_prompt:
        base_prompt = config.ai.custom_prompt
    
    # 3. Global template
    elif config.ai.prompt_template == "security_focused":
        base_prompt = SECURITY_FOCUSED_TEMPLATE
    
    # 4. Default
    else:
        base_prompt = SIMPLE_TEMPLATE
    
    # Add context
    prompt = f"""
{base_prompt}

Context:
- Kamera: {camera.name}
- Zaman: {event.timestamp}
- Confidence: {event.confidence:.0%}
- Zone: {event.zone_name}
"""
    
    return prompt
```

---

## ✅ HEMEN GÜNCELLİYORUM!

Dosyalar:
- ✅ AI_PROMPT_SPEC.md (güncellendi)
- ✅ AI_PROMPT_EXAMPLES.md (yeni - 5 kamera için hazır)
- ✅ CONFIG_REFERENCE.md (camera.ai_prompt_override eklendi)

**Commit ediyorum!** 🚀

<function_calls>
<invoke name="StrReplace">
<parameter name="path">c:\Users\Administrator\OneDrive\Desktop\Thermal Kamera Projesi\thermal-dual-vision\docs\CONFIG_REFERENCE.md