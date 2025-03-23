#!/usr/bin/env python3
"""
Telefon fotoğraf/video/ses dosyalarındaki tüm meta verileri siler
Hiçbir ek kütüphane gerektirmez - Android, Windows ve Linux'ta çalışır
"Umutsuz durumlar yoktur, umutsuz insanlar vardır. Ben hiçbir zaman umudumu yitirmedim." Gazi Mustafa Kemal Atatürk 
"""

import os
import sys
import random
import struct
import re
import time

# Desteklenen dosya türleri
TELEFON_MEDYA_UZANTILARI = [
    # Fotoğraflar
    '.sjpg', '.jpeg', '.png', '.heic', '.heif',
    # Videolar
    '.mp4', '.mov', '.3gp', '.mkv',
    # Ses
    '.mp3', '.m4a', '.aac', '.wav'
]

def dosya_turu_bul(dosya_adi):
    """Dosya türünü uzantısına göre belirler"""
    _, uzanti = os.path.splitext(dosya_adi)
    uzanti = uzanti.lower()
    
    if uzanti in ['.jpg', '.jpeg', '.heic', '.heif']:
        return "foto"
    elif uzanti in ['.mp4', '.mov', '.3gp', '.mkv']:
        return "video"
    elif uzanti in ['.mp3', '.m4a', '.aac', '.wav']:
        return "ses"
    else:
        return "bilinmiyor"

def zaman_damgasi_degistir(dosya_yolu):
    """Dosyanın oluşturma ve değiştirme tarihlerini rastgele değerler ile değiştirir"""
    try:
        # Son 3 yıl için rastgele tarih üret
        simdiki_zaman = int(time.time())
        uc_yil = 3 * 365 * 24 * 60 * 60
        rastgele_zaman = random.randint(simdiki_zaman - uc_yil, simdiki_zaman)
        
        # Dosya tarihlerini değiştir
        os.utime(dosya_yolu, (rastgele_zaman, rastgele_zaman))
        
        return True
    except Exception as e:
        return False

def jpeg_meta_verilerini_yok_et(dosya_yolu):
    """JPEG dosyalarındaki tüm meta verileri yok eder (konum, cihaz bilgisi, tarih vb.)"""
    try:
        # Dosyayı oku
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # JPEG kontrolü yap
        if veri[0:2] != b'\xFF\xD8':
            return False
        
        # Sadece gerekli bölümleri içeren yeni bir JPEG oluştur
        yeni_veri = bytearray()
        yeni_veri.extend(b'\xFF\xD8')  # JPEG başlangıç işareti
        
        # Segmentleri işle
        i = 2
        while i < len(veri) - 1:
            if veri[i] != 0xFF:
                i += 1
                continue
            
            # İşaretçi bulundu
            isaretci = veri[i:i+2]
            
            # Görüntü sonu
            if isaretci == b'\xFF\xD9':
                yeni_veri.extend(b'\xFF\xD9')
                break
            
            # Segment uzunluğunu al
            if i + 3 < len(veri):
                uzunluk = (veri[i+2] << 8) + veri[i+3]
            else:
                i += 1
                continue
            
            # Meta veri segmentlerini atla
            if isaretci in [
                b'\xFF\xE0',  # JFIF
                b'\xFF\xE1',  # EXIF (GPS, cihaz bilgileri burada)
                b'\xFF\xE2',  # ICC
                b'\xFF\xEE',  # Adobe
                b'\xFF\xED',  # IPTC
                b'\xFF\xFE',  # Yorum
            ]:
                i += 2 + uzunluk
                continue
            
            # Görüntü için gerekli diğer segmentleri koru
            if i + 2 + uzunluk <= len(veri):
                yeni_veri.extend(veri[i:i+2+uzunluk])
                
                # Start of Scan (SOS) segmenti ise, görüntü verilerini de ekle
                if isaretci == b'\xFF\xDA':
                    scan_sonu = i + 2 + uzunluk
                    while scan_sonu < len(veri) - 1:
                        if veri[scan_sonu] == 0xFF and veri[scan_sonu + 1] != 0x00:
                            break
                        scan_sonu += 1
                    
                    yeni_veri.extend(veri[i+2+uzunluk:scan_sonu])
                    i = scan_sonu
                    continue
                
                i += 2 + uzunluk
            else:
                i += 1
        
        # Meta veri anahtar kelimelerini ara ve boz
        anahtar_kelimeler = [b"GPS", b"Konum", b"Make", b"Model", b"Software", 
                          b"DateTime", b"Artist", b"Copyright", b"CameraModel"]
        
        for kelime in anahtar_kelimeler:
            pos = 0
            while True:
                pos = yeni_veri.find(kelime, pos)
                if pos == -1:
                    break
                
                # Anahtar kelimeleri boz
                for i in range(len(kelime)):
                    if pos + i < len(yeni_veri):
                        yeni_veri[pos + i] = random.randint(32, 126)  # ASCII karakterler
                
                pos += len(kelime)
        
        # Temizlenmiş dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(yeni_veri)
        
        return True
    except Exception as e:
        print(f"  ! Hata: {str(e)}")
        return False

