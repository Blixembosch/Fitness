# Apple Health → Google Sheet otomasyonu

Apple Health'in buluta açık API'si yok; telefon veriyi Google Sheet'e yazar, uygulama Sheet'i okur.

Akış: **iOS Kısayol (otomasyon) → Google Apps Script → Google Sheet (Weight / Daily / Workouts) → Streamlit uygulaması.**

Sheet: `1GnfbwWETyrNXJm_t5x0MrxrW_CmclH2MiQS8UuZf42M`

Toplanan veriler:
- **Weight** sekmesi — kilo (kg).
- **Daily** sekmesi — günlük: aktif kalori, egzersiz dakikası, adım, yürüme+koşu mesafesi.
- **Workouts** sekmesi — her antrenman: tür, süre, kalori (padel dahil).

---

## 1) Apps Script (yazma ucu) — güncel sürüm

Sheet → **Uzantılar → Apps Script** → hepsini sil, yapıştır → Kaydet. Sonra **Dağıt → Dağıtımları yönet →
(kalem) → Sürüm: Yeni sürüm → Dağıt** (zaten dağıttıysan yeni sürüm yayınla).

```javascript
function doPost(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var d = JSON.parse(e.postData.contents);
  if (d.kind === 'weight') {
    upsert(ss, 'Weight', ['date','weight_kg'], d.date, [d.date, d.weight]);
  } else if (d.kind === 'daily') {
    upsert(ss, 'Daily', ['date','active_kcal','exercise_min','steps','distance_km'],
           d.date, [d.date, d.active_kcal, d.exercise_min, d.steps, d.distance_km]);
  } else if (d.kind === 'workout') {
    tab(ss, 'Workouts', ['date','type','minutes','kcal'])
      .appendRow([d.date, d.type || '', d.minutes || '', d.kcal || '']);
  }
  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
function tab(ss, name, headers) {
  var sh = ss.getSheetByName(name);
  if (!sh) { sh = ss.insertSheet(name); sh.appendRow(headers); }
  return sh;
}
function upsert(ss, name, headers, dateVal, row) {           // tarih aynıysa satırı günceller
  var sh = tab(ss, name, headers);
  var vals = sh.getDataRange().getValues();
  for (var i = 1; i < vals.length; i++) {
    if (String(vals[i][0]) === String(dateVal)) {
      sh.getRange(i + 1, 1, 1, row.length).setValues([row]); return;
    }
  }
  sh.appendRow(row);
}
```

## 2) iOS Kısayolu — Günlük aktivite (tek otomasyon)

**Otomasyon → + → Günün Saati → 23:40, her gün → Run Immediately.** Her metrik için aynı 3 adım:
Find Health Samples → Get Numbers from Input → Calculate Statistics (Sum). Dört metriği kur, sonra tek POST.

Her metrik için:
1. **Find Health Samples** — Type = (aşağıdaki), **Start Date → is today**, Limit kapalı.
2. **Get Numbers from Input** ← Health Samples.
3. **Calculate Statistics** — Operation = **Sum**, Input = Numbers. Çıkanı değişkene al.

Metrikler ve Type değerleri:
- **Aktif kalori** → Type: **Active Energy** → değişken `AEnergy`
- **Egzersiz dakikası** → Type: **Apple Exercise Time** → `ExMin`
- **Adım** → Type: **Steps** → `Steps`
- **Mesafe** → Type: **Walking + Running Distance** (km) → `Dist`

Sonra:
4. **Format Date** — Current Date → `yyyy-MM-dd` → `DateStr`
5. **Get Contents of URL** — exec URL · **POST** · **JSON**:
   - `kind` (Text) = `daily`
   - `date` (Text) = `DateStr`
   - `active_kcal` (Number) = `AEnergy`
   - `exercise_min` (Number) = `ExMin`
   - `steps` (Number) = `Steps`
   - `distance_km` (Number) = `Dist`

## 3) iOS Kısayolu — Workout'lar (gerçek süre/kalori)

**"Find Workouts" aksiyonu varsa** (Search Actions → `workout`):
1. Otomasyon → Günün Saati → 23:45 → Run Immediately.
2. **Find Workouts** — End Date → is today.
3. **Repeat with Each** (Workouts) → **Get Contents of URL** POST JSON:
   - `kind` = `workout`
   - `date` = (Repeat Item → End Date, `yyyy-MM-dd` formatlı)
   - `type` = Repeat Item → **Workout Type**
   - `minutes` = Repeat Item → **Duration** (dakika)
   - `kcal` = Repeat Item → **Active Energy**

**"Find Workouts" yoksa (padel için tek dokunuş):**
- Yeni kısayol "Padel" → **Current Date** → **Format Date** `yyyy-MM-dd` → **Get Contents of URL** POST JSON:
  `kind`=workout, `date`=Formatted Date, `type`=Padel, `minutes`=(elle ya da Health'ten).
- Ana Ekrana ekle (tek dokunuş) veya **"Vardığımda → padel kulübü"** otomasyonu ile otomatik.

## Kontroller
- Sheet **Paylaş → Bağlantısı olan herkes: Görüntüleyen** açık olmalı (uygulama okuyabilsin).
- Kurduktan sonra uygulamada **Beslenme → "🔗 Google Sheet senkron: … kilo · … padel · … workout · … günlük aktivite"**,
  ve Ana Sayfa'da aktivite kartı (adım / aktif kcal / egzersiz dk / km) dolar. "🔄 Şimdi senkronla" ile anında tazelenir.
