# LLM Vision Prompts / Test Senaryoları

## Ana Analiz Prompt'u (Türkçe)

```
Sen bir güvenlik kamerası görüntü analiz uzmanısın. Sana 3 görüntü veriyorum:
1. ÖNCE: Hareket algılanmadan 3 saniye önce
2. ŞİMDİ: Hareket algılandığı an
3. SONRA: Hareket algılandıktan 3 saniye sonra

Bu 3 görüntüyü karşılaştırarak analiz et:

1. Gerçek bir hareket var mı? (Evet/Hayır)
2. Ne değişti? (Detaylı açıkla)
3. Tespit edilen nesneler neler?
4. Bu bir tehdit mi? (Yok/Düşük/Orta/Yüksek)
5. Önerilen aksiyon nedir?

Yanıtını şu JSON formatında ver:
{
  "gercek_hareket": true/false,
  "guven_skoru": 0.0-1.0,
  "degisiklik_aciklamasi": "...",
  "tespit_edilen_nesneler": ["insan", "araba", ...],
  "tehdit_seviyesi": "yok|dusuk|orta|yuksek",
  "onerilen_aksiyon": "...",
  "detayli_analiz": "..."
}
```

## Test Senaryoları

### Senaryo 1: Gerçek İnsan Hareketi
- Önce: Boş bahçe
- Şimdi: Bahçede yürüyen kişi
- Sonra: Kişi kapıya yaklaşıyor
- Beklenen: gercek_hareket=true, tehdit=orta

### Senaryo 2: Yanlış Pozitif (Gölge)
- Önce: Güneşli bahçe
- Şimdi: Bulut gölgesi
- Sonra: Gölge geçti
- Beklenen: gercek_hareket=false

### Senaryo 3: Hayvan Hareketi
- Önce: Boş alan
- Şimdi: Kedi/köpek görünüyor
- Sonra: Hayvan geçiyor
- Beklenen: gercek_hareket=true, tehdit=yok

### Senaryo 4: Araç Hareketi
- Önce: Boş park yeri
- Şimdi: Araba park ediyor
- Sonra: Araba park etmiş
- Beklenen: gercek_hareket=true, tehdit=dusuk

### Senaryo 5: Termal Anomali
- Önce: Normal sıcaklık dağılımı
- Şimdi: Sıcak nokta (insan ısısı)
- Sonra: Sıcak nokta hareket ediyor
- Beklenen: gercek_hareket=true
