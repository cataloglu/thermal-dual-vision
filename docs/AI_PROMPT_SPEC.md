# AI Prompt Specification - Smart Motion Detector v2

OpenAI Vision API için prompt şablonları ve best practices.

**Hedef**: Güvenlik odaklı, kısa, net, Türkçe açıklamalar

---

## 🤖 OpenAI Vision API Kullanımı

### API Call Format:
```python
import openai

response = openai.ChatCompletion.create(
    model="gpt-4-vision-preview",
    messages=[
        {
            "role": "system",
            "content": "Sen bir ev güvenlik sistemi AI asistanısın."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": PROMPT_TEMPLATE
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": collage_base64  # 5 frame collage
                    }
                }
            ]
        }
    ],
    max_tokens=200,
    temperature=0.3  # Düşük = daha tutarlı
)

summary = response.choices[0].message.content
```

---

## 📝 Prompt Şablonları

### Template 1: Basit (Default)
```
Bu thermal kamera görüntüsünde ne görüyorsun? 
Kişi sayısı, ne yaptıkları ve şüpheli bir durum var mı kısaca açıkla.
```

**Kullanım**: Genel amaçlı  
**Uzunluk**: 2-3 cümle  
**Dil**: Türkçe/İngilizce

---

### Template 2: Güvenlik Odaklı (Önerilen)
```
Sen bir ev güvenlik sistemi AI asistanısın.
Bu thermal kamera görüntüsünü analiz et:

Kamera: {camera_name}
Zaman: {timestamp}
Confidence: {confidence:.0%}

Şunları Türkçe olarak belirt:
1. İnsan var mı? Kaç kişi?
2. Ne görüyorsun? (görünüm, hareket, konum)
3. Şüpheli durum var mı?
4. Yanlış alarm olabilir mi? (ağaç, gölge, hayvan, araba)
5. Tehdit seviyesi: Düşük/Orta/Yüksek

Kısa ve net cevap ver (max 5 satır).
```

**Kullanım**: Güvenlik sistemi  
**Uzunluk**: 5 satır  
**Dil**: Türkçe  
**Format**: Numaralı liste

---

### Template 3: Detaylı Analiz
```
Sen bir profesyonel güvenlik analisti AI'sısın.
Bu thermal kamera görüntü serisini (5 frame) analiz et:

Kamera: {camera_name}
Konum: {zone_name}
Zaman: {timestamp}
YOLOv8 Confidence: {confidence:.0%}

Detaylı analiz yap:

1. İNSAN TESPİTİ:
   - Kaç kişi var?
   - Nerede konumlanmışlar?
   - Ne yapıyorlar? (giriyor, çıkıyor, bekliyor, dolaşıyor)

2. GÖRSEL DETAYLAR:
   - Kıyafet rengi/tipi (varsa)
   - Boy/yapı (kısa, uzun, orta)
   - Taşıdığı eşya var mı?

3. HAREKET ANALİZİ:
   - Hareket yönü (sola, sağa, içeri, dışarı)
   - Hız (yavaş, normal, hızlı)
   - Davranış (normal, şüpheli)

4. DURUM DEĞERLENDİRMESİ:
   - Şüpheli durum var mı?
   - Yanlış alarm olabilir mi? (ağaç, hayvan, araba)
   - Tehdit seviyesi: Düşük/Orta/Yüksek
   - Önerilen aksiyon (izle, alarm ver, ignore)

Türkçe, kısa ve net cevap ver (max 10 satır).
```

**Kullanım**: Kritik event'ler  
**Uzunluk**: 10 satır  
**Dil**: Türkçe  
**Format**: Kategorize edilmiş

---

## 🎯 Config Schema

**Global AI Settings**:
```json
{
  "ai": {
    "enabled": true,
    "api_key": "***REDACTED***",
    "model": "gpt-4-vision-preview",
    "prompt_template": "security_focused",
    "custom_prompt": "Global prompt (tüm kameralar için)",
    "language": "tr",
    "max_tokens": 200,
    "temperature": 0.3,
    "timeout": 30
  }
}
```

