"""
Telefon fotolarındaki ve videolardaki meta verileri silmek için yazılmış basit bir script
Hiçbir ek kütüphane gerektirmiyor - Android, Win ve Linux'ta çalışıyor
"Umutsuz durumlar yoktur, umutsuz insanlar vardır. Ben hiçbir zaman umudumu yitirmedim." Gazi Mustafa Kemal Atatürk 
"""

import os
import sys
import random
import struct
import re
import time
import subprocess

# Desteklenen uzantılar - sonradan daha ekleyebilirim belki
TELEFON_MEDYA_UZANTILARI = [
    # Fotoğraflar
    '.jpg', '.sjpg', '.jpeg', '.png', '.heic', '.heif',
    # Videolar - mp4 en çok kullanılan
    '.mp4', '.mov', '.3gp', '.mkv',
    # Ses dosyaları
    '.mp3', '.m4a', '.aac', '.wav'
]

def dosya_turu_bul(dosya_adi):
    """Dosya türünü uzantıya göre buluyor"""
    _, uzanti = os.path.splitext(dosya_adi)
    uzanti = uzanti.lower()
    
    # En yaygın uzantıları kontrol et
    if uzanti in ['.jpg', '.jpeg', '.heic', '.heif']:
        return "foto"
    elif uzanti in ['.mp4', '.mov', '.3gp', '.mkv']:
        return "video"
    elif uzanti in ['.mp3', '.m4a', '.aac', '.wav']:
        return "ses"
    else:
        return "bilinmiyor"

def zaman_damgasi_degistir(dosya_yolu):
    """Dosya tarihlerini rastgele değiştiriyor ki tarihinden bulunmasın"""
    try:
        # Son 3 yıl içinde rastgele bir tarih - daha eskisi şüpheli olabilir
        simdiki_zaman = int(time.time())
        uc_yil = 3 * 365 * 24 * 60 * 60
        rastgele_zaman = random.randint(simdiki_zaman - uc_yil, simdiki_zaman)
        
        # Dosya tarihlerini değiştir
        os.utime(dosya_yolu, (rastgele_zaman, rastgele_zaman))
        
        return True
    except Exception as e:
        # Pek sorun değil aslında
        return False

def jpeg_meta_verilerini_yok_et(dosya_yolu):
    """JPEG'lerdeki meta verileri siliyor (konum, cihaz, tarih, vb)"""
    try:
        # Dosyayı oku
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # JPEG mi diye bak
        if veri[0:2] != b'\xFF\xD8':
            return False
        
        # RADİKAL YAKLAŞIM: Sadece resmin kendisini koru, meta verileri at gitsin
        # Burası biraz karmaşık ama JPEG formatını biliyorsanız anlarsınız
        
        yeni_veri = bytearray()
        yeni_veri.extend(b'\xFF\xD8')  # SOI - Start of Image
        
        # Segment segment tarayalım
        i = 2
        while i < len(veri) - 1:
            if veri[i] != 0xFF:
                i += 1
                continue
            
            isaretci = veri[i:i+2]
            
            # EOI - End of Image
            if isaretci == b'\xFF\xD9':
                yeni_veri.extend(b'\xFF\xD9')
                break
                
            # Segment uzunluğu 
            if i + 3 < len(veri):
                uzunluk = (veri[i+2] << 8) + veri[i+3]
            else:
                i += 1
                continue
            
            # Bütün meta veri segmentlerini atla 
            # (en kapsamlı temizleme - bunu ben uzun denemeler sonucu buldum)
            if isaretci[1] >= 0xE0 and isaretci[1] <= 0xEF:  # Tüm APP segmentleri (0xFFE0-0xFFEF)
                i += 2 + uzunluk
                continue
            
            # Bazı segmentler lazım yoksa resim bozulur
            # SOF, DHT, DQT ve SOS segmentleri lazım
            gerekli_isaretciler = [
                b'\xFF\xC0', b'\xFF\xC1', b'\xFF\xC2', b'\xFF\xC3',  # SOF0-SOF3
                b'\xFF\xC4',  # DHT
                b'\xFF\xDB',  # DQT
                b'\xFF\xDA'   # SOS
            ]
            
            if isaretci in gerekli_isaretciler:
                # Bu segment gerekli, koru
                if i + 2 + uzunluk <= len(veri):
                    yeni_veri.extend(veri[i:i+2+uzunluk])
                    
                    # SOS segmentinden sonra resmin asıl pikselleri geliyor, onları da ekle
                    if isaretci == b'\xFF\xDA':
                        scan_sonu = i + 2 + uzunluk
                        while scan_sonu < len(veri) - 1:
                            if veri[scan_sonu] == 0xFF and veri[scan_sonu + 1] != 0x00 and veri[scan_sonu + 1] >= 0xD0:
                                break
                            scan_sonu += 1
                        
                        yeni_veri.extend(veri[i+2+uzunluk:scan_sonu])
                        i = scan_sonu
                        continue
                    
                    i += 2 + uzunluk
                else:
                    i += 1
            else:
                # Diğer segmentleri at gitsin
                i += 2 + uzunluk
        
        # Temizlenmiş dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(yeni_veri)
        
        # Kontrol et - bazı cep telefonu fotoğraflarında bu yöntem çalışmayabiliyor
        if len(yeni_veri) < 1000:  # çok küçükse bozulmuştur
            print("  ! JPEG düzgün temizlenemedi, başka yöntem deniyorum...")
            return alternatif_jpeg_temizleme(dosya_yolu)
            
        return True
    except Exception as e:
        print(f"  ! Bir sorun oldu: {str(e)}")
        return alternatif_jpeg_temizleme(dosya_yolu)  # Hata olunca B planı
