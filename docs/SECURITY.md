# SECURITY — Smart Motion Detector (v2)

## 1) Secrets Yönetimi
- RTSP/Telegram/OpenAI gibi gizli alanlar maskelenir.
- Config dosyasında gerçek değerler tutulur, API’de maskeli döner.
- `.env` yalnızca lokal geliştirme içindir, repoya girmez.

---

## 2) Depolama Güvenliği
- Media ve DB erişimi yalnızca uygulama kullanıcılarıyla sınırlıdır.
- Disk temizleme stratejisi aktif olmalıdır.

---

## 3) Ağ Güvenliği
- MVP’de auth yok (kapalı ağ/yerel kullanım varsayımı).
- Üretimde reverse proxy + IP kısıtı önerilir.