**Per-Camera AI Prompt Override** (YENİ! 🔥):
```json
{
  "cameras": [
    {
      "id": "cam-1",
      "name": "Ön Kapı",
      "ai_prompt_override": "Bu ön kapı kamerası. Ziyaretçi mi yoksa şüpheli kişi mi analiz et.",
      "use_custom_prompt": true
    },
    {
      "id": "cam-2",
      "name": "Arka Bahçe",
      "ai_prompt_override": "Bu arka bahçe. Gece burada kimse olmamalı. Şüpheli mi değerlendir.",
      "use_custom_prompt": true
    },
    {
      "id": "cam-3",
      "name": "Garaj",
      "ai_prompt_override": null,  // Global prompt kullan
      "use_custom_prompt": false
    }
  ]
}
```

**Prompt Hierarchy** (Öncelik Sırası):
```
1. Camera-level custom prompt (en yüksek)
   ↓
2. Global custom prompt
   ↓
3. Global template (security_focused)
   ↓
4. Default template (simple)
```

**Avantaj**: Her kamera için özel context! 🎯

---

## 📋 Prompt Template Seçimi (UI'da)

**AI Settings Tab**:
```
┌─────────────────────────────────────────┐
│ Prompt Template:                        │
│ ○ Simple (2-3 cümle)                    │
│ ● Security Focused (5 satır, önerilen) │
│ ○ Detailed Analysis (10 satır)         │
│ ○ Custom (kendi prompt'unu yaz)        │
│                                         │
│ [Preview Prompt] ← Button              │
│                                         │
│ Language: [Türkçe ▼]                    │
└─────────────────────────────────────────┘
```

---

## 💡 Best Practices

### 1. **Kısa Prompt = Hızlı + Ucuz**
```
Simple: ~50 tokens → $0.005 per event
Detailed: ~200 tokens → $0.02 per event
```

### 2. **System Message Kullan**
```python
{
    "role": "system",
    "content": "Sen bir güvenlik sistemi AI'sısın. Kısa ve net cevap ver."
}
```

**Sonuç**: Daha tutarlı cevaplar

---

### 3. **Temperature Düşük**
```
temperature: 0.3  // Düşük = tutarlı, yüksek = yaratıcı
```

**Güvenlik için**: Tutarlı olmalı!

---

### 4. **Max Tokens Sınırla**
```
max_tokens: 200  // Yeterli + ucuz
```

---

## 🎯 Örnek Response'lar

### Gerçek Tehdit:
```
Prompt: Security Focused
Response:
"1. İnsan var: 1 kişi
2. Görünüm: Arka bahçede, siyah mont, kapüşonlu
3. Şüpheli: Evet! Gece 02:00'da bahçede dolaşıyor
4. Yanlış alarm: Hayır
5. Tehdit: YÜKSEK"
```

**Telegram'a**:
```
🚨 YÜKSEK TEHDİT!
Arka bahçede kapüşonlu kişi, gece 02:00
```

---

### False Positive (Ağaç):
```
Prompt: Security Focused
Response:
"1. İnsan var: Hayır
2. Görünüm: Ağaç ve duvar, rüzgarda sallanıyor
3. Şüpheli: Hayır
4. Yanlış alarm: Evet, ağaç hareketi
5. Tehdit: Düşük"
```

**Telegram'a**:
```
ℹ️ Düşük Tehdit
Muhtemelen ağaç hareketi (yanlış alarm)
```

---

## 📝 HEMEN EKLIYORUM!

<function_calls>
<invoke name="StrReplace">
<parameter name="path">c:\Users\Administrator\OneDrive\Desktop\Thermal Kamera Projesi\thermal-dual-vision\docs\CONFIG_REFERENCE.md