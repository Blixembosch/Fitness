# ATES FAM Fitness Geliştirme ve Dokümantasyon Kuralları

Bu kurallar ATES FAM Fitness projesindeki tüm kodlama, tasarım, test ve dağıtım adımlarında zorunludur.

## 1. Mimari ve Tasarım Prensipleri
- **Sadelik ve Tutarlılık:** Antrenman ve diğer tüm sekmeler, Plan sayfasındaki sakin, minimalist ve nötr estetiği (`.exgrid` ve `.exrow` kart yapısı) 1:1 korumalıdır. Gereksiz iç içe butonlar, parlak neon renkler ve karmaşık container blokları kullanılmaz.
- **Kalıcı Veri Yönetimi (GitHub Data Branch):**
  - Tüm kullanıcı verileri (kalori hedefleri, vücut ağırlıkları, antrenman/set kayıtları, Cronometer girdileri) yerel SQLite (`data/fitness.db`) ve GitHub üzerindeki bağımsız `data` branch'inde (`origin/data` -> `fitness.sql`) SQL formatında saklanır.
  - Streamlit Cloud container yeniden başlatmalarında veya yeni pushlarda veriler `data` branch'indeki `fitness.sql` üzerinden otomatik restore edilir; kod içine asla geçici statik varsayılanlar ezilerek yazılmaz.

## 2. Otomatik Test ve Regresyon Zorunluluğu
- Yapılan her fonksiyonel veya görsel değişiklikten sonra test paketi headless olarak çalıştırılmalıdır:
  ```bash
  /usr/local/bin/python3 -c "..." (veya test runner)
  ```
- Tüm birim testleri (WCAG kontrast, Cronometer ayrıştırma, program mantığı, beslenme hesapları) ve Streamlit `AppTest` fonksiyonel testleri (tüm 5 sayfanın hatasız render edilmesi) %100 yeşil olmadan değişiklik tamamlanamaz.

## 3. Doğrudan Commit ve Push Akışı
- Testler başarıyla geçtikten sonra değişiklikler kullanıcıdan onay beklemeden doğrudan anlamlı Conventional Commits mesajlarıyla commit edilmeli ve `origin/main` branch'ine pushlanmalıdır.
- Veri şeması veya kalıcı veri değiştiğinde `origin/data` branch'ine `fitness.sql` senkronizasyonu eksiksiz yapılmalıdır.

## 4. Dokümantasyonun Sürekli Güncel Tutulması
- Yapılan her yapısal ve fonksiyonel değişiklikte ilgili `.md` dokümanları (başta `README.md` olmak üzere) otomatik olarak kod ile eş zamanlı güncellenmelidir.
