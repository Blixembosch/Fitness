# ATES FAM Fitness Geliştirme ve Dokümantasyon Kuralları

Bu kurallar ATES FAM Fitness projesindeki tüm kodlama, tasarım, test ve dağıtım adımlarında zorunludur.

## 1. Mimari ve Tasarım Prensipleri
- **Sadelik ve Tutarlılık:** Antrenman ve diğer tüm sekmeler, Plan sayfasındaki sakin, minimalist ve nötr estetiği (`.exgrid` ve `.exrow` kart yapısı) 1:1 korumalıdır. Gereksiz iç içe butonlar, parlak neon renkler ve karmaşık container blokları kullanılmaz.
- **Karanlık/Aydınlık Tema & WCAG Kontrast Güvencesi:**
  - Streamlit varsayılan açık arayüzünden (`base = "light"`) kaynaklanabilecek beyaz kutu/beyaz metin ve koyu metin/koyu arka plan hataları kesinlikle engellenmelidir.
  - `.streamlit/config.toml` içinde `base = "dark"` ve nötr koyu arka planlar (`backgroundColor = "#0e1117"`, `secondaryBackgroundColor = "#161b22"`, `textColor = "#e6edf3"`) tanımlı olmalıdır.
  - Emotion CSS sınıfları (`.e1fp86qc*`), `[role="combobox"]`, `[data-baseweb="select"]`, takvim/popover pencereleri ve sanal portal listeleri için `lib/ui.py` içinde derin CSS override'ları ve evrensel kontrast fail-safe kuralları (`background-color: var(--card-bg) !important; color: var(--text) !important;`) eksiksiz uygulanmalı ve test edilmelidir.
- **Kalıcı Veri Yönetimi (GitHub Data Branch):**
  - Tüm kullanıcı verileri (kalori hedefleri, vücut ağırlıkları, antrenman/set kayıtları, Cronometer girdileri, Google Takvim iCal linki) yerel SQLite (`data/fitness.db`) ve GitHub üzerindeki bağımsız `data` branch'inde (`origin/data` -> `fitness.sql`) SQL formatında saklanır.
  - Streamlit Cloud container yeniden başlatmalarında veya yeni pushlarda veriler `data` branch'indeki `fitness.sql` üzerinden otomatik restore edilir; kod içine asla geçici statik varsayılanlar ezilerek yazılmaz.
- **Resmi Başlangıç Tarihi ve Veri Filtreleme:**
  - Programın resmi başlangıç tarihi **25 Ekim 2026** (kullanıcı ayarlarından 26 Ekim veya başka bir tarihe esnetilebilir) olarak kabul edilir.
  - Başlangıç tarihinden önceki geçmiş veriler (örneğin önceki test CSV'leri veya eski kayıtlar) istatistiklerde, GitHub katkı heatmap'inde, periyot barlarında ve trend grafiklerinde gösterilmez; temiz bir başlangıç baz alınır.

## 2. Otomatik Test ve Regresyon Zorunluluğu
- Yapılan her fonksiyonel, görsel veya veri modeli değişikliğinden sonra test paketi headless olarak çalıştırılmalıdır:
  ```bash
  /usr/local/bin/python3 run_tests.py
  ```
- Tüm birim testleri (WCAG kontrast ve erişilebilirlik, Cronometer ayrıştırma, program mantığı, beslenme hesapları, Google Takvim senkronu ve Atlas filtreleme) ve Streamlit `AppTest` fonksiyonel testleri (tüm 5 sayfanın hatasız render edilmesi) %100 yeşil (pass) olmadan değişiklik tamamlanamaz.

## 3. Doğrudan Commit ve Push Akışı
- Testler %100 başarıyla geçtikten sonra değişiklikler kullanıcıdan onay beklemeden doğrudan anlamlı Conventional Commits mesajlarıyla commit edilmeli ve `BypassSandbox: true` yetkisiyle `origin/main` branch'ine pushlanmalıdır.
- Veri şeması veya kalıcı veri değiştiğinde `origin/data` branch'ine `fitness.sql` senkronizasyonu eksiksiz yapılmalıdır.

## 4. Dokümantasyonun Otomatik ve Eş Zamanlı Güncellenmesi (Tüm MD Dosyaları)
- Kodda, mimaride, veri şemasında, entegrasyonlarda veya ekranlarda yapılan her değişiklikte, projede yer alan ilgili tüm Markdown (`.md`) dosyaları (`README.md`, `docs/*.md`, vb.) otomatik olarak ve kod ile eş zamanlı olarak güncellenmelidir:
  - Yeni bir özellik veya entegrasyon eklendiğinde (örn. Google Takvim, Padel hedefi, iCal senkronu, 25 Ekim başlangıç filtresi) kullanım kılavuzu ve teknik detaylar anında dokümante edilir.
  - Eski, çelişkili veya geçerliliğini yitirmiş bilgiler (örn. lisans referansları, eski tarihler, geçici oturum içi saklama notları) anında temizlenir.
  - Kod değişikliği ile dokümantasyon değişikliği aynı commit akışında bir arada tamamlanır.
