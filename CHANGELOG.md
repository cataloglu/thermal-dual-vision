# Changelog

Tüm önemli değişiklikler bu dosyada listelenir.

Format [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/) esas alınır.

---

## [4.0.78] - 2026-03-03

### Düzeltmeler

- **`ffmpeg exit(code=0)` kök neden ayrıştırması eklendi**: Exit anında son ffmpeg stderr satırı loga taşındı; böylece “niye exit oldu” bilgisi artık görünür.
- **İzole `code=0` için yanlış fallback azaltıldı**: Tekil `ffmpeg exit(0)` olayında doğrudan OpenCV fallback yerine önce ffmpeg tekrar deneniyor; yalnızca kısa pencerede tekrar eden `code=0` veya yüksek reconnect baskısında fallback açılıyor.
- **RTSP timeout taban değeri yükseltildi**: Çok düşük input timeout nedeniyle oluşan gereksiz EOF/code=0 çıkışlarını azaltmak için ffmpeg RTSP timeout alt sınırı 15s yapıldı.
- **Test kapsamı genişletildi**: İzole/repeat `code=0`, reconnect pressure ve non-zero exit durumlarında fallback kararını doğrulayan unit test eklendi.

## [4.0.77] - 2026-03-03

### Düzeltmeler

- **Reconnect sonrası thermal kör pencere azaltıldı**: Warmup/reconnect döneminde motion artık tamamen sıfırlanmıyor; güçlü motion sinyali varsa event hattına geçebiliyor.
- **Tek kamera thermal suppression döngüsü yumuşatıldı**: `inference_suppressed` tekrarlarını azaltmak için single-camera suppression streak yükseltildi ve suppression süresi kısaltıldı.
- **Test kapsamı genişletildi**: Thermal warmup gate helper ve güncellenen suppression politikası için detector unit testleri güncellendi.

## [4.0.76] - 2026-03-02

### Düzeltmeler

- **Kısa walk-through event yakalama iyileştirildi (thermal)**: Tek kamera akışında temporal tutarlılık kapısı 3 kare yerine 2 kare ile event adayını ilerletecek şekilde güncellendi; kısa süreli insan geçişlerinde kaçırma azaltıldı.
- **Yüksek min_area altında thermal static guard dengelendi**: Hareketli izlerin event’e geçişinde motion-area kapısı, çok yüksek `base_min_area` değerlerinde aşırı sertleşmeyecek şekilde normalize edildi; “motion active var ama event yok” vakaları azaltıldı.
- **Test kapsamı güncellendi**: Thermal temporal politika beklentileri güncellendi ve yüksek `base_min_area` ile hareketli track’in geçişini doğrulayan unit test eklendi.

## [4.0.75] - 2026-03-02

### Düzeltmeler

- **Auto modda fallback sonrası ffmpeg’e zorunlu dönüş**: Geçici OpenCV fallback süresi bittiğinde backend seçimi artık reconnect baskısı beklemeden tekrar ffmpeg’i tercih ediyor.
- **OpenCV’de takılı kalma azaltıldı**: Uzun süre OpenCV’de kalıp periyodik `read failures` reconnect döngüsüne giren kameralarda ffmpeg’e geri dönüş daha deterministik hale getirildi.
- **Test güncellendi**: Auto modun fallback sonrası ffmpeg’e geri dönmesini doğrulayan unit test beklentileri güncellendi.

## [4.0.74] - 2026-03-02

### Düzeltmeler

- **FFmpeg exit fallback süresi adaptif hale geldi**: `ffmpeg exit(0)` sonrası OpenCV fallback artık reconnect baskısına göre 180s/360s/600s seviyelerinde ayarlanıyor; izole kesintilerde ffmpeg’e daha hızlı dönüş sağlanıyor.
- **Non-zero exit fallback adaptasyonu**: Hata kodlu exit durumlarında fallback süresi baskıya göre 120s/210s/300s olarak ölçeklendi.
- **Early retry eşiği düşürüldü**: Fallback penceresi içindeyken OpenCV reconnect baskısı `>=3` olduğunda ffmpeg erken tekrar deneniyor.
- **Test güncellendi**: Yeni adaptif fallback süreleri ve fallback içi early retry eşiği için unit testler güncellendi.

## [4.0.73] - 2026-03-02

### Düzeltmeler

- **Fallback içinde erken ffmpeg retry**: Auto modda OpenCV fallback aktifken reconnect baskısı yükselirse 600s dolmasını beklemeden ffmpeg backend erken tekrar denenir.
- **Daha net backend logları**: Erken ffmpeg geri denemesi için reconnect pressure ve fallback kalan süre loglanır.
- **Yeni test**: Fallback penceresi içinde pressure yüksek/düşük senaryolarında backend seçim davranışını doğrulayan unit test eklendi.

## [4.0.72] - 2026-03-02

### Düzeltmeler

- **Auto backend recovery iyileştirildi**: Fallback süresi bittikten sonra OpenCV tarafında reconnect baskısı devam ediyorsa sistem kontrollü şekilde tekrar ffmpeg backend’i deniyor.
- **Pressure-aware backend seçimi**: Backend seçimi artık son reconnect yoğunluğunu da dikkate alıyor; OpenCV’de takılı kalan döngülerde ffmpeg’e dönüş penceresi açıldı.
- **Yeni test**: Auto modda reconnect pressure altında ffmpeg’e geri deneme davranışı için unit test eklendi.

## [4.0.71] - 2026-03-02

### Düzeltmeler

- **OpenCV steady-state reconnect hardening**: Fallback süresi bitse bile OpenCV backend üzerinde read-failure reconnect eşiği/timeout/cooldown daha konservatif hale getirildi.
- **Backend-aware stale-age gate**: OpenCV backend aktifken reconnect kararı için daha uzun “last successful frame age” zorunlu tutuldu; periyodik reconnect döngüsü azaltıldı.
- **Test kapsamı genişletildi**: OpenCV steady-state reconnect toleransı ve opencv-aware stale-age gate davranışı için yeni unit testler eklendi.

## [4.0.70] - 2026-03-01

### Düzeltmeler

- **Kolaj boyutu sınırlandı (hard cap)**: `collage.jpg` artık yüksek entropy/noise karelerde bile hedef byte limitini aşmamak için kaliteyi kademeli düşürerek kaydediliyor.
- **AI kolaj boyutu daha da küçültüldü**: `collage_ai.jpg` için daha düşük byte tavanı uygulanarak OpenAI görsel yükü/latency azaltıldı.
- **Yeni testler**: Gürültülü karelerle hem normal kolaj hem AI kolaj için “boyut limiti korunuyor” unit testleri eklendi.

## [4.0.69] - 2026-03-01

### Düzeltmeler

- **Collage zaman yayılımı genişletildi**: 6 kare artık yeterli zaman aralığı varsa daha geniş event penceresine yayılıyor; “aynı saniyede 6 kare” problemi azaltıldı.
- **AI collage context genişletildi**: Pre/post motion hedefleri dinamik hale getirildi; AI için başlangıç-orta-bitiş akışı daha anlaşılır hale getirildi.
- **AI prompt metni güncellendi**: Prompt artık kare aralığının sabit olmadığını açıkça belirtiyor (saniye altı + birkaç saniye arası).
- **Test kapsamı artırıldı**: Collage/AI-collage seçiminde zaman yayılımını doğrulayan yeni unit testler eklendi.

## [4.0.68] - 2026-03-01

### Düzeltmeler

- **Fallback sırasında read-failure reconnect daha da yumuşatıldı**: FFmpeg exit sonrası geçici OpenCV fallback aktifken reconnect eşik/timeout/cooldown değerleri otomatik yükseltiliyor.
- **Fallback-aware stale-age gate eklendi**: Fallback penceresinde reconnect kararı için daha uzun “son başarılı frame yaşı” zorunlu tutuldu; kısa RTSP takılmalarında gereksiz reopen azaltıldı.
- **Test kapsamı genişletildi**: Fallback aktif durumda stream reconnect politikasını ve fallback-age gate davranışını doğrulayan unit testler eklendi.

## [4.0.67] - 2026-03-01

### Düzeltmeler

- **Preset ekranı sadeleştirildi (tek seçim akışı)**: Üstte tek “Hızlı kullanım modu” (Stabil / Dengeli / Yakalama odaklı) ile tüm gerekli ayarlar tek tıkla uygulanır.
- **Kafa karıştıran çift grup varsayılan olarak gizlendi**: Eski “Genel preset” + “Termal ince ayar” blokları artık gelişmiş detay altında, isteyene açılır durumda.
- **Açık kapsam metni eklendi**: Hızlı modun ne yaptığını ve detaylı presetlerin sadece ileri kullanım için olduğunu belirten metinler eklendi.
- **TR/EN çeviriler güncellendi**: Yeni hızlı mod ve gelişmiş preset toggle metinleri eklendi.

## [4.0.66] - 2026-03-01

### Düzeltmeler

- **Reconnect flapping (read failures) daha toleranslı hale getirildi**: Thermal stream’lerde kısa upstream RTSP stall’larında hemen reconnect yerine daha güçlü stale-age şartı aranıyor.
- **Reconnect pressure adaptasyonu eklendi**: Son 5 dakikadaki reconnect sayısı arttıkça `read_failure` eşik/timeout/cooldown değerleri otomatik yükseltiliyor; `Reconnecting camera ... after read failures` döngüleri azaltıldı.
- **Yeni stale-age gate eklendi**: Reconnect kararı için sadece failure sayısı değil, “son başarılı frame’den geçen süre” için dinamik bir minimum yaş eşiği zorunlu kılındı.
- **Test kapsamı güncellendi**: Thermal + reconnect pressure altında stream policy ve reconnect age gate davranışını doğrulayan unit testler eklendi.

## [4.0.65] - 2026-03-01

### Düzeltmeler

