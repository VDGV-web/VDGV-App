import streamlit as st
import json
import os
from datetime import datetime
from PIL import Image

STARTSEITE_DATEI = "daten/startseite.json"
TERMINE_DATEI = "daten/termine.json"

# --- Helper: JSON laden ---
def lade_json(datei, default):
    if os.path.exists(datei):
        with open(datei, "r") as f:
            return json.load(f)
    return default

def lade_termine():
    if os.path.exists(TERMINE_DATEI):
        with open(TERMINE_DATEI, "r") as f:
            return json.load(f)
    return []

def show(termine):
    st.title("🏁 DGM - Deutsche Geländewagenmeisterschaft")

    startseite = lade_json(STARTSEITE_DATEI, {"aktuelles": []})
    aktuelles = startseite.get("aktuelles", [])

    st.divider()
    col1, col2 = st.columns(2)

    # --- Linke Spalte: Aktuelles ---
    with col1:
        st.subheader("📰 Aktuelles")
        if aktuelles:
            for info in aktuelles:
                st.markdown(
                    f'<div style="background-color:#fff3cd; padding:10px; border-radius:5px; margin-bottom:5px;">'
                    f"🛈 {info if isinstance(info, str) else info.get('text', '')}"
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("Noch keine aktuellen Informationen vorhanden.")

    # --- Rechte Spalte: Termine ---
    with col2:
        st.subheader("📅 Nächste Termine")
        if termine:
            try:
                termine.sort(key=lambda x: tuple(map(int, x['datum'].split('.')[::-1])))
            except:
                pass
            for i, t in enumerate(termine[:5]):
                if i < 2:  # Die nächsten 2 Termine hervorheben
                    st.markdown(
                        f'<div style="background-color:#cce5ff; padding:5px; border-radius:5px; margin-bottom:5px;">'
                        f"<strong>{t['datum']} — {t['beschreibung']}</strong>"
                        f'</div>', 
                        unsafe_allow_html=True
                    )
                else:
                    st.info(f"{t['datum']} — {t['beschreibung']}")
        else:
            st.info("Noch keine Termine vorhanden.")

    st.divider()
    
    # --- Footer / VDGV-Website in grün ---
    st.markdown(
        '<div style="background-color:#d4edda; padding:10px; border-radius:5px; text-align:center;">'
        '<strong>Alle Termine und Informationen unter: <a href="https://www.vdgv.de" target="_blank">www.vdgv.de</a></strong>'
        '</div>',
        unsafe_allow_html=True
    )

    # --- Sponsor-Bereich ---
    st.divider()
    st.subheader("Unsere Sponsoren")

    sponsoren_logos = [
        "seiten/logos/4x4.png",
        "seiten/logos/Bausch.png",
        "seiten/logos/CST.png",
        "seiten/logos/fahrzeugtechnikjansen.jpg",
        "seiten/logos/kocher.png",
        "seiten/logos/koehler.jpg",
        "seiten/logos/Schmidt.jpg",
        "seiten/logos/Switchcamper.png",
        "seiten/logos/wassermann.png",
        "seiten/logos/Maxxis.png"
    ]

    vorhandene_logos = []
    fehlende_logos = []

    # Prüfen, ob die Logos existieren und valide sind
    for logo in sponsoren_logos:
        if os.path.exists(logo):
            try:
                img = Image.open(logo)
                img.verify()  # Prüft, ob es ein gültiges Bild ist
                vorhandene_logos.append(logo)
            except Exception:
                fehlende_logos.append(logo)
        else:
            fehlende_logos.append(logo)

    # Fehlende oder ungültige Logos melden
    for logo in fehlende_logos:
        st.warning(f"Logo nicht gefunden oder ungültig: {logo}")

    # Alle Logos in einer horizontalen Reihe anzeigen
    if vorhandene_logos:
        cols = st.columns(len(vorhandene_logos))
        for col, logo in zip(cols, vorhandene_logos):
            try:
                col.image(logo, width=80)  # Logos kleiner darstellen
            except Exception:
                col.write("Fehler beim Laden")

    # Optional: CSS Hover-Effekt für die Logos
    st.markdown("""
        <style>
        div[data-testid="stImage"] img:hover {
            transform: scale(1.05);
            transition: transform 0.3s;
        }
        </style>
        """, unsafe_allow_html=True)

