# 📈 Borsapy ile OOP Mimarisinde Borsa Otomasyonu

Bu proje, **Aydın Adnan Menderes Üniversitesi Söke İşletme Fakültesi Yönetim Bilişim Sistemleri Bölümü** bünyesinde yürütülen **YBS470 - Bitirme Çalışması** dersi kapsamında geliştirilmiş terminal tabanlı bir finansal takip ve analiz otomasyonudur.

## 🎓 Akademik Künye
* **Üniversite:** Aydın Adnan Menderes Üniversitesi
* **Fakülte / Bölüm:** Söke İşletme Fakültesi / Yönetim Bilişim Sistemleri
* **Ders:** YBS470 - Bitirme Çalışması (2026)
* **Proje Adı:** Borsapy Kütüphanesi Kullanılarak Nesne Yönelimli Programlama (OOP) Mimarisiyle Terminal Tabanlı Borsa Otomasyonu Geliştirilmesi
* **Öğrenci:** Berkant KARAÇAY (No: 223201064)
* **Danışman:** Prof. Dr. Sertan ALKAN

---

## 🚀 Proje Hakkında
Bu otomasyon; canlı ve geçmiş finansal piyasa verilerini tek bir terminal arayüzünden izlemek, teknik analiz taramaları yapmak ve portföy takibini gerçekleştirmek amacıyla **Python 3.14** çalışma zamanı ortamında kararlı çalışacak şekilde geliştirilmiştir. 

Yazılım mimarisi tamamen **Nesne Yönelimli Programlama (OOP)** prensiplerine (Soyutlama, Kalıtım, Polimorfizm, Kapsülleme) dayalı olarak kurgulanmıştır.

### 🏗️ OOP Mimari Yapısı
```text
FinansalEnstruman (ABC - Soyut Sınıf)
 ├── Hisse        ← (borsapy.Ticker entegrasyonu)
 ├── Doviz        ← (borsapy.FX entegrasyonu)
 │    └── Emtia   ← (Doviz sınıfından türetilmiş alt sınıf)
 ├── Kripto       ← (borsapy.Crypto entegrasyonu)
 ├── YatirimFonu  ← (borsapy.Fund entegrasyonu)
 └── Endeks       ← (borsapy.Index entegrasyonu)

Yardımcı Sistem Modülleri (Türemsiz / Kompozisyon):
 ├── Enflasyon    ← (TCMB Makro Veri Servisi)
 ├── VIOP         ← (İş Yatırım VİOP Servisi)
 └── Portfoy      ← (Çoklu Lot İzleme ve Maliyet Yönetimi)
```

---

## 🛠️ Sistem Özellikleri ve Menü Yapısı
Otomasyon dinamik menüsü üzerinden şu işlevleri sunmaktadır:
1. **Hisse Senedi İşlemleri:** BIST hisselerinin anlık fiyatları, derinlik analizi ve Matplotlib tabanlı grafik görselleştirmesi.
2. **Döviz Kurları:** 65+ döviz kurunun canlı takibi.
3. **Altın & Emtia:** Gram altın, ons altın, gümüş, platin takibi (Özel sembol çökme düzeltmeli).
4. **Kripto Para:** BtcTurk API entegrasyonuyla majör kripto varlık takibi.
5. **Yatırım Fonu:** TEFAS verileri üzerinden fon performans analizi.
6. **Endeks Analizi:** 79 farklı BIST endeksinin takibi.
7. **Enflasyon Verileri:** TCMB üzerinden resmi enflasyon serileri.
8. **VİOP:** Vadeli İşlem ve Opsiyon Piyasası verileri.
9. **Portföy Yönetimi:** Kişisel lot ekleme, maliyet hesaplama ve kar/zarar durum takibi.
10. **Tarama & Korelasyon:** Teknik indikatörler (RSI, SMA, MACD, Bollinger Bands, Williams %R) ile piyasa taraması ve varlıklar arası korelasyon analizi.

---

## 📦 Kurulum ve Çalıştırma

### Gereksinimler
Sistemin çalışması için gerekli kütüphaneleri terminalinizde aşağıdaki komutla kurabilirsiniz:

```bash
pip install borsapy rich matplotlib pandas numpy mplcursors
```

### Çalıştırma
Gereksinimler yüklendikten sonra projeyi ana dizinde şu komutla başlatabilirsiniz:

```bash
python borsaotomasyon.py
```

---

## 📂 Depo (Repository) İçeriği
* `borsaotomasyon.py` - Projenin tüm OOP mimarisini ve arayüzünü barındıran ana kaynak kod dosyası.
* `Berkant_Karacay_223201064_YBS470_Detayli_Bitirme_Raporu.docx` - Akademik yazım kurallarına uygun hazırlanan resmi bitirme tezi raporu.
* `README.md` - Proje tanıtım ve kılavuz belgesi (Bu dosya).
* `.gitignore` - Gereksiz sistem ve önbellek dosyalarını filtreleme yapılandırması.