- **“Collage’de insan var, video’da yok” senaryosu düzeltildi (threading worker)**: Event media artık event timestamp + pre/postbuffer penceresine göre seçiliyor; geçmiş buffer’dan alakasız (stale) frame karışması engellendi.
- **Media window fallback sıkılaştırıldı**: Tam pencere boşsa önce kontrollü geniş pencere, yine boşsa sadece son (tail) frame seti kullanılıyor; tarihsel eski person frame’lerinin collage/video’ya taşınması azaltıldı.
- **Delayed recording replace güvenli hale getirildi**: Zaten üretilmiş `timelapse.mp4` varsa 65s sonra recording’den üzerine yazılmıyor; böylece event-anına hizalı MP4 korunuyor.
- **Test kapsamı genişletildi**: Event window filtreleme (frame/video) ve mevcut MP4’ü delayed replace’in ezmemesi için unit test eklendi.

## [4.0.64] - 2026-03-01

### Düzeltmeler

- **Multi-camera recall güçlendirildi (thermal)**: Eşzamanlı aktif kamera sayısı arttığında thermal suppression artık çok daha geç devreye giriyor (streak ciddi yükseltildi), kısa walk-through kaçırmaları azaltıldı.
- **Concurrent thermal confidence politikası eklendi**: Çoklu kamera + güçlü motion sinyalinde thermal confidence eşiği kontrollü gevşetiliyor; “aynı anda sadece tek kamera yakalıyor” senaryosunda diğer kameraların da evente düşmesi kolaylaştırıldı.
- **Gated thermal retry eklendi**: Multi-camera durumda ilk infer boşsa ve motion güçlü ise tek seferlik hafif düşük eşik retry çalışıyor; contention anında kaçırma azaltıldı.
- **Thread/MP parity güncellendi**: Aynı recall-biased suppression + thermal confidence/retry yaklaşımı multiprocessing worker’a da taşındı.
- **Test kapsamı güncellendi**: Yeni thermal confidence politikasını doğrulayan unit test eklendi.

## [4.0.63] - 2026-03-01

### Düzeltmeler

- **FFmpeg→OpenCV fallback mantık hatası düzeltildi**: Geçici fallback aktifken worker artık yanlışlıkla aynı döngüde tekrar ffmpeg açmayı denemiyor; gerçekten OpenCV reopen yoluna geçiyor.
- **Backend seçim akışı netleştirildi**: Reopen sırasında backend seçimi helper fonksiyona taşındı; fallback penceresi aktifse OpenCV zorlanır, forced-ffmpeg modunda pencere bitince ffmpeg yeniden denenir.
- **Test kapsamı artırıldı**: Reopen backend seçimi için fallback aktif/pasif ve auto/ffmpeg kombinasyonlarını doğrulayan unit test eklendi.

## [4.0.62] - 2026-03-01

### Düzeltmeler

- **FFmpeg exit(0) için daha agresif stabilizasyon**: `ffmpeg capture exited (code=0)` görüldüğünde kamera bazlı geçici OpenCV fallback penceresi eklendi; aynı kamerada tekrar eden ffmpeg reopen döngüsü kırılmaya çalışılır.
- **Reconnect sonrası thermal baseline reseti**: Stream reconnect anında thermal motion state/baseline temizlenip daha uzun warmup uygulanıyor; reconnect sonrası görülen `area=0 -> çok büyük area` spike’ları azaltıldı.
- **Forced ffmpeg modunda da fallback güvenliği korundu**: `capture_backend=ffmpeg` kullanılırken de stabilite için geçici OpenCV fallback devreye girebilir.
- **Test kapsamı genişletildi**: Exit-code fallback süresi ve reconnect sonrası thermal warmup reset davranışı için yeni unit testler eklendi.

## [4.0.61] - 2026-03-01

### Düzeltmeler

- **FFmpeg flapping fallback kapsamı genişletildi**: Anti-flapping OpenCV fallback artık sadece `capture_backend=auto` için değil, `capture_backend=ffmpeg` seçiliyken de devreye giriyor.
- **Reconnect flapping logu iyileştirildi**: Fallback tetiklenirken aktif capture mode (`auto/ffmpeg`) loglanıyor; sahadaki teşhis netliği arttı.
- **Thread behavior test kapsamı güncellendi**: Fallback izin koşulu için (`auto`, `ffmpeg`, `opencv`) ek unit test eklendi.

## [4.0.60] - 2026-02-28

### Düzeltmeler

- **FFmpeg reconnect flapping için auto fallback eklendi**: Thread worker’da kısa pencerede sık FFmpeg reconnect tespit edilirse (`capture_backend=auto`), kamera OpenCV backend’e düşürülerek sürekli ffmpeg reconnect döngüsü yumuşatıldı.
- **Reconnect nedeni gözlemlenebilir hale getirildi**: FFmpeg process exit durumunda reconnect nedeni stream istatistiklerine işleniyor (`ffmpeg_exit` / `ffmpeg_reopen`), teşhis netliği artırıldı.
- **Thermal active/idle chatter azaltıldı**: Thermal motion state için kısa süreli `active hold` penceresi eklendi; eşik çevresinde anlık düşüşlerde hızlı active→idle flip azalır.
- **Thread/MP parity korundu**: Thermal `active hold` mantığı multiprocessing worker tarafına da taşındı.

## [4.0.59] - 2026-02-28

### Düzeltmeler

- **Reconnect flapping yumuşatıldı**: Kamera yeni reconnect olduktan hemen sonra read-failure kaynaklı yeniden reconnect kararları daha toleranslı hale getirildi; kısa decoder/akış ısınma dalgalanmaları için erken reconnect azaltıldı.
- **Thermal motion gate anti-chatter eklendi**: `active/idle` geçişleri için streak tabanlı hysteresis eklendi (üst/alt eşik ardışık frame onayı); eşik çevresi jitter’da hızlı state zıplamaları azaltıldı.
- **Thermal auto min-area geçişleri kademelendi**: Auto-learned `min_area` thermal tarafta tek adımda sert düşüp/yükselmek yerine slew-limit ile kademeli değişiyor; ani eşik düşüşlerinden gelen false active oranı azaltıldı.
- **Reconnect warmup ile motion gate korundu**: Kamera reconnect sonrası kısa pencerede thermal motion gate kontrollü ısınma süresi uygulayarak reconnect sonrası anlık motion spike gürültüsü azaltıldı.
- **Thread/MP parity korundu**: Aynı reconnect stabilizasyonu + thermal motion anti-chatter davranışı multiprocessing worker’a da taşındı.

## [4.0.58] - 2026-02-28

### Düzeltmeler

- **Suppression re-arm cooldown eklendi**: Thermal suppression bir kez kalktıktan sonra hemen tekrar devreye girmiyor; `45 empty -> 12s suppress` loop frekansı düşürüldü.
- **Recent peak motion smoothing eklendi**: Tek frame area düşüşlerinde suppression kararı için son kısa pencere tepe motion alanı dikkate alınıyor; “anlık düşüş yüzünden tekrar suppress” azaltıldı.
- **Reconnect sonrası suppression grace eklendi**: Kamera reconnect olur olmaz eski suppression state devam etmiyor, kısa bir grace penceresiyle detection tekrar nefes alıyor.
- **Thread/MP parity korundu**: Aynı suppression rearm + peak smoothing mantığı multiprocessing worker’a da eklendi.

## [4.0.57] - 2026-02-28

### Düzeltmeler

- **Edge jitter (ağaç/sabit siluet) için yön tutarlılığı guard’ı eklendi**: Sadece spread/IoU değil, son 5 framede net center displacement oranı da kontrol edilerek “sağa-sola sallanan ama ilerlemeyen” kutular bloklandı.
- **Thermal false-positive filtresi sıkılaştırıldı**: Düşük/orta confidence için border-oscillation pattern’i (yüksek spread + düşük net displacement) event öncesinde kesiliyor.
- **Suppression döngüsü azaltıldı**: Motion hâlâ anlamlıyken thermal `empty_inference_streak` kör artmıyor; `motion active` sırasında gereksiz `inference_suppressed` tetiklenmesi azaltıldı.
- **Thread/MP parity korundu**: Aynı edge-oscillation + suppression-hold kuralı multiprocessing worker’a da uygulandı.

## [4.0.56] - 2026-02-28

### Düzeltmeler

- **Sabit ağaç/siluet kutuları için edge-touch guard eklendi**: Frame sınırına yapışan bbox pattern’i (border-hugging jitter) düşük/orta confidence’da evente düşmesi engellendi.
- **Hareket geçiş kriteri rafine edildi**: Sadece spread değil; spread + IoU + confidence + motion-area birlikte doğrulanarak jitter kaynaklı false-positive azaltıldı.
- **Thread/MP parity güncellendi**: Aynı edge-touch + IoU kuralı multiprocessing worker’a da taşındı.

## [4.0.55] - 2026-02-28

### Düzeltmeler

- **Kolajdaki sabit kutu (jitter ghost) için IoU guard eklendi**: Sadece center spread değil, ardışık bbox overlap (IoU) deseni de kontrol edilerek aynı siluete yapışan statik kutular evente düşmesi zorlaştırıldı.
- **Hareket imzası sıkılaştırıldı**: Event öncesi “gerçek hareket” için daha yüksek center spread + daha düşük IoU birlikte aranıyor; jitter kaynaklı sahte hareketler filtreleniyor.
- **Thread/MP parity korundu**: Aynı IoU tabanlı guard multiprocessing worker’a da uygulandı.

## [4.0.54] - 2026-02-28

### Düzeltmeler

- **Kolajdaki statik kutu pattern’i için guard sıkılaştırıldı**: Multi-camera durumda da statik bbox artık otomatik geçmez; düşük/orta confidence için hareket (center spread) zorunlu hale getirildi.
- **Static ghost eşiği güncellendi**: Bbox center spread eşiği 8 px’e yükseltildi; “aynı noktada titreyen kutu” evente daha zor düşer.
- **Thread/MP parity korundu**: Aynı sıkılaştırılmış static-guard kuralı multiprocessing worker’a da uygulandı.

## [4.0.53] - 2026-02-28

### Düzeltmeler

