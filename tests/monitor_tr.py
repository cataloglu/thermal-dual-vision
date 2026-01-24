import time
import csv
import datetime
import subprocess
import json
import urllib.request
import urllib.error
import sys
import os

# Ayarlar
API_URL = "http://localhost:8000/api/health"
GO2RTC_URL = "http://localhost:1984/api/streams"
RAPOR_DOSYASI = "uzun_test_sonuclari.csv"
KONTROL_ARALIGI = 60  # saniye
TEST_SURESI_SAAT = 3

def zaman_damgasi_al():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def api_saglik_kontrolu():
    try:
        with urllib.request.urlopen(API_URL, timeout=5) as response:
            if response.status == 200:
                return "TAMAM", response.read().decode('utf-8')
            else:
                return "HATA", f"Durum Kodu: {response.status}"
    except Exception as e:
        return "KRITIK_HATA", str(e)

def yayinlari_kontrol_et():
    try:
        with urllib.request.urlopen(GO2RTC_URL, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                sayi = len(data) if isinstance(data, dict) else 0
                return "TAMAM", sayi, data
            else:
                return "HATA", 0, {}
    except Exception as e:
        return "KRITIK_HATA", 0, str(e)

def docker_durumu_al():
    try:
        cmd = ["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.MemPerc}}|{{.CPUPerc}}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        stats = {}
        for line in result.stdout.strip().split('\n'):
            if not line: continue
            parts = line.split('|')
            if len(parts) == 3:
                isim = parts[0]
                bellek = parts[1]
                cpu = parts[2]
                stats[isim] = f"Bellek: {bellek}, CPU: {cpu}"
        return stats
    except Exception as e:
        return {"hata": str(e)}

def loglari_kontrol_et():
    try:
        cmd = ["docker-compose", "logs", "--since", "1m"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        hata_sayisi = 0
        cikti = result.stdout + result.stderr
        
        detaylar = []
        for satir in cikti.split('\n'):
            if "Error" in satir or "Exception" in satir or "Traceback" in satir:
                hata_sayisi += 1
                if len(detaylar) < 3: # Sadece ilk 3 hatayı kaydet
                    detaylar.append(satir.strip()[:100])
                
        return hata_sayisi, "; ".join(detaylar)
    except Exception as e:
        return -1, str(e)

def csv_baslat():
    basliklar = ["Zaman", "API_Durumu", "Yayin_Sayisi", "Docker_Kullanimi", "Log_Hata_Sayisi", "Hata_Detaylari"]
    
    if not os.path.exists(RAPOR_DOSYASI):
        with open(RAPOR_DOSYASI, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(basliklar)

def rapora_yaz(satir):
    with open(RAPOR_DOSYASI, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(satir)

def main():
    print(f"Uzun süreli test başlatılıyor... Hedef: {TEST_SURESI_SAAT} saat")
    print(f"Rapor dosyası: {RAPOR_DOSYASI}")
    csv_baslat()
    
    baslangic = time.time()
    bitis = baslangic + (TEST_SURESI_SAAT * 3600)
    
    while time.time() < bitis:
        zaman = zaman_damgasi_al()
        
        # Kontroller
        api_durum, api_detay = api_saglik_kontrolu()
        yayin_durum, yayin_sayisi, yayin_detay = yayinlari_kontrol_et()
        docker_stats = docker_durumu_al()
        docker_json = json.dumps(docker_stats)
        hata_sayisi, hata_detay = loglari_kontrol_et()
        
        # Konsol Bildirimi
        print(f"[{zaman}] API: {api_durum} | Yayinlar: {yayin_sayisi} | Hatalar: {hata_sayisi}")
        
        if api_durum != "TAMAM":
            print(f"\033[91mKRİTİK: API ÇALIŞMIYOR! ({api_detay})\033[0m")
        
        if yayin_sayisi < 3:
             print(f"\033[93mUYARI: Eksik yayın var! ({yayin_sayisi}/3)\033[0m")
             
        # CSV Kayıt
        rapora_yaz([zaman, api_durum, yayin_sayisi, docker_json, hata_sayisi, hata_detay])
        
        time.sleep(KONTROL_ARALIGI)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest durduruldu.")
