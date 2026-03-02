# boardkarte.py
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from io import BytesIO
import datetime

# Zuordnung Klassen -> Sektionsbereiche
def get_sektion_range(klasse: str):
    """
    Prototype & ProModified: Sektion 2–11
    Fun-Cup & Junior-Cup:    Sektion 1–8
    alle anderen:            Sektion 1–2
    """
    if not klasse:
        return list(range(1, 3))

    k = klasse.lower().strip()
    if "prototype" in k or "promodified" in k:
        return list(range(2, 12))
    if "fun" in k or "junior" in k:
        return list(range(1, 9))
    # Standard, Original, Modified etc.
    return list(range(1, 3))


def draw_header(c, w, h, daten, logo_path=None):
    """
    Kopfbereich wie auf der Karte: Fahrer, Beifahrer, Fahrzeug, Klasse, Startnummer etc.
    'daten' ist ein dict mit möglichen Keys:
    fahrer, beifahrer, fahrzeug, klasse, startnummer, lauf, veranstalter
    """
    c.setFont("Helvetica-Bold", 11)

    # rechter Block (wie auf deinem Bild am Rand)
    x = w - 80*mm
    y = h - 20*mm
    line_h = 6*mm

    def label(text, value, offset):
        c.drawString(x, y - offset, f"{text}")
        c.setFont("Helvetica", 11)
        c.drawString(x + 25*mm, y - offset, value or "")
        c.setFont("Helvetica-Bold", 11)

    label("Fahrer:",      daten.get("fahrer", ""))
    label("Beifahrer:",   daten.get("beifahrer", ""), line_h*1)
    label("Fahrzeug:",    daten.get("fahrzeug", ""),  line_h*2)
    label("Startnr.:",    daten.get("startnummer", ""), line_h*3)
    label("Gruppe:",      daten.get("klasse", ""),    line_h*4)
    label("Lauf:",        daten.get("lauf", ""),      line_h*5)
    label("Veranstalter:",daten.get("veranstalter", ""), line_h*6)

    # Logo (optional) unten rechts
    if logo_path:
        try:
            c.drawImage(logo_path, w-70*mm, 10*mm, width=60*mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Datum oben links
    c.setFont("Helvetica", 9)
    c.drawString(15*mm, h-15*mm, datetime.date.today().strftime("Datum: %d.%m.%Y"))


def draw_table(c, sektionen):
    """
    Zeichnet die Haupttabelle mit Fehlerarten vs. Sektionen.
    sektionen: Liste von Sektionsnummern (z.B. [2..11] oder [1..8])
    Layout ist an dein Foto angelehnt, aber technisch vereinfacht.
    """

    w, h = landscape(A4)

    # Tabelle startet ca. links/unten
    left = 15*mm
    top = h - 60*mm
    col_width = 12*mm
    first_col_width = 70*mm
    last_col_width = 18*mm

    # Fehlerzeilen (vereinfachter Auszug, kannst du nach Bedarf anpassen)
    rows = [
        ("Sektion nicht befahren / nicht durchfahren Tor", "50"),
        ("Nicht durchfahren Tor", "50"),
        ("Rückwärts", "3"),
        ("Toreinfahrt berühren", "2"),
        ("Absperrband berühren", "1"),
        ("Absperrband umfahren", "6"),
        ("Toreinfahrt umfahren", "6"),
        ("Rückwärts (zweite Spalte)", "3"),
        ("Summe der Fehlerpunkte pro Sektion", ""),
    ]

    num_rows = len(rows)
    num_sek = len(sektionen)

    # Kopfzeile: leere Zelle + Sektionsnummern + Summe
    c.setFont("Helvetica-Bold", 9)
    c.rect(left, top, first_col_width + num_sek*col_width + last_col_width, - (num_rows+1)*7*mm)

    # Kopfzeilen
    c.drawString(left+2, top-5, "Fehler / Sektion")
    for i, s in enumerate(sektionen):
        x = left + first_col_width + i*col_width
        c.drawCentredString(x + col_width/2, top-5, str(s))
    # Summe-Header
    x_sum = left + first_col_width + num_sek*col_width
    c.drawCentredString(x_sum + last_col_width/2, top-5, "Σ")

    # horizontale Linien
    row_height = 7*mm
    y = top - row_height
    c.setFont("Helvetica", 8)

    for label, punkte in rows:
        # Text-Zelle
        c.line(left, y, left + first_col_width + num_sek*col_width + last_col_width, y)
        c.drawString(left+2, y - row_height + 3*mm, label)
        if punkte:
            c.drawRightString(left + first_col_width - 2, y - row_height + 3*mm, punkte)

        # vertikale Linien für jede Sektion + Summe
        for i in range(num_sek+2):  # sektionen + summe + Grenze
            x = left + first_col_width + i*col_width
            if i == num_sek:  # Summe-Spalte beginnt breiter
                x = left + first_col_width + num_sek*col_width
                c.line(x, top, x, top - (num_rows+1)*row_height)
                break
            c.line(x, top, x, top - (num_rows+1)*row_height)

        y -= row_height


def draw_footer(c):
    """Unterschriftsfelder unten wie auf der Karte (vereinfacht)."""
    w, h = landscape(A4)
    base_y = 25*mm

    c.setFont("Helvetica", 9)

    # Links: Unterschrift Fahrer / Unterschrift Streckenposten
    c.drawString(15*mm, base_y + 10*mm, "Unterschrift Fahrer")
    c.line(15*mm, base_y + 8*mm, 70*mm, base_y + 8*mm)

    c.drawString(80*mm, base_y + 10*mm, "Unterschrift Streckenposten")
    c.line(80*mm, base_y + 8*mm, 135*mm, base_y + 8*mm)

    # Rechts: Gesamtsumme / HCF / Punkte
    c.drawString(150*mm, base_y + 10*mm, "Gesamtsumme:")
    c.line(150*mm, base_y + 8*mm, 190*mm, base_y + 8*mm)

    c.drawString(150*mm, base_y + 4*mm, "HCF:")
    c.line(150*mm, base_y + 2*mm, 170*mm, base_y + 2*mm)

    c.drawString(175*mm, base_y + 4*mm, "Punkte:")
    c.line(175*mm, base_y + 2*mm, 195*mm, base_y + 2*mm)


def generate_boardcard(daten: dict, logo_path: str | None = None) -> bytes:
    """
    Erzeugt eine Boardkarte als PDF-Bytes.
    'daten' sollte enthalten:
      - fahrer
      - beifahrer
      - fahrzeug
      - klasse
      - startnummer
      - lauf
      - veranstalter
    logo_path: Pfad zu deinem DGM-Logo (optional)
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    w, h = landscape(A4)

    klasse = daten.get("klasse", "")
    sektionen = get_sektion_range(klasse)

    draw_header(c, w, h, daten, logo_path=logo_path)
    draw_table(c, sektionen)
    draw_footer(c)

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