- **Retention cleanup hatası düzeltildi**: Event klasöründe `collage_ai.jpg` veya alt klasör artığı kaldığında görülen `Directory not empty` hataları için silme adımı recursive hale getirildi.
- **Log gürültüsü azaltıldı**: Startup/cleanup sırasında retention worker’ın aynı event klasörleri için ardışık hata spam’i engellendi.

## [4.0.52] - 2026-02-28

### Düzeltmeler

- **Boş sahne false-positive (0.52–0.64) bloklandı**: Multi-camera durumunda static guard artık low-confidence thermal kutuları otomatik geçirmez; confidence floor altı evente gitmez.
- **Static guard bypass kapatıldı**: Çoklu kamera hareketinde guard’ın tamamen devreden çıkması engellendi, düşük güvenli statik hayalet kutular filtreleniyor.
- **Thread/MP parity iyileştirildi**: Aynı low-confidence bloklama kuralı multiprocessing worker’a da taşındı.

## [4.0.51] - 2026-02-28

### Düzeltmeler

- **Boş sahne false-positive guard eklendi (thermal)**: Event öncesi son frame’lerde bbox merkezi neredeyse sabitse event bloke edilir; hareketli iz veya güçlü conf+motion yoksa static ghost event oluşmaz.
- **Suppression sonrası ghost spam azaltıldı**: Suppression/probe döngüsünden gelen statik thermal kutular için evente gitmeden ek güvenlik kapısı eklendi.
- **Thread/MP parity güncellendi**: Aynı static-ghost guard multiprocessing worker tarafına da taşındı.

## [4.0.50] - 2026-02-28

### Düzeltmeler

- **Thermal suppression tek kamerada da recall-odaklı yapıldı**: Varsayılan profil artık daha geç suppress eder (daha yüksek empty streak) ve daha kısa suppress tutar; `15 empty -> 30s` döngüsü yumuşatıldı.
- **Aktif kamera sayımı kısa pencereyle stabilize edildi**: `motion_active` anlık flicker’ında yanlış düşük sayımı azaltmak için son hareket zamanı da (kısa pencere) adaptif hesapta dikkate alındı.
- **Thread/MP parity güçlendirildi**: MP worker’da da aynı recall-biased suppression davranışı uygulanarak iki worker arasında davranış farkı azaltıldı.

## [4.0.49] - 2026-02-27

### Düzeltmeler

- **Suppression tekrar tetikleme döngüsü gevşetildi**: Çoklu aktif kamerada thermal suppression artık daha geç devreye girer (daha yüksek empty streak) ve daha kısa sürer; sürekli `inference_suppressed` döngüsünün gerçek geçişleri bastırması azaltıldı.
- **Aktif kamera sayımı düzeltmesi devreye alındı**: Adaptif suppression politikasının çoklu kamera yükünü gerçekten dikkate alması garanti altına alındı (`motion_active` state).
- **Phantom/duplicate silme tarafı korunarak daha güvenli bırakıldı**: Orta confidence gerçek olayların tutulması korunur, sadece aşırı duplicate + çok düşük confidence olaylar silinir.

## [4.0.48] - 2026-02-27

### Düzeltmeler

- **Aktif kamera sayımı düzeltildi (kritik)**: Adaptif thermal politikaları hesaplanırken state’den yanlış alan okunuyordu; artık runtime `motion_active` bayrağı doğru sayılır, çoklu kamera yüküne göre probe/threshold tuning gerçekten devreye girer.
- **Phantom erken-drop daha konservatif**: Detector’daki static phantom kriterleri (conf/spread/duplicate) daha sıkılaştırıldı; gerçek kişi geçişlerinin yanlışlıkla erken silinmesi azaltıldı.
- **MP4 duplicate auto-delete daha güvenli**: Media tarafında duplicate kaynaklı otomatik silme sadece neredeyse tamamen duplicate + çok düşük confidence olaylarda çalışır.

## [4.0.47] - 2026-02-27

### Düzeltmeler

- **Thermal auto min-area runaway daha agresif sınırlandı**: Loglarda görülen `min=1500` kilitlenmesini azaltmak için thermal auto cap değerleri tekrar aşağı çekildi; eşzamanlı sahnede motion gate’in gerçek geçişleri elemesi azaltıldı.
- **Phantom erken-silme konservatifleştirildi (detector)**: Erken phantom drop için duplicate/conf/spread kriterleri daha sıkı hale getirildi; orta güvenli ve hafif hareketli gerçek kişi event’lerinin yanlış silinmesi azaltıldı.
- **MP4 duplicate auto-delete konservatifleştirildi (media)**: Duplicate kaynaklı otomatik event silme artık sadece çok uç duplicate + düşük confidence durumunda çalışır; review için eventlerin korunması artırıldı.

## [4.0.46] - 2026-02-27

### Düzeltmeler

- **Thermal motion gate tavanı adaptif kısıtlandı**: Auto-learned `min_area` artık thermal akışta eşzamanlı kamera yükünde daha düşük üst sınırla çalışır; `min=1800` benzeri runaway eşiğin kısa/uzak kişi geçişlerini kaçırması azaltıldı.
- **Concurrent thermal temporal recovery gevşetildi**: Çoklu aktif kamerada temporal recovery confidence ve gap politikası bir kademe daha toleranslı hale getirildi; suppression probe üstünden gelen kısa person hit’leri event’e dönüşmede daha az elenir.
- **Thermal kalite filtresi çoklu kamera yükünde esnetildi**: Multi-cam sahnede küçük bbox’ların (uzak kişi) kalite kapısından düşme oranı azaltıldı.

## [4.0.45] - 2026-02-27

### Düzeltmeler

- **Eşzamanlı kamera hareketinde kaçırma azaltıldı**: Thermal suppression probe aralığı artık çoklu aktif kamerada adaptif olarak sıklaşıyor; kısa süreli eşzamanlı geçişlerin kaçma riski düşürüldü.
- **Thermal temporal gate adaptif hale getirildi**: Çoklu aktif kamera yükünde temporal gereksinim kontrollü gevşetildi (yalnızca contention durumunda), gerçek kişi geçişlerinde yakalama oranı artırıldı.
- **Thermal recovery eşiği iyileştirildi**: Çoklu kamera hareketinde recovery confidence/motion alan koşulları hafifletilerek tek-kamera davranışı korunurken yoğun sahnede kaçırma azaltıldı.

## [4.0.44] - 2026-02-27

### Düzeltmeler

- **Legacy collage onarımı güçlendirildi**: `collage.jpg` eski AI-style formatta kalmışsa ve event MP4'te frame yoksa, artık event metadata ile continuous recording'den frame çekilip standard collage rebuild denenir.
- **UI'da bozuk collage kalma olasılığı azaltıldı**: "no MP4 frames" durumunda yalnızca skip etmek yerine recording fallback devreye alınır.

## [4.0.43] - 2026-02-27

### Düzeltmeler

- **AI collage ve kullanıcı collage ayrıldı**: AI pre-check artık `collage_ai.jpg` kullanır; kullanıcıya gösterilen `collage.jpg` standard görünümde kalır.
- **Legacy bozuk collage otomatik onarım**: Eski sürümden kalan AI-style `collage.jpg`, `/api/events/{id}/collage` çağrısında MP4'ten otomatik rebuild edilir.
- **HA update görünürlüğü için sürüm bump**: Addon versiyonu `4.0.43` yapıldı (aynı versiyon cache kaynaklı eski image kalmasını önlemek için).

## [4.0.42] - 2026-02-27

### Düzeltmeler

- **Thermal suppression wake-up thrash düzeltildi**: `suppression_wakeup` artık probe interval'ini bypass etmiyor; suppression yalnızca probe'da gerçek detection oluşursa kaldırılıyor. Böylece wake-up görünüp anında tekrar suppress olma döngüsü kesildi.
- **Saha takibi kolaylaştırıldı**: suppression kaldırma logları `suppression_wakeup_confirmed` / `suppression_probe_confirmed` olarak netleştirildi; "aday wake-up" ile "gerçek recover" ayrımı belirgin.

## [4.0.41] - 2026-02-27

### Düzeltmeler

- **Processing kuyruğu hızlandırıldı (fake event erken drop)**: Medya/AI üretimine girmeden önce yüksek duplicate + düşük güven + sabit bbox paterni yakalanırsa phantom event erken siliniyor; ağır MP4/GIF/AI işlemleri boşuna çalıştırılmıyor.
- **Events ekranı bekleme durumu güncellendi**: Son 3 dakikadaki medya-bekleyen eventler için liste otomatik 5s poll ile yenileniyor; `processing` durumları manuel refresh beklemeden güncelleniyor.
- **Amaç**: Fake event yoğunluğunda medya kuyruğu birikmesini azaltmak ve gerçek alarm akışını hızlandırmak.

## [4.0.40] - 2026-02-27

### Düzeltmeler

- **Startup readiness warning gürültüsü azaltıldı**: DB/MQTT hazır, sadece go2rtc geç kalıyorsa timeout mesajı `warning` yerine `info` olarak yazılıyor.
- **Phantom event log seviyesi iyileştirildi**: MP4 duplicate quality-gate ile silinen phantom eventler `warning` yerine `info` olarak raporlanıyor.
- **Delayed MP4 replace hata spam'i giderildi**: Phantom event silindikten sonra medya dizini yoksa gecikmeli extract güvenli şekilde atlanıyor; `No such file or directory` kaynaklı recorder hata gürültüsü kesildi.

## [4.0.39] - 2026-02-27

### Düzeltmeler

- **Thermal suppression kaçırma riski azaltıldı**: Suppression sırasında sadece ani area sıçramasına bağlı kalınmıyor; kademeli büyüme de erken wake-up sayılıyor ve periyodik probe inference ile gerçek insan girişleri suppression penceresinde kaçmıyor.
- **Thermal temporal recovery güçlendirildi**: Threading ve multiprocessing worker'da yüksek güven + yeterli motion area şartında tek-frame thermal recovery açıldı; kısa dropout'larda gereksiz event kaçırma azaltıldı.
- **Collage frame seçimi AI için iyileştirildi**: Seçim algoritması zaman yakınlığı + keskinlik + detection confidence skoruna taşındı; event merkez frame collage'a garanti dahil ediliyor.
- **Preset + ayar sadeleştirme**: Performance presetleri artık thermal suppression ve thermal preprocessing detaylarını da set ediyor; ayrıca Kamera Ayarları'na "Thermal Quick Profiles" ve "Expert controls" eklendi.

