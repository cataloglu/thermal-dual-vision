# Full Repo Audit TODO Master

Bu dosya yalnızca analiz çıktısıdır. Buradaki hiçbir madde kullanıcı seçimi olmadan uygulanmayacaktır.

## Kullanım

- Kimlik: `A-###`
- Şiddet: `Kritik | Yuksek | Orta | Dusuk`
- Regresyon riski: `Dusuk | Orta | Yuksek`
- Oncelik: `P1 | P2 | P3`
- Durum: `pending | selected | done | skipped`

---

## P1 (Ilk tur onerilenler)

### A-001
- Katman: Backend
- Alan: WebSocket
- Siddet: Kritik
- Regresyon riski: Dusuk
- Oncelik: P1
- Durum: done
- Etki: Guvenilirlik
- Bulgular: `WebSocketManager._run_async()` icinde `self._loop` kullaniliyor ama sinifta hic initialize edilmiyor; non-async contextte AttributeError riski var.
- Kanit: `app/services/websocket.py` (`_run_async`, `if not self._loop ...`)
- Onerilen cozum: Event loop sahipligi tek pattern'e indirilsin (ya tamamen sync-safe queue, ya explicit loop init).

### A-002
- Katman: Backend
- Alan: Zaman damgasi / Python 3.12+
- Siddet: Yuksek
- Regresyon riski: Dusuk
- Oncelik: P1
- Durum: done
- Etki: Bakim / gelecek uyumluluk
- Bulgular: `datetime.utcnow()` kullanimlari devam ediyor.
- Kanit: `app/workers/detector.py`, `app/workers/detector_mp.py`, `app/workers/retention.py`, `app/services/mqtt.py`
- Onerilen cozum: Tum noktalar `datetime.now(timezone.utc).replace(tzinfo=None)` (veya aware datetime stratejisi) ile standartlansin.

### A-003
- Katman: Backend
- Alan: Startup/Lifespan
- Siddet: Yuksek
- Regresyon riski: Orta
- Oncelik: P1
- Durum: done
- Etki: Performans / guvenilirlik
- Bulgular: Startup'ta sabit bekleme var (`10s + 2s`), readiness-check yok.
- Kanit: `app/main.py` (`await asyncio.sleep(10)`, `await asyncio.sleep(2)`)
- Onerilen cozum: Sleep yerine go2rtc/backend/mqtt readiness probe + timeout politikasi.

### A-004
- Katman: Backend
- Alan: Session yonetimi
- Siddet: Yuksek
- Regresyon riski: Orta
- Oncelik: P1
- Durum: done
- Etki: Guvenilirlik
- Bulgular: Worker/service icinde `next(get_session())` ile manuel session pattern'i cok yaygin; hata patikalarinda kacirma riski buyutuyor.
- Kanit: `app/main.py`, `app/workers/detector.py`, `app/workers/detector_mp.py`, `app/workers/retention.py`, `app/services/mqtt.py`
- Onerilen cozum: Tek tip session helper/context manager ile standartlastirma.

### A-005
- Katman: Frontend
- Alan: Events realtime filtreleme
- Siddet: Yuksek
- Regresyon riski: Dusuk
- Oncelik: P1
- Durum: done
- Etki: Fonksiyonel
- Bulgular: WebSocket'ten gelen event prepend'i `showRejected` filtresini dikkate almiyor; yanlis listede event gorunebilir.
- Kanit: `ui/src/pages/Events.tsx` (`handleEventRef.current`, `if (cameraFilter || dateFilter || confidenceFilter > 0) return`)
- Onerilen cozum: Prepend kosuluna aktif filtrelerin tamami (rejected dahil) ve source-compatibility kontrolu eklensin.

### A-006
- Katman: Infra/Release
- Alan: Surum tutarliligi
- Siddet: Yuksek
- Regresyon riski: Dusuk
- Oncelik: P1
- Durum: done
- Etki: Operasyon / release dogrulugu
- Bulgular: Surum numaralari repo icinde drift etmis.
- Kanit: `config.yaml` (`3.10.98`), `ui/package.json` (`3.10.55`), `README.md` (`v3.10.79`)
- Onerilen cozum: Single-source-of-truth version policy + CI drift check.