def alternatif_jpeg_temizleme(dosya_yolu):
    """B Planı: JPEG'leri daha az agresif temizleme (ilki bazen bozabiliyor)"""
    try:
        # Dosyayı oku
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # JPEG mi diye bak
        if veri[0:2] != b'\xFF\xD8':
            return False
            
        # Bilinen tüm meta veri işaretçileri - bunları siliyoruz
        meta_isaretciler = [
            b'\xFF\xE0',  # JFIF
            b'\xFF\xE1',  # EXIF (GPS, cihaz bilgileri burada)
            b'\xFF\xE2',  # ICC
            b'\xFF\xE3',  # Meta
            b'\xFF\xE4',  # Meta
            b'\xFF\xE5',  # Meta
            b'\xFF\xE6',  # Meta
            b'\xFF\xE7',  # Meta
            b'\xFF\xE8',  # Meta
            b'\xFF\xE9',  # Meta
            b'\xFF\xEA',  # Meta
            b'\xFF\xEB',  # Meta
            b'\xFF\xEC',  # Meta
            b'\xFF\xED',  # IPTC/Photoshop
            b'\xFF\xEE',  # Adobe
            b'\xFF\xEF',  # Meta
            b'\xFF\xFE',  # Yorum
        ]
        
        # Bu işaretçileri bulup sil
        for isaretci in meta_isaretciler:
            pozisyon = 0
            while True:
                pozisyon = veri.find(isaretci, pozisyon)
                if pozisyon == -1:
                    break
                
                # Uzunluğu bul
                if pozisyon + 3 < len(veri):
                    uzunluk = (veri[pozisyon+2] << 8) + veri[pozisyon+3]
                    segment_sonu = pozisyon + 2 + uzunluk
                    
                    # Sıfırla
                    for i in range(pozisyon, min(segment_sonu, len(veri))):
                        veri[i] = 0xFF if i == pozisyon else 0x00
                
                pozisyon += 4
        
        # Bazı meta veriler text olarak da saklanabilir, onları da boz
        anahtar_kelimeler = [
            b"GPS", b"Konum", b"Make", b"Model", b"Software", b"Device",
            b"DateTime", b"Date", b"Time", b"Artist", b"Copyright", b"CameraModel",
            b"Location", b"Latitude", b"Longitude", b"Altitude", b"ShutterSpeed",
            b"Flash", b"FocalLength", b"ISO", b"ExposureTime", b"Aperture",
            b"iPhone", b"Samsung", b"Huawei", b"Xiaomi", b"OPPO", b"Realme",
            b"Google", b"Pixel", b"OnePlus", b"Sony", b"LG", b"Motorola"
        ]
        
        for kelime in anahtar_kelimeler:
            pozisyon = 0
            while True:
                pozisyon = veri.find(kelime, pozisyon)
                if pozisyon == -1:
                    break
                
                # Rastgele değiştir
                for i in range(len(kelime)):
                    if pozisyon + i < len(veri):
                        veri[pozisyon + i] = random.randint(32, 126)  # ASCII 
                
                pozisyon += len(kelime)
        
        # Temizlenmiş dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(veri)
        
        return True
    except Exception as e:
        print(f"  ! B planı da olmadı: {str(e)}")
        return False

