# Rechnungs-Extraktor

Rechnungen (PDF, PNG, JPG, WebP) hochladen, per OpenAI auslesen, in der Tabelle korrigieren und als Excel-CSV exportieren.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export OPENAI_API_KEY=sk-...   # ohne Key läuft ein Demo-Modus mit Beispieldaten
.venv/bin/python app.py        # http://localhost:5050
```

- Modell per `OPENAI_MODEL` änderbar (Standard `gpt-4.1-mini`).
- CSV: Semikolon, UTF-8 mit BOM, Dezimalkomma, öffnet direkt im deutschen Excel.
- Hinweis: Rechnungen werden an OpenAI gesendet, das gehört in die Datenschutzerklärung des Kunden.
