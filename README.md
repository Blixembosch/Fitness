# ATES FAM Fitness

Wegovy (GLP-1) sürecinde **kas kütlesini koruma/artırma, yağ yakımı ve metabolik sağlık takibi** için geliştirilmiş özel antrenman ve beslenme paneli. Streamlit ile çalışır, PC/Docker gerektirmez; Streamlit Community Cloud veya yerel tarayıcı üzerinden doğrudan kullanılır.

---

## Özellikler & Ekranlar

- **Ana Sayfa:** Dörtlü aktivite halkaları (antrenman, dinamik padel, protein, kalori hedefi), tek tıkla Padel hızlı kaydı ve hedef ayarı, günün antrenman kartı, kilo değişimi, Wegovy mini-kartı, Google Takvim'den gelen günün maçı bilgisi ve 52 haftalık GitHub katkı grafiği (heatmap).
- **Plan:** 12 haftalık periodize program takvimi (Hazırlık, Temel, İnşa, Zirve fazları). Düşük eklem yüküyle eklem ve nabız hazırlığı, güç hareketleri ve antrenman sonu yağ yakım/soğuma adımları.
- **Antrenman:** Numaralandırılmış minimalist adımlar (1..9), egzersiz bazlı kas haritaları, dambıl ağırlık takibi, tek tıkla kalıcı antrenman tamamlama/geri alma ve esnek Padel seansı kaydı & hızlı hedef yönetimi.
- **İstatistik:** 25 Ekim 2026 resmi başlangıç tarihi bazlı dinamik filtreleme; hafta, ay ve 3 aylık (ISO hafta numaralı) antrenman/padel dağılımı, esnek padel hedeflerine göre güncellenen periyot barları, haftalık % kilo kaybı güvenlik göstergesi (hızlı kas kaybı uyarısı) ve çalışılan kasların görsel anatomik haritası.
- **Beslenme:** Cronometer dışa aktarım dosyaları (dailysummary, exercises, biometrics) üzerinden kalori, protein, lif ve makro takibi; Wegovy doz/enjeksiyon bölgesi rotasyonu, haftalık dinamik padel hedefi, Google Takvim iCal entegrasyonu ve kalori/protein yönetimi.

---

## Antrenman Mimarisi (Wegovy Koruma Modu)

Her güç antrenmanı (Üst A, Alt A, Üst B), glikojen depolarını ve kas kütlesini optimize eden **3 aşamalı akışla** yürütülür:
1. **Adım 1 — Eliptik Isınma (5 dk):** Düşük eklem yüküyle nabız ve eklemleri hazırlar.
2. **Adım 2..N-2 — Güç & Hipertrofi:** Kas koruma ve artırma sinyali veren bileşik dambıl ve vücut ağırlığı egzersizleri.
3. **Son 2 Adım — Su Küreği (10 dk) + Eliptik (10 dk) Yağ Yakım Bitirişi:** Ağırlık sonrası glikojen azalmışken tam-vücut (sırt + core + bacak) metabolik yağ yakımı ve Zone-2 aktif soğuma.

---

## Entegrasyonlar ve Veri Kalıcılığı

### 1. Google Takvim (Padel) Entegrasyonu
- Gizli iCal URL'si (`.streamlit/secrets.toml` veya Beslenme sekmesindeki ayar kutusu) ile Anıl'ın Padel maçları takvimden otomatik çekilir.
- **Akıllı Filtreleme:** Atlas'ın dersleri ("Padel Training for Atlas", çocuk, junior) otomatik elenir, programa ve hedeflere sadece Anıl'ın maçları yansıtılır.
- Ayrıntılı kurulum için: [Google Takvim Entegrasyon Kılavuzu](docs/google-calendar-sync.md).

### 2. Apple Health & Cronometer Senkronizasyonu
- Apple Health verileri Google Sheet köprüsü üzerinden anlık çekilir (kilo, adım, aktif kalori). Detaylar: [Apple Health Kurulum Kılavuzu](docs/health-sync.md).
- Cronometer dışa aktarımlarıyla mikro ve makro besin hedefleri takip edilir.

### 3. GitHub Data Branch SQL Kalıcılığı
- **Yerel Katman:** Anlık sayfa yenilemeleri için `data/fitness.db` SQLite veritabanı.
- **Bulut Katmanı:** Streamlit Cloud sunucu yeniden başlatmalarında veya yeni kod pushlarında verilerin asla kaybolmaması için tüm veritabanı SQL dökümü (`fitness.sql`) GitHub üzerindeki bağımsız [`data` branch'i](https://github.com/Blixembosch/fitness/tree/data) üzerinden çift yönlü otomatik senkronize edilir.

---

## Tasarım, Tema ve Erişilebilirlik Güvencesi

- **Karanlık / Aydınlık Mod:** `.streamlit/config.toml` dosyasında `base = "dark"` tanımlıdır.
- **Ergonomik Tipografi & Kompakt Yerleşim:** Arayüz yazı boyutları (13.5px baz, 23px h1, 12px kompakt alert kutuları) mobil ve masaüstünde göz yormayan, dengeli ve ergonomik bir hiyerarşide standartlaştırılmıştır; `st.info` ve uyarı kutuları ekranı kaplamayan şık kart formatına dönüştürülmüştür.
- **WCAG AA/AAA Kontrast:** Emotion sınıfları (`.e1fp86qc*`), sanal portal selectbox bileşenleri (`[data-baseweb="select"]`), calendar popover'ları özel CSS kurallarıyla koyu arka planda yüksek kontrastlı metin sağlayacak şekilde güvenceye alınmıştır.
- **HTML/CSS Enjeksiyon Güvenliği:** `st.html` ve arındırılmış CSS şablonları kullanılarak CommonMark markdown parser'ının stil etiketlerini metin/kod bloğu olarak ekranda sızdırması (`<style>` leaks) engellenmiştir.

---

## Test ve Kalite Güvencesi

Proje, 92 otomatik birim, erişilebilirlik ve 5 sayfanın CSS/bileşen bütünlüğünü denetleyen Streamlit `AppTest` fonksiyonel testi ile korunur:
```bash
/usr/local/bin/python3 run_tests.py
```

---

## Kurulum ve Çalıştırma

### Streamlit Community Cloud (Mobil / Web)
1. [share.streamlit.io](https://share.streamlit.io) üzerinden GitHub ile giriş yapın.
2. `Blixembosch/fitness` reposunu, `main` branch'ini ve `app.py` dosyasını seçip dağıtın.
3. Her `git push origin main` işlemi yeni sürümü otomatik olarak devreye alır; veriler `data` branch'inden korunur.

### Yerel Çalıştırma
```bash
pip install -r requirements.txt
streamlit run app.py
```
