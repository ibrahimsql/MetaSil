## Önemli Uyarı

**Türkiye Cumhuriyeti'ndeki son olaylar yüzünden insanlar eylem yapıyor, ancak bunları sosyal medyada paylaşırken meta verilerini silmeyi unutuyorlar.** Bu durum, kişilerin konum bilgilerinin ve kimliklerinin istemeden de olsa ifşa olmasına neden olabiliyor. Bu tool, özellikle bu gibi durumlarda fotoğraf ve videoların güvenle paylaşılabilmesi için geliştirilmiştir.

## Neden Bu Araca İhtiyaç Var?

Günümüzde sosyal medyada paylaşılan fotoğraf ve videolar, farkında olmadığımız birçok meta veri içerir:

- **Konum bilgileri** (tam GPS koordinatları)
- **Cihaz bilgileri** (telefonunuzun markası, modeli)
- **Tarih ve saat** (fotoğrafın ne zaman çekildiği)
- **Kamera ayarları** ve diğer teknik detaylar

Bu bilgiler, özellikle toplumsal olaylarda çekilen ve paylaşılan medyalarda ciddi gizlilik ve güvenlik sorunlarına yol açabilir. Sosyal medyada paylaşılan bir fotoğrafta, **farkında olmadan konum bilgilerinizi** veya kişisel bilgilerinizi ifşa ediyor olabilirsiniz.

## Bu Araç Ne Yapar?

MetaSil, telefonla çekilen fotoğraf, video ve ses dosyalarından tüm meta verileri tamamen siler:

- ✓ GPS ve konum bilgilerini yok eder
- ✓ Cihaz marka/model bilgilerini temizler
- ✓ Tarih ve zaman bilgilerini değiştirir
- ✓ Kullanıcı kimliğini belirleyebilecek tüm bilgileri siler

## Nasıl Kullanılır?

### Termux (Android) Kurulumu:

1. Termux uygulamasını telefonunuza yükleyin
2. Termux'u açın ve şu komutları çalıştırın:
   ```
   pkg update && pkg upgrade -y
   pkg install python -y
   termux-setup-storage
   ```
3. Scripti telefonunuza indirin veya oluşturun:
   ```
   git clone https://github.com/ibrahimsql/MetaSil.git
   
   cd MetaSil
   ```
4. Çalıştırma izni verin:
   ```
   chmod +x metasilici.py
   ```

### Kullanım:

```bash
# Tek bir dosya için:
python metasilici.py /sdcard/DCIM/Camera/fotograf.jpg

# Bir klasör için:
python metasilici.py /sdcard/DCIM/Camera/

# Alt klasörler dahil bir klasör için:
python metasilici.py /sdcard/DCIM/ -r
```

## Güvenlik İçin Öneriler

- **Paylaşmadan önce mutlaka meta verileri silin**. Özellikle toplumsal olaylarda çekilen fotoğraflar konum bilgisi içerebilir.
  
- **Fotoğrafları doğrudan sosyal medya uygulamalarından paylaşmayın**. Önce bu araçla temizleyin, sonra paylaşın.
  
- **Yüzleri ve belirleyici özellikleri bulanıklaştırın**. Bu script sadece meta verileri siler, görüntü içeriğini değiştirmez.

- **Güvenlik için VPN kullanmayı unutmayın**. Meta veriler silinse bile, IP adresiniz takip edilebilir.

## Teknik Detaylar

- Hiçbir ek kütüphane gerektirmez, tamamen Python'un standart modülleriyle çalışır
- Desteklenen dosya formatları:
  - **Fotoğraf**: .jpg, .jpeg, .png, .heic, .heif
  - **Video**: .mp4, .mov, .3gp, .mkv
  - **Ses**: .mp3, .m4a, .aac, .wav
- İşlem öncesi tüm dosyalar yedeklenir, sorun olursa orijinal dosyalar geri yüklenir

## Yasal Uyarı

Bu araç, kişisel mahremiyet ve güvenliği korumak amacıyla tasarlanmıştır. Yasaların izin verdiği kapsamda ve etik kurallara uygun şekilde kullanılmalıdır. Kullanıcılar, bu aracı kendi yasal sorumlulukları dahilinde kullanmalıdır.

## Toplumsal Sorumluluk Notu

Toplumsal olaylar sırasında çektiğiniz ve paylaştığınız fotoğraf ve videolar, sizin veya başkalarının güvenliğini riske atabilir. Bu tool, teknolojinin zorlu zamanlarda insanları korumaya yardımcı olması için geliştirilmiştir. Medya paylaşırken her zaman kendinizin ve başkalarının güvenliğini ön planda tutun.