### A-007
- Katman: Infra/Startup
- Alan: Migration guvenilirligi
- Siddet: Yuksek
- Regresyon riski: Dusuk
- Oncelik: P1
- Durum: done
- Etki: Guvenilirlik
- Bulgular: Migration script hatalari startup'ta bilincli olarak yutuluyor.
- Kanit: `run.sh` (`python3 ... 2>/dev/null || true`)
- Onerilen cozum: Fail-fast veya en azindan structured error log + health degraded flag.

---

## P2 (Ikinci tur onerilenler)

### A-008
- Katman: Frontend
- Alan: WebSocket reconnect
- Siddet: Orta
- Regresyon riski: Orta
- Oncelik: P2
- Durum: done
- Etki: Guvenilirlik
- Bulgular: Yeni `connect()` cagrisi eski socket'i kapatirken eski `onclose` tekrar reconnect planlayabilir; cift reconnect olasiligi var.
- Kanit: `ui/src/hooks/useWebSocket.ts` (`connect`, `ws.onclose`, `setTimeout(() => connect(), reconnectInterval)`)
- Onerilen cozum: Socket instance token/nonce ile stale `onclose` olaylarini ignore et.

### A-009
- Katman: Frontend
- Alan: i18n/locale
- Siddet: Orta
- Regresyon riski: Dusuk
- Oncelik: P2
- Durum: done
- Etki: Fonksiyonel/UX
- Bulgular: Hardcoded locale ve metinler var.
- Kanit: `ui/src/pages/Dashboard.tsx` (`toLocaleString('tr-TR')`, Turkce hardcoded stringler), `ui/src/components/EventCompare.tsx` (`toLocaleString('tr-TR')`), `ui/src/components/Sidebar.tsx` (`MQTT Bilgileri`)
- Onerilen cozum: Tam i18n key coverage + `toLocaleString(undefined, ...)`.

### A-010
- Katman: Frontend
- Alan: VideoAnalysis page
- Siddet: Orta
- Regresyon riski: Dusuk
- Oncelik: P2
- Durum: done
- Etki: Bakim/UX
- Bulgular: Cok sayida `t('key') || 'fallback'` pattern'i var; key drift oldugunda sessizce gizlenir.
- Kanit: `ui/src/pages/VideoAnalysis.tsx`
- Onerilen cozum: Fallback stringleri key setine tasiyip eksik keyleri CI/lint ile yakala.

### A-011
- Katman: Backend
- Alan: MQTT mesaj dil/tarih tutarliligi
- Siddet: Orta
- Regresyon riski: Dusuk
- Oncelik: P2
- Durum: done
- Etki: Operasyon / entegrasyon
- Bulgular: MQTT payloadlarda hem `datetime.utcnow()` hem de dil karisikligi var (`Henüz olay yok`).
- Kanit: `app/services/mqtt.py` (`connected_at`, `_publish_camera_state`, `_track_publish`)
- Onerilen cozum: Dil/format standardi ve UTC strategy teklestirilsin.

### A-012
- Katman: Infra
- Alan: CI kapsam
- Siddet: Orta
- Regresyon riski: Dusuk
- Oncelik: P2
- Durum: done
- Etki: Kalite guvencesi
- Bulgular: CI sadece backend test + UI lint calistiriyor; UI build ve e2e yok.
- Kanit: `.github/workflows/ci.yml`
- Onerilen cozum: `npm run build` ve secili smoke/e2e adimi eklenmeli.

### A-013
- Katman: Test
- Alan: Test gucu
- Siddet: Orta
- Regresyon riski: Dusuk
- Oncelik: P2
- Durum: done
- Etki: Yanlis-negatif test riski
- Bulgular: Zayif assertion mevcut (`assert isinstance(result, bool)`), davranis dogrulugu yerine sadece crash kontrolu yapiyor.
- Kanit: `tests/test_inference_optimized.py`
- Onerilen cozum: Deterministic beklenen davranisla assert guclendirilsin.