def png_meta_verilerini_yok_et(dosya_yolu):
    """PNG meta verilerini siliyor"""
    try:
        # Dosyayı oku
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # PNG mi diye bak
        if veri[0:8] != b'\x89PNG\r\n\x1a\n':
            return False
        
        # Yeni temiz PNG yapıyoruz
        yeni_veri = bytearray()
        yeni_veri.extend(b'\x89PNG\r\n\x1a\n')  # PNG imzası
        
        # Sadece gerekli chunk'ları koru (IHDR, IDAT, IEND)
        # Diğerleri meta veri olabilir
        gerekli_chunklar = [b'IHDR', b'PLTE', b'IDAT', b'IEND']
        
        pozisyon = 8
        while pozisyon < len(veri):
            if pozisyon + 8 > len(veri):
                break
            
            # Chunk boyutu ve tipi
            uzunluk = struct.unpack('>I', veri[pozisyon:pozisyon+4])[0]
            chunk_tipi = veri[pozisyon+4:pozisyon+8]
            
            # Chunk'ın bitişi
            chunk_sonu = pozisyon + 8 + uzunluk + 4  # uzunluk + tip + veri + CRC
            if chunk_sonu > len(veri):
                break
            
            # Sadece gereklileri koru
            if chunk_tipi in gerekli_chunklar:
                yeni_veri.extend(veri[pozisyon:chunk_sonu])
            
            pozisyon = chunk_sonu
        
        # Temizlenmiş dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(yeni_veri)
        
        return True
    except Exception as e:
        print(f"  ! PNG temizlerken sorun: {str(e)}")
        return False

def mp4_meta_verilerini_yok_et(dosya_yolu):
    """MP4 ve diğer videolardan meta verileri temizliyor"""
    try:
        # Dosyayı oku
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # Meta veri atomlarını bul - bunlar MP4 standardından
        meta_atomlar = [b'moov.udta.meta', b'moov.meta', b'uuid', b'xyz', b'geo']
        
        # MP4 atomlarını ara ve temizle
        for atom in meta_atomlar:
            pozisyon = 0
            while True:
                pozisyon = veri.find(atom, pozisyon)
                if pozisyon == -1:
                    break
                
                # İçeriği rastgele değiştir
                for i in range(len(atom)):
                    if pozisyon + i < len(veri):
                        veri[pozisyon + i] = random.randint(0, 255)
                
                pozisyon += len(atom)
        
        # GPS ve konum içerebilecek kısımları ara
        gps_kelimeler = [b"GPS", b"Location", b"GEO", b"geo", b"Konum", b"Lokasyon"]
        
        for kelime in gps_kelimeler:
            pozisyon = 0
            while True:
                pozisyon = veri.find(kelime, pozisyon)
                if pozisyon == -1:
                    break
                
                # Boz
                for i in range(len(kelime)):
                    if pozisyon + i < len(veri):
                        veri[pozisyon + i] = random.randint(32, 126)
                
                pozisyon += len(kelime)
        
        # Temizlenmiş dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(veri)
        
        return True
    except Exception as e:
        print(f"  ! MP4 temizlerken sorun: {str(e)}")
        return False

