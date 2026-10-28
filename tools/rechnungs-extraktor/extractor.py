"""Liest Rechnungen (PDF/Bild) per OpenAI aus und liefert strukturierte Daten."""
import base64
import csv
import io
import json
import os

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
FIELDS = ["datum", "rechnungsnummer", "lieferant", "netto", "mwst_satz", "mwst_betrag", "brutto", "waehrung"]

PROMPT = (
    "Lies diese Rechnung aus und antworte ausschließlich mit einem JSON-Objekt mit den Schlüsseln: "
    "datum (YYYY-MM-DD), rechnungsnummer, lieferant, netto, mwst_satz (Prozent), mwst_betrag, brutto, "
    "waehrung (z. B. EUR). Beträge als Zahlen mit Punkt als Dezimaltrenner. "
    "Fehlende oder unleserliche Werte als null, nichts erfinden."
)

DEMO_ROWS = [
    ("2026-09-03", "RE-2026-0412", "Baustoffhandel Müller GmbH", 420.17, 19, 79.83, 500.00),
    ("2026-09-11", "20260917", "Büro & Mehr e. K.", 84.03, 19, 15.97, 100.00),
    ("2026-09-24", "R-88213", "Stadtwerke Glauchau", 112.15, 7, 7.85, 120.00),
]


SERVICE = "rechnungs-extraktor"


def get_key():
    """Key aus Umgebungsvariable, sonst aus dem System-Schlüsselbund."""
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    try:
        import keyring
        return keyring.get_password(SERVICE, "openai")
    except Exception:
        return None


def save_key(key: str) -> None:
    import keyring
    keyring.set_password(SERVICE, "openai", key)


def delete_key() -> None:
    import keyring
    try:
        keyring.delete_password(SERVICE, "openai")
    except keyring.errors.PasswordDeleteError:
        pass


def demo_mode() -> bool:
    return not get_key()


def _demo(index: int) -> dict:
    d, nr, lief, netto, satz, mwst, brutto = DEMO_ROWS[index % len(DEMO_ROWS)]
    return dict(datum=d, rechnungsnummer=nr, lieferant=lief, netto=netto, mwst_satz=satz,
                mwst_betrag=mwst, brutto=brutto, waehrung="EUR")


def extract(filename: str, data: bytes, mimetype: str, index: int = 0) -> dict:
    """Gibt ein Dict mit den FIELDS zurück. Ohne API-Key: Demo-Daten."""
    if demo_mode():
        return _demo(index)

    from openai import OpenAI

    b64 = base64.b64encode(data).decode()
    if mimetype == "application/pdf":
        part = {"type": "input_file", "filename": filename, "file_data": f"data:application/pdf;base64,{b64}"}
    else:
        part = {"type": "input_image", "image_url": f"data:{mimetype};base64,{b64}"}

    resp = OpenAI(api_key=get_key()).responses.create(
        model=MODEL,
        input=[{"role": "user", "content": [{"type": "input_text", "text": PROMPT}, part]}],
        text={"format": {"type": "json_object"}},
    )
    raw = json.loads(resp.output_text)
    return {k: raw.get(k) for k in FIELDS}


NUMERIC = {"netto", "mwst_satz", "mwst_betrag", "brutto"}


def _cell(key, value):
    """Zahlenfelder mit Dezimalkomma (deutsches Excel), alles andere unverändert."""
    if value is None:
        return ""
    if key in NUMERIC:
        return str(value).replace(".", ",")
    return value


def to_csv(rows: list[dict]) -> bytes:
    """Semikolon-getrennt mit BOM, damit deutsches Excel es direkt richtig öffnet."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Datum", "Rechnungsnr.", "Lieferant", "Netto", "MwSt-Satz %", "MwSt", "Brutto", "Währung"])
    for r in rows:
        w.writerow([_cell(k, r.get(k)) for k in FIELDS])
    return buf.getvalue().encode("utf-8-sig")
