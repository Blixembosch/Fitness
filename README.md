# ATES FAM Fitness

Wegovy (GLP-1) sürecinde **kas kütlesini koruma/artırma, yağ yakımı ve metabolik sağlık takibi** için geliştirilmiş özel antrenman ve beslenme paneli. Streamlit ile çalışır, PC/Docker gerektirmez; Streamlit Community Cloud veya yerel tarayıcı üzerinden doğrudan kullanılır.

---

## Özellikler & Ekranlar

- **Ana Sayfa:** Üçlü aktivite halkaları (antrenman, protein, kalori hedefi), günün antrenman kartı, kilo değişimi, vücut kompozisyonu özeti ve 52 haftalık GitHub katkı grafiği (heatmap).
- **Plan:** 12 haftalık periodize program takvimi (Hazırlık, Temel, İnşa, Zirve fazları). Düşük eklem yüküyle eklem ve nabız hazırlığı, güç hareketleri ve antrenman sonu yağ yakım/soğuma adımları.
- **Antrenman:** Numaralandırılmış minimalist adımlar (1..9), egzersiz bazlı kas haritaları, dambıl ağırlık takibi ve tek tıkla kalıcı antrenman tamamlama/geri alma.
- **İstatistik:** Hafta, ay ve 3 aylık (ISO hafta numaralı) antrenman/padel dağılımı, haftalık % kilo kaybı güvenlik göstergesi (hızlı kas kaybı uyarısı) ve çalışılan kasların görsel anatomik haritası.
- **Beslenme:** Cronometer dışa aktarım dosyaları (dailysummary, exercises, biometrics) üzerinden kalori, protein, lif ve makro takibi; Wegovy doz/enjeksiyon bölgesi rotasyonu ve hedef kalori (2000 kcal) yönetimi.

---

## Antrenman Mimarisi (Wegovy Koruma Modu)

Her güç antrenmanı (Üst A, Alt A, Üst B), glikojen depolarını ve kas kütlesini optimize eden **3 aşamalı akışla** yürütülür:
1. **Adım 1 — Eliptik Isınma (5 dk):** Düşük eklem yüküyle nabız ve eklemleri hazırlar.
2. **Adım 2..N-2 — Güç & Hipertrofi:** Kas koruma ve artırma sinyali veren bileşik dambıl ve vücut ağırlığı egzersizleri.
3. **Son 2 Adım — Su Küreği (10 dk) + Eliptik (10 dk) Yağ Yakım Bitirişi:** Ağırlık sonrası glikojen azalmışken tam-vücut (sırt + core + bacak) metabolik yağ yakımı ve Zone-2 aktif soğuma.

---

## Veri Kalıcılığı (GitHub Data Branch Mimarisi)

Uygulama, **ATES FAM Budget** altyapısıyla aynı kurumsal kalıcılık sistemini kullanır:
- **Yerel Katman:** Anlık sayfa yenilemeleri (F5) ve oturumlar için `data/fitness.db` SQLite veritabanı.
- **Bulut Katmanı:** Streamlit Cloud sunucu güncellemelerinde veya yeni kod pushlarında verilerin asla kaybolmaması için tüm veritabanı SQL dökümü (`fitness.sql`) GitHub üzerindeki bağımsız [`data` branch'i](https://github.com/Blixembosch/fitness/tree/data) üzerinden çift yönlü otomatik senkronize edilir.

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