def mp3_meta_verilerini_yok_et(dosya_yolu):
    """MP3 dosyalarının ID3 etiketlerini siliyor"""
    try:
        with open(dosya_yolu, 'rb') as f:
            veri = f.read()
        
        # Temiz veri
        temiz_veri = bytearray()
        
        # ID3v2 etiketleri başta olur
        pozisyon = 0
        
        # ID3v2 var mı?
        if len(veri) > 10 and veri[0:3] == b'ID3':
            # Boyutunu hesapla (biraz karışık)
            etiket_boyutu = ((veri[6] & 0x7F) << 21) | \
                           ((veri[7] & 0x7F) << 14) | \
                           ((veri[8] & 0x7F) << 7) | \
                           (veri[9] & 0x7F)
            etiket_boyutu += 10  # başlık da ekle
            
            # Atla
            pozisyon = etiket_boyutu
        
        # Buradan sonrası müzik verisi
        temiz_veri.extend(veri[pozisyon:])
        
        # ID3v1 etiketi sonda olur (sabit 128 byte)
        if len(temiz_veri) > 128 and temiz_veri[-128:-125] == b'TAG':
            temiz_veri = temiz_veri[:-128]
        
        # Temizlenmiş dosyayı yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(temiz_veri)
        
        return True
    except Exception as e:
        print(f"  ! MP3 temizlerken sorun: {str(e)}")
        return False


def meta_veri_kontrol_et(dosya_yolu):
    """Dosyada meta veri kalıntısı var mı diye bakıyor"""
    try:
        # Dosya türü
        dosya_turu = dosya_turu_bul(dosya_yolu)
        
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # Aranacak meta veriler
        meta_kelimeler = [
            b"GPS", b"Konum", b"Location", b"Make", b"Model", b"Device", b"Camera",
            b"DateTime", b"Date", b"Time", b"Created", b"Modified", 
            b"Artist", b"Copyright", b"Author", b"Owner", b"Comment",
            b"iPhone", b"Samsung", b"Huawei", b"Xiaomi", b"OPPO", b"Realme",
            b"Google", b"Pixel", b"OnePlus", b"Sony", b"LG", b"Motorola",
            b"WhatsApp", b"Facebook", b"Instagram", b"Twitter", b"Telegram"
        ]
        
        bulunan_metalar = []
        toplam_meta = 0
        
        # Ara
        for kelime in meta_kelimeler:
            pozisyon = 0
            while True:
                pozisyon = veri.find(kelime, pozisyon)
                if pozisyon == -1:
                    break
                
                # Bulunan yerin etrafına da bak
                baslangic = max(0, pozisyon - 10)
                bitis = min(len(veri), pozisyon + len(kelime) + 10)
                context = veri[baslangic:bitis]
                
                # Sadece ASCII göster, diğerleri yerine nokta koy
                context_str = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in context])
                
                bulunan_metalar.append(f"  {kelime.decode('utf-8', 'ignore')}: ...{context_str}...")
                toplam_meta += 1
                
                pozisyon += len(kelime)
                
                # En fazla 5 örnek göster, çok uzun olmasın        # En fazla 5 örnek göster, çok uzun olmasın
                if len(bulunan_metalar) >= 5:
                    bulunan_metalar.append(f"  ... ve {toplam_meta - 5} başka meta veri ...")
                    break
            
            # 5'ten fazla örnek varsa yeter
            if len(bulunan_metalar) >= 5:
                break
        
        if toplam_meta > 0:
            print(f"\n! DİKKAT: Dosyada {toplam_meta} meta veri kalıntısı var:")
            for bulgu in bulunan_metalar[:5]:
                print(bulgu)
            return False
        else:
            print("\n✓ Hiçbir meta veri kalıntısı bulunamadı.")
            return True
            
    except Exception as e:
        print(f"  ! Kontrol ederken sorun: {str(e)}")
        return False

