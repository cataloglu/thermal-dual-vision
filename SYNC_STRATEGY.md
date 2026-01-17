# Thermal/Color Sync Strategy

Bu dokuman thermal ve color akislari icin temel zaman senkronizasyonu yaklasimini tanimlar.

## Hedef
- Iki akisin zaman bazinda hizalanmasi
- Kisa drift durumlarinda toleransli eslestirme
- Gelecekte uygulanabilir bir arayuz notu sunmak

## Metrikler / Alanlar
Senkronizasyon icin her frame paketinde asagidaki alanlar tutulur:
- `source`: `thermal` | `color`
- `sequence`: artan frame sayaci
- `capture_ts`: capture aninda UTC epoch (ms)
- `receive_ts`: pipeline giris aninda UTC epoch (ms)
- `fps`: hedef fps

## Yaklasim
1) **Capture timestamp tabanli eslestirme**
   - Esas alinacak alan `capture_ts`.
   - Bir akistan gelen frame, diger akisin `capture_ts` alanina en yakin olan frame ile eslestirilir.

2) **Kaynakla bagimsiz gecici buffer**
   - Her kaynak icin kisa sureli halka buffer (N frame).
   - Eslestirme, buffer icindeki en yakin `capture_ts` ile yapilir.

3) **Eslestirme maliyeti**
   - `delta_ms = abs(thermal.capture_ts - color.capture_ts)`
   - En dusuk `delta_ms` kazanir.

## Drift / Tolerans Sinirlari
- `soft_tolerance_ms`: 150 ms (eslestirme tercih eşiği)
- `hard_tolerance_ms`: 500 ms (eslestirme kesme eşiği)
- `drop_policy`: `hard_tolerance_ms` asilirsa frame eslestirilmez ve "unmatched" olarak isaretlenir.

## Arayuz Notlari (Gelecek Uygulama)
Senkronizasyona uygun ortak frame paketi:
```text
FramePacket {
  source: "thermal" | "color"
  sequence: int
  capture_ts: int  // epoch ms
  receive_ts: int  // epoch ms
  fps: int
  frame: <numpy ndarray>
}
```

Senkronizasyon modul imzasi:
```text
match_frames(
  thermal_frames: List[FramePacket],
  color_frames: List[FramePacket],
  soft_tolerance_ms: int,
  hard_tolerance_ms: int
) -> List[Tuple[FramePacket, FramePacket]]
```

## Notlar
- `capture_ts` cihaz veya stream timestamp'tan alinabiliyorsa tercih edilir.
- `receive_ts` sadece yedek/diagnostic amaciyla tutulur.
- Drift izlemek icin `delta_ms` loglanabilir.
