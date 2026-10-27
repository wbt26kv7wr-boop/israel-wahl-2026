# Israel-Wahl 2026 · Mobilisierung

Live-Dashboard zur Wahlbeteiligung bei der Knesset-Wahl am 27.10.2026: Tempo-Index je Ort, Lager und Sektor, Karten, Sitzmodell, DE/EN/HE.

## Einrichtung (einmalig)
1. **Settings → Pages:** Source „Deploy from a branch“, Branch `main`, Ordner `/ (root)` → Save.
2. **Settings → Actions → General → Workflow permissions:** „Read and write permissions“ → Save.
3. **Actions → „Daten aktualisieren“ → Run workflow:** einmal manuell starten. Danach läuft es alle 10 Minuten.

Seite: `https://<benutzer>.github.io/israel-wahl-2026/`

Einbetten:
```html
<iframe src="https://<benutzer>.github.io/israel-wahl-2026/" style="width:100%;height:3200px;border:0" loading="lazy"></iframe>
```

## Dateien
- `index.html` – das Dashboard (lädt `data/*.json`, rechnet im Browser).
- `scripts/refresh.py` – holt die Live-Daten der Wahlkommission und schreibt `data/`.
- `.github/workflows/refresh.yml` – führt das Skript automatisch aus.

## Quellen
Zentrale Wahlkommission (mapvotes.bechirot.gov.il, media25.bechirot.gov.il), votes26.com (Sektoren, Prognosemethode), Natural Earth (Karte), Umfragen von Kan, Kanal 12, Kanal 13. Die Sitzverteilung ist ein einfaches Modell, keine Prognose.
