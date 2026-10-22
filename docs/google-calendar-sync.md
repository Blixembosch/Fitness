# Google Takvim (Padel) Entegrasyonu

ATES FAM Fitness, Google Takvim'inizdeki Padel maçlarını ve antrenmanlarını otomatik olarak algılar; haftalık antrenman planınızı, günlük bildirim rozetlerini ve hedeflerinizi dinamik olarak günceller.

---

## 1. `.streamlit/secrets.toml` Yapılandırması

`.streamlit/secrets.toml` dosyanıza aşağıdaki satırı ekleyin:

```toml
# Google Takvim Gizli iCal URL'si (.ics)
GOOGLE_CALENDAR_ICAL_URL = "https://calendar.google.com/calendar/ical/SENIN_EMAIL%40gmail.com/private-xxxxxxxxxxxxxxxx/basic.ics"
```

*(İsteğe bağlı olarak `GCAL_ICAL_URL` değişken adı da desteklenir).*

---

## 2. Google Takvim'den Gizli iCal Linki Nasıl Alınır?

1. Masaüstü tarayıcınızdan **[Google Takvim](https://calendar.google.com)**'i açın.
2. Sol menüdeki **"Takvimlerim"** (*My calendars*) altında kendi takviminizin yanındaki **üç noktaya (⋮)** tıklayın.
3. **"Ayarlar ve paylaşım"** (*Settings and sharing*) seçeneğine tıklayın.
4. Sol menüden veya sayfayı aşağı kaydırarak **"Takvimi entegre et"** (*Integrate calendar*) başlığını bulun.
5. **"iCal biçiminde gizli adres"** (*Secret address in iCal format*) kutusundaki URL'yi kopyalayın.

> [!WARNING]
> *"Genel adres"* değil, mutlaka **"Gizli adres"** kutusundaki linki kopyalayın. Gizli link takviminizi herkese açmadan sadece sizin uygulamanızın okumasını sağlar.

---

## 3. Alternatif: Uygulama İçi Arayüzden Yapıştırma

`.streamlit/secrets.toml` dosyasını düzenlemek istemiyorsanız:
1. Uygulamada **Beslenme** sekmesine gidin.
2. **"⚙️ Hedef ayarları"** menüsünü açın.
3. **"📅 Google Takvim Entegrasyonu"** başlığı altındaki kutucuğa gizli iCal linkinizi yapıştırın.
4. Sistem linki yerel veritabanınıza kaydeder ve maçlarınızı anında çekmeye başlar.

---

## 4. Nasıl Çalışır?

- Takvim etkinlik başlıklarında `Padel`, `Padel Maçı`, `Peak Padel`, `Padel w/ Mert` veya `Tennis` kelimeleri arandığında seans otomatik yakalanır.
- Tek seferlik maçlar ve haftalık tekrarlanan etkinlikler (`RRULE`) desteklenir.
- Etkinlik saati (örn. `19:30`) ve kulüp konumu (örn. `Peak Padel Club`) Ana Sayfa ve Antrenman sekmesinde gösterilir.
- Takvimde Padel olan günlerde günün programı otomatik olarak Padel odaklı dinamik moda geçer.
- Performans için takvim verileri 5 dakikalık akıllı önbellekte (`@st.cache_data`) tutulur.
