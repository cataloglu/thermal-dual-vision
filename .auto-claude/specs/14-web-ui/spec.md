# 14 - Web UI

## Overview
Home Assistant ingress uyumlu web arayüzü. Vite + Preact + Tailwind CSS frontend, Flask backend. Canlı kamera görüntüsü, dashboard, galeri, event log ve ayarlar sayfaları.

## Workflow Type
**feature** - Web arayüzü geliştirme

## Task Scope
Frigate NVR benzeri modern, hafif web arayüzü. HA ingress ile entegre, responsive tasarım.

### Sayfa Yapısı
| Sayfa | Açıklama |
|-------|----------|
| Dashboard | Özet istatistikler, son tespitler, sistem durumu |
| Live View | Canlı kamera stream (MJPEG) |
| Gallery | Kaydedilen screenshot'lar grid görünümü |
| Events | Tespit geçmişi tablo/liste |
| Settings | Konfigürasyon ayarları formu |

### Teknoloji Stack
```
Frontend:
  - Vite (build tool)
  - Preact (lightweight React alternative)
  - Tailwind CSS (utility-first CSS)
  - TypeScript

Backend:
  - Flask (Python web framework)
  - Flask-SocketIO (WebSocket for live updates)
```

### API Endpoints
```
GET  /api/status          - Sistem durumu
GET  /api/stats           - İstatistikler
GET  /api/events          - Tespit geçmişi
GET  /api/screenshots     - Screenshot listesi
GET  /api/screenshot/<id> - Tek screenshot
GET  /api/stream          - MJPEG canlı stream
POST /api/config          - Ayarları güncelle
GET  /api/config          - Mevcut ayarlar
WS   /ws/events           - Canlı event stream
```

## Requirements
1. HA ingress uyumlu (X-Ingress-Path header)
2. Sadece 172.30.32.2 IP'den erişim
3. Responsive tasarım (mobile-friendly)
4. Dark/Light mode
5. WebSocket ile canlı güncellemeler
6. Türkçe/İngilizce dil desteği
7. Hafif ve hızlı yükleme (<100KB gzipped)

## Files to Modify
- `Dockerfile` - Node.js build step eklenmesi
- `requirements.txt` - Flask-SocketIO eklenmesi

## Files to Create
```
web/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── components/
│   │   ├── Layout.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── ...
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── LiveView.tsx
│   │   ├── Gallery.tsx
│   │   ├── Events.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   └── useApi.ts
│   └── utils/
│       └── api.ts
src/
├── web_server.py         - Flask app
├── api/
│   ├── __init__.py
│   ├── routes.py         - API endpoints
│   └── websocket.py      - WebSocket handlers
```

## Files to Reference
- `src/config.py` - Konfigürasyon yapısı
- `src/screenshot_manager.py` - Screenshot erişimi
- `.auto-claude/CONTEXT.md` - Proje bağlamı

## Success Criteria
- [ ] Flask web server çalışıyor
- [ ] Tüm API endpoint'leri çalışıyor
- [ ] Frontend build ediliyor
- [ ] HA ingress üzerinden erişim var
- [ ] Canlı stream görüntüleniyor
- [ ] WebSocket bağlantısı çalışıyor
- [ ] Responsive tasarım mobile'da çalışıyor
- [ ] Dark/Light mode çalışıyor

## QA Acceptance Criteria
- Lighthouse performance score > 90
- Tüm sayfalarda navigasyon testi
- Mobile responsive test (320px - 1920px)
- WebSocket reconnection testi
- API endpoint'leri unit test
- Puppeteer ile E2E test

## Dependencies
- 01-project-structure
- 04-screenshot-system
- 06-mqtt-integration
- 08-main-app

## Notes
- Frigate NVR'ın web UI'ından ilham alınacak
- Preact tercih edildi (React'tan 3KB vs 45KB)
- Tailwind CSS ile tutarlı styling
- Vite ile hızlı development ve build