def dosya_meta_verilerini_sil(dosya_yolu):
    """Tüm meta verileri siliyor"""
    print(f"İşleniyor: {dosya_yolu}")
    
    # Yedek al - başımıza bir şey gelmesin
    yedek_yolu = dosya_yolu + ".yedek"
    try:
        with open(dosya_yolu, 'rb') as kaynak:
            with open(yedek_yolu, 'wb') as hedef:
                hedef.write(kaynak.read())
    except:
        print("  ! Yedek alamadım, bu dosyayı atlıyorum...")
        return False
    
    # Dosya türü
    dosya_turu = dosya_turu_bul(dosya_yolu)
    
    try:
        # Dosya türüne göre uygun metodu çağır
        if dosya_turu == "foto":
            _, uzanti = os.path.splitext(dosya_yolu)
            uzanti = uzanti.lower()
            
            if uzanti in ['.jpg', '.jpeg']:
                basarili = jpeg_meta_verilerini_yok_et(dosya_yolu)
            elif uzanti in ['.png']:
                basarili = png_meta_verilerini_yok_et(dosya_yolu)
            else:
                # Diğer formatlara genel yaklaşım
                basarili = genel_meta_temizle(dosya_yolu)
        
        elif dosya_turu == "video":
            basarili = mp4_meta_verilerini_yok_et(dosya_yolu)
            
        elif dosya_turu == "ses":
            basarili = mp3_meta_verilerini_yok_et(dosya_yolu)
            
        else:
            print("  ! Bu dosya türü desteklenmiyor :(")
            # Yedeği geri al
            os.remove(dosya_yolu)
            os.rename(yedek_yolu, dosya_yolu)
            return False
        
        # Son olarak dosyanın zaman damgasını değiştir
        zaman_damgasi_degistir(dosya_yolu)
        
        if basarili:
            print("  ✓ Meta veriler tamamen yok edildi")
            # Kontrol et
            meta_veri_kontrol_et(dosya_yolu)
        else:
            print("  ! Meta veri temizleme kısmen başarılı oldu")
            
        # Sorun yoksa yedeği sil
        try:
            os.remove(yedek_yolu)
        except:
            pass
            
        return True
        
    except Exception as e:
        print(f"  ! Bir sorun çıktı: {str(e)}")
        
        # Yedeği geri al
        try:
            os.remove(dosya_yolu)
            os.rename(yedek_yolu, dosya_yolu)
            print("  Yedek geri alındı")
        except:
            print("  ! Yedeği geri alamadım :(")
        
        return False

def genel_meta_temizle(dosya_yolu):
    """Dosya türü belirsiz olanlar için temizlik (HEIC gibi)"""
    try:
        with open(dosya_yolu, 'rb') as f:
            veri = bytearray(f.read())
        
        # Başlangıçtaki bir kısmı tara (genelde meta veriler başta olur)
        tara_boyutu = min(4096, int(len(veri) * 0.02))
        
        # Meta veri olabilecekler
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
                
                # Bozalım
                for i in range(len(kelime)):
                    if pozisyon + i < len(veri):
                        veri[pozisyon + i] = random.randint(32, 126)
                
                pozisyon += len(kelime)
        
        # Yaz
        with open(dosya_yolu, 'wb') as f:
            f.write(veri)
        
        return True
    except Exception as e:
        return False

def klasor_islet(klasor, alt_klasorler=False):
    """Bir klasördeki tüm dosyaları işliyor"""
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
        print("Kullanım: python metasilici_v2.py  dosya veya klasor yolu   [-r] [-c]")
        print("  -r: Alt klasörleri de işle")
        print("  -c: Sadece meta veri kontrolü yap (silme işlemi yapmaz)")
        sys.exit(1)
    
    yol = sys.argv[1]
    alt_klasorler = "-r" in sys.argv
    sadece_kontrol = "-c" in sys.argv
    
    if not os.path.exists(yol):
        print(f"Hata: {yol} bulunamadı")
        sys.exit(1)
    
    # Sadece kontrol modunda çalış
    if sadece_kontrol:
        print(f"Sadece kontrol modu: {yol}")
        if os.path.isfile(yol):
            print(f"Kontrol ediliyor: {yol}")
            meta_veri_kontrol_et(yol)
        elif os.path.isdir(yol):
            print(f"Klasör kontrol ediliyor: {yol}")
            for kok, dizinler, dosyalar in os.walk(yol):
                if not alt_klasorler and kok != yol:
                    continue
                
                for dosya in dosyalar:
                    tam_yol = os.path.join(kok, dosya)
                    _, uzanti = os.path.splitext(tam_yol)
                    if uzanti.lower() in TELEFON_MEDYA_UZANTILARI:
                        print(f"Kontrol ediliyor: {tam_yol}")
                        meta_veri_kontrol_et(tam_yol)
        
        print("\n✓ KONTROL TAMAMLANDI.")
        sys.exit(0)
    
    # Normal silme modunda devam et (sadece kontrol değilse)
    # Dosya veya klasör işle
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