## [4.0.38] - 2026-02-27

### Düzeltmeler

- **Temporal consistency geri alındı**: 5→3 frame, gap 0→1. Gerçek insanlar termal'de 5 ardışık frame tutarlı görünemeyebilir, 3 frame yeterli.
- **No-detection grace geri alındı**: 0→2. Termal'de kısa YOLO dropout'ları normal, 2 frame tolerans gerekli.
- **Suppression wakeup hassaslaştırıldı**: Minimum area 5000→3000. Gerçek insan daha kolay suppression'ı kaldırır.
- **MP4 duplicate gate korundu** (v4.0.37): Fake event'ler MP4 aşamasında yakalanıp silinir.

## [4.0.37] - 2026-02-27

### Düzeltmeler

- **MP4 quality gate ile phantom event silme**: MP4 duplicate oranı %85+ ise event DB'den silinir, medya dosyaları temizlenir, Telegram bildirimi GÖNDERİLMEZ. Sistem zaten fake olduğunu biliyordu ama yine de bildirim gönderiyordu — artık göndermez.

## [4.0.36] - 2026-02-26

### Düzeltmeler

- **Termal temporal consistency sıkılaştırıldı**: 3→5 ardışık frame gerekli, gap toleransı 1→0. Termal gürültünün 2-3 frame'de aynı blob'u görmesi artık event oluşturmaz.
- **Termal no-detection grace kaldırıldı**: Boş frame toleransı 2→0. Termal'de YOLO bulamazsa hemen pipeline kesilir, color'da 2 frame grace korunur.
- **Phantom event temizliği**: Media buffer'da bbox yoksa event DB'den tamamen silinir (eskiden "rejected" olarak kalıyordu). Collage'sız hayalet event'ler artık hiç görünmez.

## [4.0.35] - 2026-02-26

### Düzeltmeler

- **Suppression artık kalıcı**: Motion idle→active geçişi streak'i sıfırlamıyor. Streak sadece YOLO gerçekten bir şey bulduğunda sıfırlanıyor. Kamera bir kez suppressed olduktan sonra, termal gürültü motion'ı tekrar tetiklese bile YOLO çalışmıyor — 30s boyunca tam sessizlik.

## [4.0.34] - 2026-02-26

### İyileştirmeler

- **Termal inference suppression ayarları UI'a eklendi**: Kamera Ayarları → Hareket bölümünde yeni "Termal Inference Bastırma" paneli. Tüm parametreler (streak, süre, uyanma çarpanı) arayüzden ayarlanabilir.
- **Config modeline 4 yeni alan**: `thermal_suppression_enabled`, `thermal_suppression_streak`, `thermal_suppression_duration`, `thermal_suppression_wakeup_ratio`
- **TR/EN çevirileri eklendi**

## [4.0.33] - 2026-02-26

### İyileştirmeler

- **Termal inference suppression**: YOLO art arda 15 kez boş sonuç döndürürse (`raw=0`), inference 30 saniye duraklatılır. Motion alanı belirgin şekilde artarsa (2.5x + >5000 area) suppression erken kalkar. Termal gürültüde gereksiz YOLO çalışmasını ~%70 azaltır, CPU tasarrufu sağlar.

## [4.0.32] - 2026-02-25

### Düzeltmeler

- **Termal kameralarda fallback zinciri tamamen kaldırıldı**: Relaxed, plain ve highres fallback'ler termal'de sadece false positive üretiyordu. Artık termal kameralar yalnızca kullanıcının ayarladığı `thermal_confidence_threshold` ile çalışıyor — bulamazsa bulmamış demek.
- **Quality floor = confidence_threshold**: Termal tespit quality floor'u artık threshold'un kendisi. Alt threshold'lu tespit quality filter'ı geçemiyor.
- **Color kameralarda fallback korundu**: Relaxed retry sadece color/dual kameraları etkiliyor.

## [4.0.31] - 2026-02-25

### Düzeltmeler

- **Fallback threshold sıkılaştırıldı**: Relaxed threshold `conf - 0.10` → `conf - 0.05`, fallback floor `conf * 0.65` → `conf * 0.80`. Thermal'de 0.40-0.45 arası false positive'ler artık geçemiyor.
- **Quality floor yükseltildi**: `conf * 0.75` → `conf * 0.85`. Örn. conf=0.50 için floor 0.38 → 0.43 oldu.

## [4.0.30] - 2026-02-25

### Düzeltmeler (Bug Fixes)

