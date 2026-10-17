# Prizma: Karar kimde? — çalıştırma

## A) İnternete koyma (Render, önerilen)

Oyun sabit bir adreste çalışır: herkes kendi internetinden girer, bilgisayarına bağlı değildir.

1. github.com'da ücretsiz hesap aç, **New repository** ile `article-quest` adlı boş bir depo oluştur.
2. Depo sayfasında **uploading an existing file** bağlantısına tıkla. Bu klasörün *içindeki* bütün dosya ve klasörleri sürükleyip bırak, **Commit changes**'e bas.
3. render.com'da GitHub hesabınla giriş yap.
4. **New → Blueprint** seç, `article-quest` deposunu bağla, **Apply**'a bas. (`render.yaml` her şeyi kendisi ayarlar.)
5. Birkaç dakika sonra `https://article-quest.onrender.com` gibi bir adres verir.
   - Yönetici ekranı: `https://<adresin>/yonetici`
   - Oyuncular: QR'ı okutur ya da `<adresin>` yazıp PIN girer.

Ücretsiz sürüm bir süre kullanılmazsa uyur; ilk açılış yaklaşık 1 dakika sürer.
Sunumdan 5 dakika önce yönetici sayfasını açman yeterli.

## B) Kendi bilgisayarında deneme

1. `py -m pip install -r requirements.txt`
2. `py app.py`
3. Tarayıcıda `http://localhost:5000/yonetici` adresini aç.

Bu modda telefonlar yalnızca bilgisayarla aynı Wi-Fi ağındaysa katılabilir.

## Tanıtım videosu

- Videoyu film sayfasındaki **Export** ile MP4 olarak indir, adını `tanitim.mp4` yapıp oyunun dosyalarının yanına yükle.
- **Oyunu başlat**'a basınca video projeksiyonda tam ekran oynar, bitince oyun başlar. **Videoyu geç** ile atlanabilir.
- Dosya yoksa oyun doğrudan başlar.

## Takımlar

- Kaç kişi katılırsa katılsın oyuncular otomatik olarak iki takıma (Kırmızı ve Mavi) bölünür.
- Takımlar kurulduktan sonra gelen kişi, oyun başlamadan küçük takıma eklenir.
- İçerik hazır onaylı gelir; istersen İçeriği onayla panelinden soru çıkarabilirsin.

## Süre ayarı

- Takım ekranındaki **Kısa mod** seçeneği ikinci vakayı (V3) çıkarır.
- **İçeriği onayla** panelinden yedek havuzdaki sahne, soru ve vakaları ekleyebilirsin.

## Testler

`py -m pytest tests`

## Kaynak doğrulama

`KAYNAK_DOGRULAMA.md`, `content.py`'den üretilir: `py tools/dogrulama_tablosu.py`
