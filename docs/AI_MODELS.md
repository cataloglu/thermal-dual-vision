# AI Models Reference - Smart Motion Detector v2

OpenAI Vision modelleri karşılaştırması ve öneriler.

**Güncelleme**: 2026-01-20

---

## 🤖 Desteklenen Modeller

### 1. **gpt-4o** (Önerilen) ✅

**Özellikler**:
- Vision support: ✅
- Speed: Hızlı
- Cost: $0.005 per image
- Quality: Yüksek
- Context: 128K tokens

**Kullanım**:
```json
{
  "ai": {
    "model": "gpt-4o"
  }
}
```

**Avantaj**:
- ✅ Hızlı (2-3 saniye)
- ✅ Ucuz
- ✅ Kaliteli
- ✅ Yeni (2024)

**Senin için**: ✅ EN İYİ SEÇİM!

---

### 2. **gpt-4o-mini** (Ekonomik)

**Özellikler**:
- Vision support: ✅
- Speed: Çok hızlı
- Cost: $0.002 per image
- Quality: İyi
- Context: 128K tokens

**Kullanım**:
```json
{
  "ai": {
    "model": "gpt-4o-mini"
  }
}
```

**Avantaj**:
- ✅ Çok hızlı (1-2 saniye)
- ✅ Çok ucuz (gpt-4o'nun yarısı)
- ⚠️ Kalite biraz düşük

**Senin için**: ✅ Çok event varsa (maliyet düşer)

---

### 3. **gpt-4-vision-preview** (Eski)

**Özellikler**:
- Vision support: ✅
- Speed: Yavaş
- Cost: $0.02 per image (pahalı!)
- Quality: Çok yüksek
- Context: 128K tokens

**Kullanım**:
```json
{
  "ai": {
    "model": "gpt-4-vision-preview"
  }
}
```

**Avantaj**:
- ✅ En yüksek kalite
- ❌ Yavaş (5-7 saniye)
- ❌ Pahalı (4x)

**Senin için**: ⚠️ Gerekli değil (gpt-4o yeterli)

---

### ❌ KULLANILMAMALI

**gpt-4** (vision YOK!):
```json
{
  "ai": {
    "model": "gpt-4"  // ❌ HATA! Vision yok!
  }
}
```

**Sonuç**: API hatası verir! 🔥

**gpt-3.5-turbo** (vision YOK!):
```json
{
  "ai": {
    "model": "gpt-3.5-turbo"  // ❌ HATA!
  }
}
```

---

## 💰 Maliyet Hesabı

**Senin için** (günde 10 event):

### gpt-4o:
```
10 event/gün × $0.005 = $0.05/gün
$0.05 × 30 = $1.5/ay
```

### gpt-4o-mini:
```
10 event/gün × $0.002 = $0.02/gün
$0.02 × 30 = $0.6/ay
```

### gpt-4-vision-preview:
```
10 event/gün × $0.02 = $0.2/gün
$0.2 × 30 = $6/ay
```

**Önerim**: **gpt-4o** ($1.5/ay - uygun!)

---

## 🎯 Default Config

**Güncellendi**:
```json
{
  "ai": {
    "enabled": false,
    "model": "gpt-4o",  // YENİ! (eski: gpt-4)
    "prompt_template": "security_focused",
    "language": "tr",
    "max_tokens": 200,
    "temperature": 0.3
  }
}
```

---

## 📋 Pydantic Model (Güncellendi)

```python
class AIConfig(BaseModel):
    model: Literal["gpt-4o", "gpt-4o-mini", "gpt-4-vision-preview"] = Field(
        default="gpt-4o",
        description="OpenAI model with vision support"
    )
```

**Validation**: Sadece vision modelleri seçilebilir! ✅

---

**Düzeltme yapıldı ve commit ediliyor!** 🚀
