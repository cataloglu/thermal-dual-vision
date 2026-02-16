# Disk kullanımı: 1484 GB neden dolu görünüyor?

## Önemli: O rakam **tüm sistemin** kullanımı

Gördüğün **1484.8 / 1833.08 GB** = Bilgisayarın (veya Home Assistant host’un) **tüm diskinin** kullanımı. Sadece bu addon’un kullandığı alan değil.

Yani:
- **Disk (used/total)** = Tüm sistem (/, root)
- **Addon verisi** = Sadece bu addon’un yazdığı klasörler (genelde birkaç GB – onlarca GB bile olabilir ama 1 TB değil)

Her şeyi sildiysen addon içinde (event’ler, medya) sadece **addon’un kullandığı kısım** azalır. 1484 GB’ın büyük kısmı başka yerlerden geliyor olabilir.

---

## Bu addon nereye yazıyor?

Addon verisi **tek yerde**: `/app/data` (HA’da addon config ile mount edilir).

| Alt klasör      | İçerik                          | Kabaca boyut        |
|-----------------|----------------------------------|---------------------|
| `recordings/`  | Son 1 saatlik kamera kayıtları   | Kamera sayısına göre (saatlik buffer) |
| `media/`       | Event collage + MP4              | retention_days / disk_limit’e göre temizlenir |
| `models/`      | YOLO modelleri                   | Birkaç yüz MB – birkaç GB |
| `config.json`  | Ayar dosyası                     | Çok küçük           |
| Veritabanı     | SQLite                           | Küçük               |

Yani addon tek başına **1 TB’a yakın** alan doldurmaz; büyük sayı sistemdeki diğer verilerden gelir.

---

## “Her şeyi sildim” deyince ne olur?

- **Uygulama içinde event’leri / medyayı silmek** → Sadece `media/` ve veritabanındaki event kayıtları azalır. Addon’un kullandığı alan düşer.
- **1484 GB’ın büyük kısmı** → Addon dışı: Home Assistant, diğer addon’lar, Docker imajları/volumes, işletim sistemi, yedekler, başka uygulama verileri.

Yani “hepsini sildim ama hâlâ 1484 GB” demen normal; çünkü o rakam **tüm disk**, addon değil.

---

## Addon’un gerçekten ne kadar kullandığını görmek

- **Diagnostics** sayfasında (veya `/api/system/info` yanıtında) **“Addon verisi (GB)”** alanı var. Bu, sadece `/app/data` altındaki toplam boyut = **bu addon’un** kullandığı alan.
- Karşılaştır:
  - **Disk:** 1484 / 1833 GB → tüm sistem
  - **Addon verisi:** X GB → sadece bu addon

Böylece “bu kadar GB’ın ne kadarı bu addon?” sorusunu net görürsün.

---

## 1484 GB’ı kim dolduruyor? (Sistem tarafında)

Bunu addon içinden tek tek sayamayız; **host (sistem)** tarafında bakmak gerekir:

1. **Home Assistant:**  
   - Config, veritabanı, loglar, yedekler (ör. `config/`, `backups/`).  
   - HA arayüzü veya SSH ile bu klasörlerin boyutuna bak.

2. **Docker (HA Core / Supervised kurulumlarda):**  
   - `docker system df`  
   - İmajlar, container’lar, volume’lar. Eski imajlar/volume’lar çok yer tutabilir.

3. **Diğer addon’lar**  
   - Her addon kendi data/config alanına yazar; toplamda onlarca–yüzlerce GB olabilir.

4. **Trash / silinmemiş dosyalar**  
   - “Sildim” dediğin yer çöp kutusu kullanıyorsa veya bir uygulama dosyayı hâlâ açık tutuyorsa, disk boşalmaz.

5. **Farklı disk/partition**  
   - Bazen “tüm disk” tek bir büyük partition’da olur; 1484 GB onun toplam kullanımıdır.

Özet: **1484 GB = tüm sistem.** Addon’un kullandığı kısım Diagnostics’teki **“Addon verisi (GB)”** ile sınırlı; geri kalanı host’ta (HA, Docker, diğer addon’lar, OS) kontrol etmek gerekir.