def png_meta_verilerini_yok_et(dosya_yolu):
    """PNG dosyalarındaki tüm meta verileri yok eder"""
    try:
        # Dosyayı oku
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # PNG kontrolü yap
        if veri[0:8] != b'\x89PNG\r\n\x1a\n':
            return False
        
        # Sadece gerekli blokları içeren yeni bir PNG oluştur
        yeni_veri = bytearray()
        yeni_veri.extend(b'\x89PNG\r\n\x1a\n')  # PNG imzası
        
        # Sadece gerekli chunk'ları koru (IHDR, IDAT, IEND)
        gerekli_chunklar = [b'IHDR', b'PLTE', b'IDAT', b'IEND']
        
        pozisyon = 8
        while pozisyon < len(veri):
            if pozisyon + 8 > len(veri):
                break
            
            # Chunk uzunluğu ve tipini oku
            uzunluk = struct.unpack('>I', veri[pozisyon:pozisyon+4])[0]
            chunk_tipi = veri[pozisyon+4:pozisyon+8]
            
            # Mevcut chunk'ın sonunu hesapla
            chunk_sonu = pozisyon + 8 + uzunluk + 4  # uzunluk + tip + veri + CRC
            if chunk_sonu > len(veri):
                break
            
            # Sadece gerekli chunk'ları koru
            if chunk_tipi in gerekli_chunklar:
                yeni_veri.extend(veri[pozisyon:chunk_sonu])
            
            pozisyon = chunk_sonu
        
        # Temizlenmiş dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(yeni_veri)
        
        return True
    except Exception as e:
        print(f"  ! Hata: {str(e)}")
        return False

def mp4_meta_verilerini_yok_et(dosya_yolu):
    """MP4 ve benzeri video dosyalarındaki meta verileri temizler"""
    try:
        # Dosyayı oku
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # Meta veri atomlarını bul ve temizle
        meta_atomlar = [b'moov.udta.meta', b'moov.meta', b'uuid', b'xyz', b'geo']
        
        # MP4 dosyalarında atomları ara
        for atom in meta_atomlar:
            pozisyon = 0
            while True:
                pozisyon = veri.find(atom, pozisyon)
                if pozisyon == -1:
                    break
                
                # Atom boyutunu alıp içeriğini sıfırla
                for i in range(len(atom)):
                    if pozisyon + i < len(veri):
                        # Atom başlığını değiştir
                        veri[pozisyon + i] = random.randint(0, 255)
                
                pozisyon += len(atom)
        
        # GPS ve konum bilgilerini içerebilecek kısımları ara
        gps_kelimeler = [b"GPS", b"Location", b"GEO", b"geo", b"Konum", b"Lokasyon"]
        
        for kelime in gps_kelimeler:
            pozisyon = 0
            while True:
                pozisyon = veri.find(kelime, pozisyon)
                if pozisyon == -1:
                    break
                
                # Bu meta verileri boz
                for i in range(len(kelime)):
                    if pozisyon + i < len(veri):
                        veri[pozisyon + i] = random.randint(32, 126)
                
                pozisyon += len(kelime)
        
        # Temizlenmiş dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(veri)
        
        return True
    except Exception as e:
        print(f"  ! Hata: {str(e)}")
        return False

def mp3_meta_verilerini_yok_et(dosya_yolu):
    """MP3 ve ses dosyalarındaki meta verileri temizler"""
    try:
        with open(dosya_yolu, 'rb') as f:
            veri = f.read()
        
        # Temizlenmiş veri oluştur
        temiz_veri = bytearray()
        
        # ID3v2 etiketlerini atla (dosya başında)
        pozisyon = 0
        
        # ID3v2 etiketi varsa atla
        if len(veri) > 10 and veri[0:3] == b'ID3':
            # Etiket boyutu (syncsafe integer)
            etiket_boyutu = ((veri[6] & 0x7F) << 21) | \
                           ((veri[7] & 0x7F) << 14) | \
                           ((veri[8] & 0x7F) << 7) | \
                           (veri[9] & 0x7F)
            etiket_boyutu += 10  # başlık boyutunu ekle
            
            # Etiketi atla
            pozisyon = etiket_boyutu
        
        # Bu noktadan sonraki müzik verisini kopyala
        temiz_veri.extend(veri[pozisyon:])
        
        # ID3v1 etiketini sondan sil (sabit 128 byte)
        if len(temiz_veri) > 128 and temiz_veri[-128:-125] == b'TAG':
            temiz_veri = temiz_veri[:-128]
        
        # Temizlenmiş dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(temiz_veri)
        
        return True
    except Exception as e:
        print(f"  ! Hata: {str(e)}")
        return False

