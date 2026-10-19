# Apple Health → Google Sheet otomasyonu

Apple Health'in buluta açık API'si yok; o yüzden **telefon** veriyi düzenli olarak senin
Google Sheet'ine yazar, uygulama da Sheet'i okur. Bir kez kurarsın, sonra otomatik çalışır.

Akış: **iOS Kısayol (otomasyon) → Google Apps Script (Sheet'e satır ekler) → Streamlit uygulaması (Sheet'i okur).**

Sheet: `1GnfbwWETyrNXJm_t5x0MrxrW_CmclH2MiQS8UuZf42M`

---

## 1) Google Apps Script (yazma ucu)

1. Sheet'i aç → **Uzantılar → Apps Script**.
2. Tüm kodu sil, aşağıdakini yapıştır → **Kaydet**:

```javascript
function doPost(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var d = JSON.parse(e.postData.contents);
  if (d.kind === 'weight') {
    tab(ss, 'Weight', ['date', 'weight_kg']).appendRow([d.date, d.weight]);
  } else if (d.kind === 'workout') {
    tab(ss, 'Workouts', ['date', 'type', 'minutes', 'kcal'])
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
```

3. **Dağıt → Yeni dağıtım → Tür: Web uygulaması.** "Şu kullanıcı olarak çalıştır: ben",
   "Erişimi olan: **Herkes**" → **Dağıt** → izinleri onayla → çıkan **Web uygulaması URL**'sini kopyala.

## 2) Sheet'i uygulamanın okuyabilmesi için

Sheet'te **Paylaş → Bağlantısı olan herkes: Görüntüleyen** açık olsun (zaten paylaştın).
Uygulama, `Weight` ve `Workouts` sekmelerini bu bağlantıdan okur.

## 3) iOS Kısayolu — Kilo (günlük otomasyon)

**Kısayollar → Otomasyon → + → Kişisel Otomasyon → Günün Saati** (ör. 08:00, her gün):
1. **Sağlık Örneklerini Bul**: Tür = *Vücut Kütlesi (Body Mass)*, Sırala = *Başlangıç Tarihi (En yeni)*, Limit = 1.
2. **Değişken Ayarla** → örnekten *Value* (kilo sayısı).
3. **Geçerli Tarih** → **Tarihi Biçimlendir** → `yyyy-MM-dd`.
4. **Sözlük**: `kind` = weight, `date` = (biçimli tarih), `weight` = (kilo değeri).
5. **URL İçeriğini Al**: URL = Apps Script web app URL, Yöntem = **POST**, İstek Gövdesi = **JSON** = (Sözlük).
6. "Çalıştırmadan önce sor" **kapalı**.

## 4) iOS Kısayolu — Spor/Padel (antrenman bitince)

**Otomasyon → + → Bir Antrenman bittiğinde** (ya da günlük):
1. **Antrenmanları Bul**: Bitiş Tarihi = *Bugün*.
2. **Her biri için tekrarla**:
   - **Sözlük**: `kind` = workout, `date` = bugünün `yyyy-MM-dd`'si, `type` = *Workout Type*,
     `minutes` = *Duration* (dakika), `kcal` = *Active Energy*.
   - **URL İçeriğini Al**: POST → JSON → Apps Script URL.

Padel, Apple Health'te çoğu zaman *Tennis* olarak görünür; uygulama bunu padel sayar.

---

Kurduktan sonra Beslenme sekmesinde **"🔗 Google Sheet senkron: … kilo · … padel"** satırını görmelisin.