- **Termal false alarm sorunu çözüldü**: Kullanıcının ayarladığı `thermal_confidence_threshold` değeri yanlış `min/max` formülüyle eziliyordu (ör. 0.55 → 0.30'a düşürülüyordu). Artık kullanıcı ayarı doğrudan kullanılıyor.
- **Quality floor artık dinamik**: Sabit 0.26 yerine `confidence_threshold * 0.75` olarak hesaplanıyor; düşük güvenilirlikli hayalet tespitler pipeline'a giremiyor.
- **Fallback zinciri sadeleştirildi**: `thermal_raw_fallback` (0.20 sabit) ve `thermal_pseudocolor_fallback` kaldırıldı — termal kameralarda çok fazla false positive üretiyorlardı. Kalan fallback'ler `confidence_threshold * 0.65` tabanını kullanıyor.
- **Multiprocessing worker aynı düzeltmeler**: Threading ve multiprocessing detector worker'ları aynı threshold/fallback mantığını kullanıyor.

### Kod Kalitesi (Code Quality)

- **Deadlock riski giderildi**: `_reset_motion_buffers` metodunda frame ve video lock'ları tutarlı sırayla alınarak olası deadlock önlendi.
- **Memory leak düzeltildi**: Kamera silindiğinde `ffmpeg_frame_shapes` ve `ffmpeg_last_errors` dict'leri temizlenmiyor olması düzeltildi.
- **detector_worker global reassign düzeltildi**: Multiprocessing moduna geçişte router'ların eski threading worker'ı görmesi sorunu `deps.detector_worker` üzerinden çözüldü.
- **Bare `except:` → `except Exception:`**: 5 yerde `KeyboardInterrupt`/`SystemExit` yutulması engellendi.
- **`_AsyncRunner` lazy init**: Multiprocessing modülü import edildiğinde gereksiz event loop thread'i başlatılması önlendi.
- **WebSocket ping interval leak**: Component unmount'ta ping interval'in temizlenmeme edge case'i düzeltildi.
- **Relative path → absolute path**: `go2rtc.yaml`, `logs/app.log` için `paths.py`'deki `BASE_DIR`/`LOGS_DIR` kullanıldı.
- **Pydantic validator iyileştirmesi**: `aspect_ratio_max` validasyonu `field_validator`'dan `model_validator`'a taşındı (field sırasına bağımlılık kaldırıldı).
- **SQLAlchemy migration pattern**: `engine.connect()` + manual `commit()` → `engine.begin()` ile proper transaction management.

## [4.0.29] - 2026-02-24

### Düzeltmeler

- AI kararına göre bildirim/otomasyon akışı tek noktadan güvenli hale getirildi: `rejected_by_ai=true` olan event’lerde Telegram bildirimi ve AI-confirmed akışları kesin olarak bastırılıyor.
- AI metinlerinde pozitif/negatif ifadeler karışık geldiğinde (çelişkili yanıt) güvenli davranış uygulanıyor; event onayı yerine reject tercih edilerek fake alarm riski azaltılıyor.
- Event medya üretimi sonrası publish/notify adımlarında AI onay kontrolü merkezi yardımcı fonksiyon üzerinden yapılıyor; farklı kod yollarındaki tutarsızlıklar giderildi.

## [4.0.28] - 2026-02-24

### Düzeltmeler

- Thermal pipeline’da `raw=1` iken `ar=0`/`zone=0` görünmesinin gerçek nedenini ayırmak için `DETECT_PIPELINE` logu genişletildi: `ar` sonrası (`ar`), kalite sonrası (`qual`) ve zone sonrası (`zone`) ayrı raporlanıyor; ayrıca thermal kalite filtre drop sayıları loglanıyor.
- Thermal bbox kalite filtre eşikleri daha gerçekçi hale getirildi (özellikle düşük `conf` ile gelen fallback recoveries gereksiz yere elenmesin diye).
- Aspect-ratio filtresi içinde bbox koordinatları normalize edildi (ters bbox durumunda `width/height` negatif olup yanlış elenmesin).

## [4.0.27] - 2026-02-24

### Düzeltmeler

- Thermal person tespitinde aspect-ratio filtresi genişletildi (`0.08-2.50`): thermal’da modelin ürettiği daha “blob” bbox’lar `ar=0` ile tamamen elenmesin.
- Fake alarm riskini artırmamak için mevcut thermal bbox kalite filtresi + daha sıkı temporal gate aynen korunuyor; sadece AR yüzünden gereksiz drop azaltıldı.
- Threading ve multiprocessing worker yollarında aynı davranış uygulanmıştır.

## [4.0.26] - 2026-02-24

### Düzeltmeler

- Person filtresi sağlamlaştırıldı: `class_id=0` (COCO person) artık `names` metadata hatalı olsa bile her durumda person kabul ediliyor.
- Bu özellikle OpenVINO/export senaryolarında `names_map` kayması yüzünden `person` kutularının “traffic light/car” gibi görünen etiketlerle elenip `DETECT_PIPELINE raw=0` üretmesini engeller.

## [4.0.25] - 2026-02-24

### Düzeltmeler

- Thermal `class_agnostic_diag` adımı tamamen kaldırıldı; `car/traffic light/train` gibi yanlış sınıf tanı log spam’i ve gereksiz ek inference yükü azaltıldı.
- Thermal motion gate’e histerezis eklendi (`active` ve `idle` için ayrı eşik); sınır değerde `active ↔ idle` zıplaması azaltıldı.
- Bu sayede loglar daha temiz, motion kararı daha stabil hale getirildi; OpenVINO ortamında gereksiz fallback gürültüsü de dolaylı olarak düştü.

## [4.0.24] - 2026-02-24

### Düzeltmeler

- Events sayfasında `Confirmed` sekmesi artık yalnızca AI-reject olmayan kayıtları getiriyor; önceki davranışta filtre boş kaldığı için `Rejected` kayıtlar da görünebiliyordu.
- Event kartında `no human`/`Muhtemel yanlış alarm` özetli veya AI-reject kayıtlar için confidence yüzdesi gizlenip `N/A` gösteriliyor; yanlış yönlendiren yüzde görünümü kaldırıldı.
- Bu sayede listede “insan tespit edilmedi” özetiyle birlikte yüzde confidence görünme tutarsızlığı giderildi.

## [4.0.23] - 2026-02-24

### Düzeltmeler

- Thermal event zincirine bbox kalite filtresi eklendi: düşük güven (`conf`), çok küçük alan oranı ve çok kısa bbox yüksekliği olan adaylar event öncesi eleniyor.
- Thermal için temporal tutarlılık şartı sıkılaştırıldı (`3 frame`, `max gap=1`) ve tek-kare yüksek güvenli `temporal_recovered` bypass’ı thermal path’te kapatıldı.
- Amaç: özellikle sabit sahnede ve parazitli ısı bloblarında fake person event üretimini düşürmek; color kamera davranışı korunmuştur.

## [4.0.22] - 2026-02-24

### Düzeltmeler

- `4.0.21` ile gelen thermal `class_agnostic_recovery` adımının fake alarm üretmesine neden olan candidate-promote davranışı geri çekildi.
- Class-agnostic adım artık yalnızca tanı amaçlı çalışıyor (`class_agnostic_diag`): sınıf dağılımını logluyor fakat event zincirine detection enjekte etmiyor.
- Böylece thermal `raw=0` kök neden analizi korunurken sahte kişi event spam’i engellendi.

## [4.0.21] - 2026-02-24

### Düzeltmeler

- Thermal `raw=0` senaryosu için yeni `thermal_pseudocolor_fallback` eklendi (dinamik aralık + colormap), düşük kontrast sahnelerde modelin bbox üretme ihtimali artırıldı.
- Thermal fallback zincirine `class_agnostic_recovery` adımı eklendi; person filtresi öncesi çıkan kutular geçici `person_candidate` olarak AR+zone hattına alınarak class-map kaynaklı kaçırmalar azaltıldı.
- Kök neden teşhisi için fallback sonu loglarına sınıf dağılım özeti eklendi (`class_diag`), modelin obje görüp görmediği sahada daha net ayrıştırılabilir hale getirildi.
- Aynı recovery/diagnostic zinciri hem threading hem multiprocessing worker modlarında eşitlendi.

## [4.0.20] - 2026-02-24

### Düzeltmeler

- Thermal auto-motion modunda `min_area` tabanının ezilmesi giderildi; thermal floor artık auto öğrenme sonrası da zorunlu uygulanıyor.
- Thermal motion gate warmup üst seviyede enforce edilerek başlangıçta erken active geçişleri daha sıkı bastırıldı.
- Thermal detection için ek `thermal_raw_fallback` eklendi (ham frame + düşük conf), enhancer kaynaklı kör noktalarda ek kurtarma adımı sağlandı.
- Thermal başlangıç confidence aralığı daha agresif kurtarma için güncellendi (varsayılan cap 0.30).

## [4.0.19] - 2026-02-24

### Düzeltmeler

- Thermal motion gate sertleştirildi: warmup süresi eklendi (varsayılan 25s), erken false-active tetiklemeleri azaltıldı.
- Thermal min area için güvenli taban eklendi (`thermal_min_area_floor`, varsayılan 260).
- Thermal persistence güçlendirildi (varsayılan pencere 4, gerekli pozitif 3) ve küçük blob etkisi azaltıldı.
- NUC hold süresi artırıldı (varsayılan 2.0s) ve thermal sahnede ani global değişimlerden sonra kısa süreli yanlış tetikler bastırıldı.

## [4.0.18] - 2026-02-24

### Düzeltmeler

- Thermal detection başlangıç confidence eşiği güvenli aralığa çekildi (0.25-0.38), `conf=0.50` kilitlenmesi giderildi.
- OpenVINO ortamında thermal fallback debug log spam’i azaltıldı (10s throttling).
- `fallback_exhausted` ve `thermal_highres_fallback skipped` satırları artık logu boğmayacak şekilde sınırlı yazdırılıyor.

## [4.0.17] - 2026-02-24

### Düzeltmeler

- OpenVINO backend ile thermal high-resolution fallback (832x832) çakışması giderildi.
- OpenVINO aktifken `thermal_highres_fallback` güvenli şekilde atlanıyor; inference loop çökmesi engellendi.
- Thread/process dedektör yollarında aynı koruma uygulanarak kamera thread restart döngüsü kesildi.

## [4.0.16] - 2026-02-23

### Düzeltmeler

- Thermal kameralar için motion pipeline ayrıştırıldı: global-mean compensation + kontrollü IIR background + adaptif eşikleme (k1/k2).
- Thermal motion kararına 2/3 temporal persistence ve morphology + connected-components tabanlı blob toplama eklendi.
- Thermal NUC/reset benzeri ani global sıçramalarda kısa süreli motion gate hold (varsayılan ~1.5s) eklendi.
- Color kamera akışı korunarak sadece thermal motion stratejisi değiştirildi.

## [4.0.15] - 2026-02-23

### Düzeltmeler

- Inference person filtresi model sınıf etiketine göre dayanıklı hale getirildi (sadece `class_id=0` varsayımına bağımlılık azaltıldı).
- Tek sınıflı person modellerde class-id sapması olsa da tespitin düşmemesi için single-class fallback eklendi.
- Bu sayede `DETECT_PIPELINE raw=0` paternindeki model-sınıf eşleme kaynaklı kaçırmalar azaltıldı.

## [4.0.14] - 2026-02-23

### Düzeltmeler

- `ffprobe` çözünürlük tespitinde RTSP transport ayarı stream config ile hizalandı (`-rtsp_transport tcp/udp`).
- `ffprobe` çıktısı dayanıklı parse edilecek şekilde güncellendi; tanı satırları (ör. `461 Unsupported transport`) yüzünden `int()` parse hatası engellendi.
- Başlangıç loglarında gereksiz `ffprobe failed ... invalid literal ...` gürültüsü azaltıldı.

## [4.0.13] - 2026-02-23

### Düzeltmeler

- Thermal sahnelerde `count=0` kaçırmalarını azaltmak için yüksek çözünürlükte ek inference fallback eklendi (`thermal_highres_fallback`, 832x832).
- Tüm fallback katmanları başarısız olduğunda net tanı için `fallback_exhausted` logu eklendi.
- Thermal kaçırma zinciri (relaxed/plain/highres) threading ve multiprocessing modlarında eşitlendi.

## [4.0.12] - 2026-02-23

### Düzeltmeler

- AI çıktısı kişi adedi uydurmasını engellemek için prompt ve sonuç guardrail'leri sertleştirildi (çıktı `insan tespit edildi/edilmedi` formatına sabitlendi).
- MP4 quality gate başarısız olsa bile var olan event MP4'ünün silinmemesi sağlandı (collage var ama MP4 yok durumu azaltıldı).
- Kısa dedektör dalgalanmaları için `no_detections_grace` ve tek-kare güvenli toparlama için `temporal_recovered` akışı eklendi.
- Thermal/person kaçırmalarını azaltmak için motion aktifken `count=0` durumunda ikinci kademe inference fallback eklendi (`relaxed_threshold`).
- Thermal akışta güçlendirme kaynaklı kaçırmaları yakalamak için enhancement kapalı alternatif preprocess fallback eklendi (`thermal_plain_fallback`).
- Aspect ratio filtresinin thermal bbox'ları fazla elemesi durumuna geniş aralık fallback eklendi (`thermal_ar_fallback`).
- Kök neden analizi için detector pipeline kırılım logları eklendi (`DETECT_PIPELINE raw/ar/zone/raw_best_conf`).
- Aynı iyileştirmeler threading ve multiprocessing worker modlarında paralel olarak uygulandı.

## [4.0.11] - 2026-02-22

### Düzeltmeler

- CI backend test hattı stabilize edildi (`pytest-asyncio` eklendi, test çalıştırma komutu iyileştirildi).
- `LogsService.get_logs()` tail sırası/boş satır davranışı düzeltildi; log testleri ve API çıktısı tutarlı hale geldi.
- Telegram bildirim akışında erken dönüşlerde oluşan `UnboundLocalError` giderildi (`bot` cleanup güvenli hale getirildi).
- Settings testleri güncel product defaultlarıyla hizalandı; eski sabit beklenti kaynaklı kırılmalar kaldırıldı.

## [4.0.10] - 2026-02-22

### Düzeltmeler

- Settings ekranındaki `Reset Defaults` akışı sayfa-bazlı hale getirildi; global reset çağrısı kaldırıldı.
- Ayarlar ekranına ikinci onaylı `Factory Default (Full Reset)` butonu eklendi (`FACTORY` yazma onayı).
- Detection/Performance presetlerinin `event` ayarlarını istemeden ezmesi engellendi.
- İnsan tespiti yokken sahte collage/media üretimini kesen koruma her iki worker moduna da eklendi.
- Kısa geçişlerde kaçırmayı azaltmak için temporal consistency ayarı `2/2` olarak güncellendi.

## [4.0.9] - 2026-02-22

### Düzeltmeler

- Collage event vurgusunda tam-kare mavi çerçeve kaldırıldı; işaretleme yalnızca kişi bbox alanına çekildi.
- `min_event_duration` kullanıcı kontrolüne geri alındı; zorunlu `1.5s` clamp kaldırıldı.
- Event cooldown varsayılanı `60s` olarak güncellendi; kullanıcı değişikliği korunur.
- Settings update akışında kullanıcı ayarlarını ezen sanitize kuralları kaldırıldı; yalnızca eksik/geçersiz alanlar normalize edilir.
- Save sırasında `***REDACTED***` değerlerinin gerçek secret üzerine yazılmasını engelleyen koruma eklendi.

## [4.0.8] - 2026-02-22

### Düzeltmeler

- Threading detector için `stream_stale` gate debounce eklendi; anlık spike'larda yanlış stale tetiklemesi azaltıldı.
- Reconnect döngüsüne cooldown eklendi; kısa sürede art arda reconnect engellendi.
- Geçici toparlanma reconnect logları `warning` yerine `info` seviyesine çekildi.

## [4.0.7] - 2026-02-22

### Düzeltmeler

- Auto motion eşikleme yeniden ayarlandı; `min_area` değerinin sık sık tavana (`2500`) vurması azaltıldı.
- Ürün varsayılanları güncellendi: `auto_multiplier=1.0`, `auto_min_area_ceiling=1800`.
- Threading modda `stream_stale` gate daha toleranslı hale getirildi; kısa frame gecikmelerinde gereksiz reconnect azaltıldı.

## [4.0.6] - 2026-02-22

### Düzeltmeler

- Threading detector başlangıcında görülen `Camera ... is not bound to a Session` hatası giderildi.
- Kamera ORM nesneleri thread başlatmadan önce güvenli snapshot nesnelerine çevrildi.
- Başlangıçta detection loop'un kamera bazında düşmesi engellendi; threading modda stabilite artırıldı.

## [4.0.5] - 2026-02-22

### İyileştirmeler

- Product varsayılanları stabilize edildi: motion her zaman global auto modunda çalışır.
- False alarm azaltımı için `auto_profile=low`, `sensitivity=4`, `cooldown=3`, `auto_min_area_floor>=120` politikası sabitlendi.
- UI tarafında manual motion modu kapatıldı; üretim davranışı tek ve tutarlı hale getirildi.

## [4.0.4] - 2026-02-21

### İyileştirmeler

- AI onay akışı hızlandırıldı: Collage analizi sonrası AI onay verirse MQTT bildirimi video beklemeden hemen yayınlanır.
- MP4 üretimi arka planda devam eder; event bildirimi medya üretimi nedeniyle gecikmez.
- `postbuffer_seconds` ürün politikası olarak `2.0s` sabitlendi ve UI'dan kaldırıldı.

## [3.10.97] - 2026-02-20

### Düzeltmeler (Bug Fix Sprint)

- **K-1:** SQLite WAL modu + foreign key enforcement her bağlantıda etkin
- **K-2:** Settings `deepcopy` düzeltmesi — migration'lar artık diske yazılıyor
- **K-3:** Paylaşımlı frame buffer yazmaları `mp.Lock` ile korunuyor
- **K-4:** Çöken kamera process 5 saniye sonra otomatik yeniden başlatılıyor
- **Y-1/Y-2:** Recorder zombie fix (`wait` sonrası `kill`) + process dict thread-safe
- **Y-3:** go2rtc YAML config yazmaları atomik (tmp→rename) + lock korumalı
- **Y-4:** Çift MQTT reconnect mekanizması devre dışı (paho + manual thread çakışması)
- **Y-5:** `rejected_only=None` artık event filtrelemiyor (tümü gösteriliyor)
- **Y-6:** cameras/status N+1 sorgusu tek GROUP BY aggregate ile değiştirildi
- **Y-7:** Video seeking — Range:bytes header'ı 206 Partial Content döndürüyor
- **Y-8:** `main.py` `detector_worker` `UnboundLocalError` riski giderildi
- **Y-9:** `stop()` shared memory serbest bırakmadan önce event_handler_thread'i join ediyor
- **Y-10:** `useWebSocket` callback'leri ref'lerde saklanıyor — parent re-render'da reconnect yok
- **O-1:** `video_analyzer` `VideoCapture` try/finally ile sarıldı
- **D-1–D-16:** i18n, locale, confirm dialog, auto-save, localStorage quota, datetime.utcnow düzeltmeleri

## [3.10.75] - 2026-02-19

### Düzeltmeler

- **AI bağımsız analiz (kutu yok):** AI collage'ına bounding box çizilmemesi sağlandı.

## [3.10.74] - 2026-02-19

### Düzeltmeler

- **AI yanlış onay sorunu:** Prompt'a YOLO güven skoru ekleniyor; dinamik prompt oluşturma.

## [3.10.73] - 2026-02-19

### İyileştirmeler

- **Kritik: Paralel event işleme (detector_mp):** Her detection eventi kendi Thread'inde işleniyor.

## [3.10.72] - 2026-02-19

### Teknik İyileştirmeler (Refactor)

- **`app/main.py` bölündü:** 2566 satırlık god file, 6 ayrı router dosyasına ayrıldı.
- **`app/dependencies.py` oluşturuldu:** Tüm servis singleton'ları tek yerden yönetilir.
- **AI onay string'leri merkezi hale getirildi:** `app/services/ai_constants.py`'e taşındı.
- **`_get_go2rtc_restream_url` tekrarı kaldırıldı:** `Go2RTCService.build_restream_url()` metodunda birleştirildi.
- **`ai_test.py` → `ai_probe.py`:** Servis klasöründeki yanıltıcı isim düzeltildi.
- **`postbuffer_seconds` sanitizer override sorunu:** Sanitizer eşiği 15→3'e düşürüldü.

---

## [3.10.71] - 2026-02-19

### Düzeltmeler

- **Kritik: Boş video sorunu (recorder):** FFmpeg `returncode == 0` döndürmesi dosyanın oynatılabilir olduğunu garanti etmiyor. Kayıt segmentinde tam o zaman aralığında boşluk varsa FFmpeg geçerli MP4 container'ı ama 0 frame ile yazıyordu (< 4KB). Bu boş dosya `os.replace()` ile buffer MP4'ün üzerine yazılıyordu — AI onaylı event'te bile siyah video görülmesinin nedeni buydu. `_extract_single` ve `_extract_multi` fonksiyonlarına 4KB minimum boyut kontrolü eklendi; boyut altında kalırsa mevcut buffer MP4 korunuyor.
- **UI: Bozuk video hata mesajı:** Video oynatıcı bozuk/boş dosyayı yüklemeye çalışırken tarayıcının cryptic "no source" ikonunu göstermek yerine artık "noData" mesajı gösteriliyor (`onError` handler eklendi).

## [3.10.70] - 2026-02-19

### Düzeltmeler

- **Kritik: Kamera bağlantı kopması engellendi (MP modu):** `detector_mp.py` ana döngüsünde `cap.read()` artık FPS throttle'dan **önce** çalışır. Önceden sistem inference_fps (5fps) arasında `time.sleep(0.01)` ile bekliyordu; bu sürede go2rtc frame buffer'ı dolup "reader too slow" hatası vererek bağlantıyı kesiyordu. Artık her frame stream'den tüketilir (Scrypted/NVR yaklaşımı), inference FPS'i sadece YOLO çalıştırma sıklığını belirler. Ek olarak `frame_buffer` yazımı da FPS throttle'dan bağımsız çalışarak `record_fps` (10fps) hızında buffer doldurur.

## [3.10.69] - 2026-02-19

### İyileştirmeler

- **`postbuffer_seconds` varsayılanı:** 15 → 5 saniye. Kayıt her zaman açık olduğundan olay videosu kayıt dosyasından çıkarılır; frame buffer'ın uzun süre dolmasını beklemek gereksizdi. AI onaylı Telegram bildirimi gecikmesi ~25-45 saniyeden ~12-15 saniyeye düşer.

## [3.10.68] - 2026-02-19

### Düzeltmeler

- **Kritik: Video kaybı engellendi:** `_extract_single` ve `_extract_multi` artık FFmpeg çıktısını geçici dosyaya yazar; yalnızca başarı durumunda `os.replace()` ile hedef dosyanın üzerine atomik yazar. Böylece geç gelen kayıt çıkarma denemesi başarısız olsa da mevcut buffer MP4 bozulmadan korunur. Bu hata hem UI'da hem Telegram'da video görünmemesinin ana nedeni idi.

## [3.10.67] - 2026-02-18

### Düzeltmeler

- **Telegram video:** `.legacy` MP4'ler artık engellenmez; gönderimde hata olursa `send_document` fallback + log eklendi.
- **Motion presetleri:** Eco/Balanced/Frigate/Quality ayarları güncellendi; varsayılan artık Balanced.
- **Motion global ayar:** Kamera custom yoksa global motion ayarı uygulanır (eski default override engellendi).
- **MP reconnect:** Multiprocessing modunda read failure sonrası go2rtc stream yeniden açılır.

## [3.10.66] - 2026-02-18

### Düzeltmeler

- **Live View:** Uzayan yüklemede snapshot fallback devreye girer.

## [3.10.65] - 2026-02-18

### Düzeltmeler

- **Collage bbox:** MP modda kutu koordinatları buffer boyutuna ölçeklenir.

## [3.10.64] - 2026-02-18

### Düzeltmeler

- **Telegram video:** Video gönderimi hata verirse dosya olarak fallback.
- **Telegram log:** Video gönderim denemeleri loglanır.

## [3.10.63] - 2026-02-18

### Düzeltmeler

- **Telegram video:** `.legacy` MP4'ler artık Telegram’a gönderilir.

## [3.10.62] - 2026-02-18

### Eklenenler

- **Live Snapshot:** MJPEG çalışmazsa tek kare snapshot fallback.

## [3.10.61] - 2026-02-18

### Düzeltmeler

- **Live View:** go2rtc başarısızsa worker stream tercih edilir.

## [3.10.60] - 2026-02-18

### Düzeltmeler

- **Live View:** Worker frame hazırsa önce worker fallback kullanılır.

## [3.10.59] - 2026-02-18

### Eklenenler

- **Live Log:** Canlı görüntü altında debug bilgisi gösterilir.
- **Live probe:** `/api/live/{id}.mjpeg?probe=1` ile hızlı durum sorgusu.

## [3.10.58] - 2026-02-18

### Düzeltmeler

- **Live View:** go2rtc MJPEG ilk frame gelmezse fallback kullanılır.

## [3.10.57] - 2026-02-18

### Düzeltmeler

- **Backend crash:** Live View fallback type hint için eksik `numpy` import eklendi.

## [3.10.56] - 2026-02-18

### Düzeltmeler

- **Live View (Ingress):** MJPEG response header’ları ile HA ingress buffering/sıkıştırma sorunu azaltıldı.
- **Live View fallback:** go2rtc MJPEG başlamazsa worker frame’lerinden MJPEG yayın.

## [3.10.55] - 2026-02-18

### Düzeltmeler

- **MP motion cooldown:** Hareket algılama, cooldown süresince aktif tutulur (false negative azalır).

## [3.10.54] - 2026-02-17

### Değişenler

- **Preset ayarları:** Eco/Balanced/Frigate/Quality stream + event + motion + detection değerleri netleştirildi.
- **MP motion:** Global motion ayarları MP modda kamera ayarlarına merge edilir.

## [3.10.53] - 2026-02-17

### Eklenenler

- **CI:** GitHub Actions ile backend test + UI lint.
- **Medya sırası kontrolü:** Eşzamanlı medya üretimi sınırlandı (queue logları).

### Değişenler

- **MQTT ayarları:** Auto-save kaldırıldı, tek state + manuel kaydet akışı.
- **Tema tokenları:** UI token eşlemesi (bg-card/foreground/primary vb.).

### Düzeltmeler

- **Live View (Ingress):** MJPEG response header’larına `Content-Encoding: identity` ve `X-Accel-Buffering: no` eklendi; HA ingress sıkıştırma/buffering sorunlarıyla uyum.
- **MP zone filtresi:** Polygon check hatası giderildi.
- **go2rtc retry:** Threading + MP modda go2rtc yoksa sürekli retry + uyarı.
- **Kamera update:** Whitelist ile güvenli update.
- **Events bulk seçimi:** Filtre/sayfa değişince seçim temizlenir.
- **EventDetail:** localStorage parse güvenliği.

## [3.10.52] - 2026-02-17

### Eklenenler

- **Live View fallback:** go2rtc MJPEG erişilemezse worker frame’lerinden MJPEG yayın.
- **Event gate debug:** MP modda min_duration/cooldown/temporal nedenleri için debug logları.
- **Motion filtresi logları:** Motion aktif/idle geçişleri ve alan/eşik bilgisi loglanır (MP + threading).

### Değişenler

- **go2rtc sağlığı:** availability dinamik yenileniyor (restart sonrası otomatik toparlama).
- **Yeni kamera akışı:** go2rtc config güncellemesi detection/recording öncesine alındı; update sonrası detection yeniden başlatılır.
- **RTSP açılışı retry:** go2rtc reload gecikmesine karşı MP detector açılış denemeleri backoff ile sürer.

### Düzeltmeler

- **MP motion cooldown:** hızlı active/idle dalgalanması sonrası event kaçırma azaltıldı.
- **MP zone filtre:** polygon kontrolü ve zone payload aktarımı düzeltildi.
- **Motion log:** efektif min_area eşiği loglanıyor.
- **Gürültülü loglar:** Bazı RTSP ve kamera durumu logları debug seviyesine çekildi.

### Eklenenler

- **Motion filtresi logları:** Motion aktif/idle geçişleri ve alan/eşik bilgisi loglanır (MP + threading).

### Değişenler

- **Yeni kamera akışı:** go2rtc config güncellemesi detection/recording öncesine alındı; update sonrası detection yeniden başlatılır.
- **RTSP açılışı retry:** go2rtc reload gecikmesine karşı MP detector açılış denemeleri backoff ile sürer.

### Düzeltmeler

- **Gürültülü loglar:** Bazı RTSP ve kamera durumu logları debug seviyesine çekildi.
## [3.10.51] - 2026-02-17

### Düzeltmeler

- **Live View:** go2rtc MJPEG başlamazsa go2rtc RTSP restream ile MJPEG üretimi (tek stream desteği).

---

## [3.10.50] - 2026-02-17

### Düzeltmeler

- **Kamera silme:** Kayıt süreci silinen kamerada yeniden başlatılmıyor.
- **MP medya:** Silinen kamera için paylaşılan buffer yoksa medya üretimi temiz şekilde atlanıyor.

---

## [3.10.49] - 2026-02-17

### Düzeltmeler

- **Live View:** Ana stream yoksa go2rtc `*_detect` substream ile canlı görüntü verilir.

---

## [3.10.48] - 2026-02-17

### Düzeltmeler

- **MP kamera durumu:** Multiprocessing modunda kamera status güncellemeleri ve UI göstergeleri düzeltildi.

---

## [3.10.47] - 2026-02-17

### Değişenler

- **Kamera ekleme:** Kullanılmayan ikinci stream (substream) alanı kaldırıldı.

---

## [3.10.46] - 2026-02-17

### Düzeltmeler

- **go2rtc durumu:** Live/detection için erişilebilirlik dinamik kontrol ediliyor; geç açılan go2rtc artık sistemi kilitlemiyor.
- **go2rtc sync:** go2rtc kapalı olsa bile kamera stream config'i yazılıyor; online olduğunda restart ile yükleniyor.

---
## [3.10.45] - 2026-02-16

### Eklenenler

- **Auto backend seçimi:** `auto` artık TensorRT → OpenVINO(GPU) → ONNX → PT sırasıyla dener; seçilen backend loga yazılır.
- **Backend rehberi:** Inference backend seçimi geniş panel + kısa açıklamalarla daha anlaşılır.
- **Preset açıklamaları:** Dengeli ve Güvenilir farkı (stream/event stabilite) netleştirildi.

---

## [3.10.44] - 2026-02-16

### Eklenenler

- **Diagnostics – Worker:** Sistem Tanılama sayfasında Worker kartı (mod: threading/multiprocessing, process sayısı, PIDs). Multiprocessing açık mı kontrol edilebilir.
- **System info:** `/api/system/info` yanıtına `worker` alanı eklendi.

---

## [3.10.43] - 2026-02-16

### Değişenler

- **Live View – tek kamera:** Grid kaldırıldı; tek kamera seçimi + tek yayın. Açılır listeden kamera seçilir, yayın go2rtc üzerinden.
- **Live stream – sadece go2rtc:** Canlı yayın fallback’siz yalnızca go2rtc; go2rtc yoksa net 503 mesajı.

### Düzeltmeler

- **Live View ayarları:** MJPEG kalitesi kaldırıldı; sabit 92 ile kararlı yayın, arayüz sadeleştirildi.
- **Worker modu:** Health ve system info’da worker bilgisi; Ayarlar’da “addon yeniden başlatıldıktan sonra geçerli” notu.

---

## [3.10.42] - 2026-02-16

### Düzeltmeler

- **MP4 .legacy:** OpenCV fallback ile oluşturulan MP4 artık gösteriliyor; .legacy marker mp4_url'yi engellemiyordu (collage var video yok).

---

## [3.10.41] - 2026-02-16

### Düzeltmeler

- **AI collage path:** `str` veya `Path` kabul ediyor; `'str' object has no attribute 'exists'` hatası giderildi.
- **Disk limit varsayılan:** %80 → %85 (HA ortamında daha uygun).

---

## [3.10.40] - 2026-02-16

### Düzeltmeler

- **AI onayı UI:** AI onayladığında `rejected_by_ai = False` açıkça ayarlanıyor; video/event artık "onaysız" görünmüyor.

---

## [3.10.39] - 2026-02-16

### Değişenler

- **Event timestamp:** Frame zamanı (`current_time`) kullanılıyor – `datetime.utcnow()` yerine buffer ile tam uyum.
- **Medya sırası:** Video/collage önce üretiliyor, AI sonra – AI beklemeden zaman tutarlılığı.
- **AI onayı son kapı:** MQTT/WebSocket/Telegram sadece AI onayladığında gönderiliyor; reddederse event UI'da kalıyor.
- **Recorder log:** Segment bulunamadığında search range vs mevcut segment aralığı loglanıyor.

### Düzeltmeler

- **Media UTC:** Local timezone fallback kaldırıldı (FFmpeg TZ=UTC ile tutarsızlık).
- **Event timestamp:** DB'den okunan `event.timestamp` için naive/aware UTC işleme düzeltildi.

---

## [3.10.38] - 2026-02-16

### Düzeltmeler

- **Video oluşturma:** Event timestamp artık detection zamanını kullanıyor (recording extract için doğru aralık).
- **Buffer:** Child process 250 frame kullanıyor (main ile uyumlu).
- **Loglama:** buffer_info eksik, "No frames" ve MP4 hata durumları için diagnostik loglar.

---

## [3.10.37] - 2026-02-16

### Eklenenler

- **Substream (Detection):** `rtsp_url_detection` ile detection için düşük çözünürlüklü substream kullanımı. Kamera formunda "Substream (Detection)" alanı – tanımlanırsa detection bu URL üzerinden yapılır, recording/live main stream'de kalır (~%5 CPU / 10 kamera hedefi).
- **Video fallback:** MP4 oluşturma başarısız olursa ilk frame ile minimal video üretiliyor.
- **extract_frames:** Recording'den frame kurtarma için `max_frames` 5 → 60.

### Düzeltmeler

- **Buffer zaman aralığı:** Tam aralıkta frame yoksa 2x prebuffer/postbuffer ile tekrar deneniyor.
- **Event MP4:** `Accept-Ranges: bytes` header, H.264 baseline profile (tarayıcı uyumluluğu).

---

## [3.10.36] - 2026-02-16

### Değişenler

- **Scrypted-style tek kaynak:** Tüm stream akışı (Live, Detection, Recording) artık sadece go2rtc üzerinden. Fallback yok – go2rtc aktif olmalı.
- **detector_mp:** Sadece go2rtc restream kullanıyor.
- **detector (threading):** Sadece go2rtc restream, direct RTSP kaldırıldı.
- **recorder:** go2rtc restream üzerinden kayıt.
- **Live / Snapshot:** go2rtc restream kullanılıyor.

---

## [3.10.35] - 2026-02-16

### Düzeltmeler

- **Ingress tam destek:** Merkezi `resolveApiPath()` ile tüm API/media URL’leri (collage, MP4, live stream, snapshot) Ingress prefix ile güncelleniyor. EventCard, EventDetail, Dashboard, AITab, EventCompare, StreamViewer, ZonesTab tek kaynaktan güncellendi.
- **AI reddeden eventler:** MP4 artık AI reddetse bile üretiliyor; collage + video "AI Reddedilenler" sekmesinde görüntülenebilir.
- **Event video oynatma:** OpenCV fallback MP4’ler için faststart remux eklendi; tarayıcıda siyah ekran azaltıldı.
- **EventDetail MP4 polling:** MP4 henüz hazır değilse (son 60 sn) 3 sn aralıkla API’den güncelleme alınıyor.

### Değişenler

- **Nginx:** API location için `proxy_request_buffering off` eklendi (video streaming için).

---

## [3.10.23] - 2026-02-10

### Değişenler

- **Event video buffer FPS:** SharedFrameBuffer artık `record_fps` (varsayılan 10) kullanıyor; önceden sabit 5 FPS vardı. Ayarlar → Events → Frame rate ile 1–30 arası ayarlanabilir; daha akıcı timelapse için 15–20 önerilir.

### Eklenenler

- **docs/VIDEO_QUALITY_ANALYSIS.md:** Event video kalite değişkenliği analizi ve iyileştirme önerileri.

---

## [3.10.22] - 2026-02-10

### Düzeltmeler

- **go2rtc buffer tutarlılığı:** detector_mp artık `config.stream.buffer_size` kullanıyor; önceden sabit 3 vardı.
- **go2rtc "reader is too slow" dokümantasyonu:** `docs/GO2RTC_SLOW_READER.md` güncellendi – buffer değerleri, performans etkisi ve tavsiyeler (substream, direct RTSP, log seviyesi, kamera FPS) eklendi.

---

## [3.10.21] - 2026-02-14

### Düzeltmeler

- **go2rtc Live View:** Ingress üzerinden /live sayfasındayken go2rtc URL'si yanlış base path kullanıyordu (…/live/go2rtc → 404). Artık Ingress base doğru çıkarılıyor.
- **go2rtc WebRTC modu:** WebRTC seçiliyken backend stream_url döndürmüyordu; MJPEG fallback URL'si eksikti. Artık webrtc modunda da stream_url üretiliyor.

---

## [3.10.20] - 2026-02-14

### Eklenenler

- **Telegram video_speed:** Ayarlardan event video hızı (web + Telegram için tek video) artık yönetiliyor.
- **Telegram max_messages_per_min:** Dakika başı mesaj limiti backend'de uygulanıyor.
- **Telegram ayar açıklamaları:** Video hızı, cooldown, rate limit için TR/EN açıklamalar eklendi.
- **Appearance:** Dil değişikliği backend config'e kaydediliyor.

### Değişenler

- **Kamera Ayarları:** 3 kolonlu gruplu layout, collapse "Gelişmiş" bölümler, kısa algoritma ipuçları.
- **Ayarlar sadeleştirme:** Kullanılmayan DetectionTab, MotionTab, ThermalTab, StreamTab kaldırıldı; enable_tracking UI'dan çıkarıldı.
- **SettingsTabs:** Tekrarlayan performance tab kaldırıldı.

### Düzeltmeler

- **API audit:** Tüm uçlar ve ayar tab'ları kontrol edildi; `docs/API_AUDIT.md` eklendi.

---

## [3.10.19] - 2026-02-14

### Düzeltmeler

- **WebSocket:** Ping 15 sn, reconnect 2 sn, sınırsız deneme – bağlantı kopması azaltıldı.

---

## [3.10.18] - 2026-02-14

### Düzeltmeler

- **Port:** RTSP host port 19854'e alındı (8554/8555 çakışma önlendi).

---

## [3.10.17] - 2026-02-14

### Düzeltmeler

- **Port 8554:** RTSP host port 8555'e alındı (çakışma önlendi).

---

## [3.10.16] - 2026-02-14

### Düzeltmeler

- **Port:** go2rtc port formatı düzeltildi (container 1984 → host 1985).

---

## [3.10.15] - 2026-02-14

### Düzeltmeler

- Root yapı geri yüklendi (dockerfile missing hatası giderildi).
- Port 1985, migration fix, stream_roles tüm iyileştirmeler dahil.

---

## [3.10.14] - 2026-02-14

### Düzeltmeler

- **Port 1984:** go2rtc host port 1985'e alındı (başka uygulama 1984 kullanıyorsa çakışma önlenir).

---

## [3.10.13] - 2026-02-10

### Düzeltmeler

- **Başlangıç:** run.sh migration app import kaldırıldı, standalone script kullanılıyor; addon açılışta çökmesi düzeltildi.

---

## [3.10.12] - 2026-02-10

### Düzeltmeler

- **Algılama:** Boş `stream_roles` olan kameralar artık algılanıyor (geriye dönük uyum).

---

## [3.10.11] - 2026-02-10

### Değişenler

- **Versiyon:** Tek kaynak config.yaml; uygulama versiyonu otomatik oradan okunuyor.

---

## [3.10.10] - 2026-02-10

### Düzeltmeler

- **MP4 hızlandırma:** MP4_MIN_OUTPUT_DURATION 20→3, MP4_SPEED_FACTOR 3→4; 20 sn içerik ~5 sn MP4 olarak çıkıyor.
- **Tek versiyon kaynağı:** Tüm uygulama (API health, system info, MQTT) `app/version.py` üzerinden tek parametreden versiyon alıyor.

---

## [2.5.9] - 2026-02-10

### Düzeltmeler

- **Hareket tespiti:** Migration gevşetildi – confidence 0.30, thermal 0.35, cooldown 7sn, min_event_duration 1sn. Varsayılanlar ve 4 Performance preset güncellendi.

---

## [2.5.8] - 2026-02-10

### Düzeltmeler

- **Live View 502/Loading:** MJPEG artık go2rtc üzerinden sunuluyor; backend RTSP blocking ve timeout kaynaklı 502 hatası giderildi. Ingress go2rtc path düzeltmesi, 502 toast spam azaltıldı.

---

## [2.5.7] - 2026-02-10

### Düzeltmeler

- **AI gate:** AI aktifken video/media yalnızca AI onayından sonra oluşturulur. AI reddederse event ve media silinir; MP4/GIF hiç üretilmez. AI kapalıyken normal akış devam eder (detector.py ve detector_mp.py).

---

## [2.3.0] - 2026-02-11

### Değişenler

- **MP4 fallback:** Kayıt yoksa frame-based MP4 üretiliyor (video her zaman oluşur).
- **Recording tab:** Gereksiz ayarlar kaldırıldı; saklama Medya sekmesinde.

### Düzeltmeler

- Event video "No data" hatası düzeltildi (MP4 fallback geri eklendi).

---

## [2.2.0] - 2026-02-10

### Değişenler

- **Kayıt buffer:** Sürekli kayıt 7 gün yerine sabit 1 saatlik rolling buffer; her kamera son 1 saati tutar, en eskisi üzerine yazılır.
- **Event retention:** Event saklama süresi seçmeli (Sınırsız, 1-365 gün); Medya sekmesinde dropdown.
- **Event MP4:** MP4 yalnızca kaydedilen videodan oluşturulur; frame-based fallback kaldırıldı (frame tekrarı önlendi).

### Düzeltmeler

- `_select_indices` / `_select_indices_by_time`: frame tekrarı engellendi.

---

## [2.1.0] - 2026-02-10

### Eklenenler

- **Zone güncelleme (UI):** Bölge listesinde enable/disable checkbox'ı `PUT /api/zones/{id}` ile bağlandı. `updateZone` API fonksiyonu ve ilgili i18n (zoneEnabled, zoneDisabled, enableZone, disableZone) eklendi.
- **Prometheus metrikleri:** Detector tarafında `record_inference_latency`, `record_event`, `set_fps`, `set_cpu_usage` çağrıları eklendi; metrikler artık dolduruluyor.
- **Sürekli kayıttan event MP4:** Event media üretilirken önce sürekli kayıttan `extract_clip` deneniyor, yoksa frame-based MP4 üretiliyor.
- **CHANGELOG.md:** Bu dosya eklendi.

### Değişenler

- **API uyumu:** `create_camera` → 201 Created, `delete_camera` → 204 No Content. Snapshot RTSP hatası 502, live stream URL yok 409. `get_live_streams` MJPEG değilse `stream_url: null`.
- **Frontend delete_camera:** 204 yanıtında body olmadığı için `{ deleted: true }` döndürülüyor.
- **DB:** RecordingState ↔ Camera için ORM ilişkisi eklendi (one-to-one, back_populates).
- **Event oluşturma:** `create_event` çağrısına `person_count` parametresi eklendi.

### Performans

- **Varsayılan config:** `inference_fps` 5 → 3, `inference_resolution` [640,640] → [480,480] (yeni kurulum / reset).
- **CPU throttling:** CPU > %90 → FPS 1’e kadar, > %80 → 2’ye düşürme; CPU < %40’ta FPS artışı 5’te sınırlandı.
- **Motion:** Hareket hesabı 640px → 480px, GaussianBlur (5,5) → (3,3) (detector + motion servisi).

### Düzeltmeler

- Snapshot endpoint’te `result` null/eksik key güvenliği.
- Return type’lar: `get_live_stream` → StreamingResponse, `get_camera_snapshot` → Response.

---

## [2.0.0] - (önceki sürüm)

- Smart Motion Detector v2: YOLOv8 person detection, termal/renkli kamera, zones, sürekli kayıt (Scrypted-style), AI özeti, Telegram, MQTT, go2rtc entegrasyonu.

---

[2.5.9]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.5.8...v2.5.9
[2.5.8]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.5.7...v2.5.8
[2.5.7]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.5.6...v2.5.7
[2.3.0]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/cataloglu/thermal-dual-vision/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/cataloglu/thermal-dual-vision/releases/tag/v2.0.0