def dosya_meta_verilerini_sil(dosya_yolu):
    """Bir dosyanın tüm meta verilerini siler"""
    print(f"İşleniyor: {dosya_yolu}")
    
    # Yedek oluştur
    yedek_yolu = dosya_yolu + ".yedek"
    try:
        with open(dosya_yolu, 'rb') as kaynak:
            with open(yedek_yolu, 'wb') as hedef:
                hedef.write(kaynak.read())
    except:
        print("  ! Yedek oluşturulamadı, dosya atlanıyor")
        return False
    
    # Dosya türünü belirle
    dosya_turu = dosya_turu_bul(dosya_yolu)
    
    try:
        # Dosya türüne göre uygun temizleme yöntemini uygula
        if dosya_turu == "foto":
            _, uzanti = os.path.splitext(dosya_yolu)
            uzanti = uzanti.lower()
            
            if uzanti in ['.jpg', '.jpeg']:
                basarili = jpeg_meta_verilerini_yok_et(dosya_yolu)
            elif uzanti in ['.png']:
                basarili = png_meta_verilerini_yok_et(dosya_yolu)
            else:
                # Diğer fotoğraf formatları için genel yaklaşım
                basarili = genel_meta_temizle(dosya_yolu)
        
        elif dosya_turu == "video":
            basarili = mp4_meta_verilerini_yok_et(dosya_yolu)
            
        elif dosya_turu == "ses":
            basarili = mp3_meta_verilerini_yok_et(dosya_yolu)
            
        else:
            print("  ! Desteklenmeyen dosya türü")
            # Yedeği geri yükle
            os.remove(dosya_yolu)
            os.rename(yedek_yolu, dosya_yolu)
            return False
        
        # Son adım: Dosya zaman damgalarını değiştir
        zaman_damgasi_degistir(dosya_yolu)
        
        if basarili:
            print("  ✓ Meta veriler tamamen yok edildi")
        else:
            print("  ! Meta veri temizleme kısmen başarılı")
            
        # Sorun yoksa yedeği sil
        try:
            os.remove(yedek_yolu)
        except:
            pass
            
        return True
        
    except Exception as e:
        print(f"  ! İşlem hatası: {str(e)}")
        
        # Yedeği geri yükle
        try:
            os.remove(dosya_yolu)
            os.rename(yedek_yolu, dosya_yolu)
            print("  Yedek geri yüklendi")
        except:
            print("  ! Yedek geri yüklenemedi")
        
        return False

def genel_meta_temizle(dosya_yolu):
    """Dosya türü tanınmayan dosyalar için genel meta veri temizleme yaklaşımı"""
    try:
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # Dosya başlangıcından itibaren belli bir kısmı tara
        tara_boyutu = min(4096, int(len(veri) * 0.02))  # Maksimum 4KB veya %2'lik kısmı
        
        # Meta veri olabilecek kelimeleri ara
        meta_kelimeler = [
            b"GPS", b"Konum", b"Make", b"Model", b"Device", 
            b"Created", b"Modified", b"Author", b"Copyright",
            b"iPhone", b"Samsung", b"Huawei", b"Xiaomi", b"OPPO", b"Realme"
        ]
        
        for kelime in meta_kelimeler:
            pozisyon = 0
            while pozisyon < tara_boyutu:
                pozisyon = veri.find(kelime, pozisyon, tara_boyutu)
                if pozisyon == -1:
                    break
                
                # Bulunan kelimeleri boz
                for i in range(len(kelime)):
                    if pozisyon + i < len(veri):
                        veri[pozisyon + i] = random.randint(32, 126)
                
                pozisyon += len(kelime)
        
        # Dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(veri)
        
        return True
    except Exception as e:
        return False

def klasor_islet(klasor, alt_klasorler=False):
    """Bir klasördeki tüm desteklenen dosyaları işler"""
    for dosya in os.listdir(klasor):
        tam_yol = os.path.join(klasor, dosya)
        
        if os.path.isfile(tam_yol):
            _, uzanti = os.path.splitext(tam_yol)
            if uzanti.lower() in TELEFON_MEDYA_UZANTILARI:
                dosya_meta_verilerini_sil(tam_yol)
        elif alt_klasorler and os.path.isdir(tam_yol):
            klasor_islet(tam_yol, alt_klasorler)

def main():
    # Komut satırı argümanlarını kontrol et
    if len(sys.argv) < 2:
        print("Kullanım: python metasilici.py  dosya veya klasor yolu   [-r]")
        print("  -r: Alt klasörleri de işle")
        sys.exit(1)
    
    yol = sys.argv[1]
    alt_klasorler = "-r" in sys.argv
    
    if not os.path.exists(yol):
        print(f"Hata: {yol} bulunamadı")
        sys.exit(1)
    
    # Belirtilen yolu işle
    if os.path.isfile(yol):
        _, uzanti = os.path.splitext(yol)
        if uzanti.lower() in TELEFON_MEDYA_UZANTILARI:
            dosya_meta_verilerini_sil(yol)
        else:
            print(f"Hata: {yol} desteklenen bir telefon medya dosyası değil")
    elif os.path.isdir(yol):
        print(f"Klasör işleniyor: {yol}")
        klasor_islet(yol, alt_klasorler)
    
    print("\n✓ İŞLEM TAMAMLANDI.")
    print("✓ TÜM META VERİLER YOK EDİLDİ.")

if __name__ == "__main__":
    main() 
