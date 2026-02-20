## Release 3.10.102

### Odak
Home Assistant mobil uygulama (Ingress webview) icin arayuz uyumlulugu guclendirildi.

### Neler Degisti
- Mobilde sol menu artik drawer olarak aciliyor; icerigi kapatip ekrani bloklamiyor.
- Mobil overlay ve body scroll-lock davranisi duzeltildi; "takili kalma" sorunu azaltildi.
- Modal pencerelerde (Event detail / compare) scroll ve kapama davranisi mobilde daha stabil.
- `viewport-fit=cover` ve safe-area stilleri eklendi (notch ve alt bar alanlari icin).
- Kamera monitor sayfasi mobil kirilimlara gore yeniden duzenlendi.

### Etki
- HA mobil uygulamada menu ustune binme ve kaydirma sorunlari azalir.
- Kucuk ekranlarda kullanilabilirlik ve dokunmatik gezinme iyilesir.

### Not
Bu surum fonksiyonel ozellik eklemesi degil, mobil UI kararlilik ve uyumluluk guncellemesidir.
