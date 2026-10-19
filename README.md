# Fitness

Kendi arayüzümüz — Wegovy sürecinde **kas koruma + ilerleme takibi** için. Streamlit ile yazıldı,
PC/Docker gerektirmez: Streamlit Community Cloud'a bağla, telefondan URL ile kullan.

openGym'den yalnızca **egzersiz verisi** alındı (hangi hareket hangi kası çalıştırır, ekipman).
Gym Visual animasyonları openGym'e özel lisanslı olduğundan **bundle edilmedi**; onların yerine
kendi **kas haritamız** gösteriliyor.

## Ekranlar
- **Ana Sayfa** — üç aktivite halkası (antrenman / protein / kalori), bugünkü plan, kilo.
- **Plan** — haftalık antrenman düzeni.
- **Antrenman** — egzersiz ekle, set/kg/tekrar logla; her hareketin kas haritası.
- **İstatistik** — hafta/ay özeti, kilo trendi, çalışılan kasların haritası.
- **Beslenme** — Cronometer CSV yükle; kalori/protein/makro; kilo kaydı.
- **Egzersizler** — 5600+ hareket; ara/filtrele; kas haritası + birincil/ikincil kaslar.

## Streamlit Cloud'a deploy (PC gerekmez)
1. [share.streamlit.io](https://share.streamlit.io) → GitHub ile giriş.
2. **New app** → repo: bu repo, branch: `main`, main file: `app.py` → **Deploy**.
3. Verilen URL'yi telefonda ana ekrana ekle. Her `git push` otomatik yeniden deploy eder.

## Durum (Faz 1)
Veri şimdilik **oturum içinde** tutulur (sayfa yenilenince sıfırlanır). Sıradaki adım kalıcılık:
Google Sheets ile kayıt + Apple Health kilonun Shortcut ile aynı Sheet'e otomatik yazılması.

## Çalıştırma (yerel, opsiyonel)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Veri / lisans
Egzersiz–kas eşlemesi openGym (AGPL-3.0) / `hasaneyldrm/exercises-dataset` kaynaklıdır. Görsel/
animasyon medyası bu repoda yoktur.
