# E2E TESTS — Playwright

Bu doküman, UI “Save” akışlarının otomatik testini açıklar.

---

## 1) Kapsam
- Settings sekmelerinde **Save** butonu çalışıyor mu?
- API çağrısı yapılıyor mu?
- Başarı toast’u görünüyor mu?

Not: Testler **API’yi stub’lar**, backend çalışmasa bile UI akışı doğrulanır.

---

## 2) Kurulum
```bash
cd ui
npx playwright install
npm install
```

---

## 3) Çalıştırma
```bash
cd ui
npm run test:e2e
```

---

## 4) Test Dosyası
- `ui/tests/settings-save.spec.ts`

---

## 5) Başarısızlık Durumunda
- UI element label değiştiyse test selector’ları güncelle
- Toast metni değiştiyse `expectSavedToast` güncelle