### A-014
- Katman: Infra
- Alan: Config senkronizasyonu
- Siddet: Orta
- Regresyon riski: Orta
- Oncelik: P2
- Durum: done
- Etki: Bakim
- Bulgular: MQTT config yazimi hem `run.sh` inline Python hem `sync_options.py` ile iki yerde.
- Kanit: `run.sh`, `sync_options.py`
- Onerilen cozum: Tek sorumlu yol (single writer) secilip digeri kaldirilsin.

---

## P3 (Ucuncu tur / iyilestirme odakli)

### A-015
- Katman: Backend
- Alan: Migration hata gorunurlugu
- Siddet: Dusuk
- Regresyon riski: Dusuk
- Oncelik: P3
- Durum: done
- Etki: Operasyon
- Bulgular: DB migration fonksiyonlari exception yakalayıp warning'e dusuyor; deployment kalite sinyali zayif.
- Kanit: `app/db/session.py` (`_migrate_*`)
- Onerilen cozum: Migration sonucunu health endpoint'e yansit.

### A-016
- Katman: Frontend
- Alan: localStorage erisimleri
- Siddet: Dusuk
- Regresyon riski: Dusuk
- Oncelik: P3
- Durum: done
- Etki: Dayaniklilik
- Bulgular: Bazi noktalarda dogrudan localStorage erisimi var (guard/catch yok).
- Kanit: `ui/src/components/Sidebar.tsx`, `ui/src/i18n/index.ts`, `ui/src/pages/Events.tsx`
- Onerilen cozum: Safe storage wrapper ile exception-safe ve merkezi yonetim.

### A-017
- Katman: Frontend
- Alan: Diagnostik metin standardi
- Siddet: Dusuk
- Regresyon riski: Dusuk
- Oncelik: P3
- Durum: done
- Etki: UX tutarliligi
- Bulgular: Diagnostics ve Dashboard'da sabit Turkce metinler var.
- Kanit: `ui/src/pages/Diagnostics.tsx`, `ui/src/pages/Dashboard.tsx`
- Onerilen cozum: Tumu i18n key'e tasinsin.

---

## Needs-Design (yan etki riski yuksek maddeler)

### A-018
- Katman: Backend
- Alan: Detector thread/process mimarisi
- Siddet: Orta
- Regresyon riski: Yuksek
- Oncelik: P2
- Durum: done
- Etki: Performans/Guvenilirlik
- Bulgular: `detector.py` icinde uzun ve cok sorumluluklu loop yapisi var; kapsamli refactor istenirse yan etki riski yuksek.
- Kanit: `app/workers/detector.py` (ana loop, reconnect, status, event create)
- Onerilen cozum: Refactor once tasarim dokumani + davranis parity checklist ile yapilmali.

### A-019
- Katman: Backend
- Alan: Live stream semaphore/backpressure
- Siddet: Orta
- Regresyon riski: Yuksek
- Oncelik: P2
- Durum: done
- Etki: Canli izleme stabilitesi
- Bulgular: Canli stream acquire/release akisi generator lifecycle'a cok bagli; edge-case disconnect'lerde detayli test gerekir.
- Kanit: `app/routers/live.py`
- Onerilen cozum: Lifecycle testleri (client disconnect/timeout/reconnect) olmadan degistirilmemeli.

### A-020
- Katman: Infra
- Alan: Startup orchestration
- Siddet: Orta
- Regresyon riski: Yuksek
- Oncelik: P2
- Durum: done
- Etki: Calisma ortami stabilitesi
- Bulgular: `supervisord` + shell startup + service init daginik; health-aware orchestrationa gecis buyuk degisiklik gerektirir.
- Kanit: `run.sh`, `supervisord.conf`, `app/main.py`
- Onerilen cozum: Kademeli gecis plani (health checks -> retry strategy -> startup contract tests).

---

## Secim Kapisi

- Bu listeden secmedigin hicbir madde uygulanmayacak.
- Once `P1` icinden secim yapman onerilir.
- Her secilen madde icin ayri, kucuk, geri alinabilir patch stratejisi izlenecek.
