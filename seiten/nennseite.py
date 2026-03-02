import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime  # <-- hinzugefügt

# --- Pfade anpassen (alle Dateien im Ordner 'daten') ---
BASE_DIR = r"D:\App_DGM\daten"
FAHRER_DATEI = os.path.join(BASE_DIR, "nennungen_fahrer.json")
MANNSCHAFT_DATEI = os.path.join(BASE_DIR, "nennungen_mannschaft.json")
TERMINE_DATEI = os.path.join(BASE_DIR, "termine.json")
FAHRZEUGE_CSV = os.path.join(BASE_DIR, "fahrzeuge.csv")
KLASSEN_CSV = os.path.join(BASE_DIR, "klassen.csv")
MANNSCHAFTEN_CSV = os.path.join(BASE_DIR, "mannschaften.csv")

# --- Helper: JSON laden/speichern ---
def lade_json(datei):
    if os.path.exists(datei):
        with open(datei, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception as e:
                st.error(f"❌ Fehler beim Laden von JSON: {e}")
                return []
    return []

def speichere_json(datei, daten):
    with open(datei, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=4, ensure_ascii=False)

# --- CSV laden (robust gegen fehlerhafte Zeilen, erkennt Trennzeichen automatisch) ---
def lade_csv(datei, erwartete_spalten, fallback=[]):
    if not os.path.exists(datei):
        return fallback
    try:
        # Trennzeichen automatisch erkennen
        with open(datei, "r", encoding="utf-8") as f:
            first_line = f.readline()
            sep = ";" if ";" in first_line else ","
        df = pd.read_csv(datei, sep=sep, engine='python', encoding="utf-8", on_bad_lines='skip')
        df.columns = [c.strip() for c in df.columns]

        for spalte in erwartete_spalten:
            matches = [c for c in df.columns if c.lower() == spalte.lower()]
            if matches:
                werte = df[matches[0]].dropna().astype(str).map(str.strip).unique()
                return sorted(set(werte))
        return fallback
    except Exception as e:
        return fallback

# --- Läufe aus Termine laden ---
def lade_lauf_optionen():
    termine = lade_json(TERMINE_DATEI)
    optionen = []
    for t in termine:
        if isinstance(t, dict) and "datum" in t and "beschreibung" in t:
            optionen.append(f"{t['datum']} – {t['beschreibung']}")
    return sorted(optionen)

# --- Hauptseite ---
def show():
    st.title("🏎️ Nennseite")
    st.write("Hier können Fahrer:innen und Mannschaften ihre Nennung zur DGM abgeben.")

    # CSV-Daten laden mit Fallback
    klassen = lade_csv(KLASSEN_CSV, ["Klasse", "Klassen"], fallback=["Serienklasse", "Prototypenklasse", "Spezialklasse", "Buggys"])
    fahrzeuge = lade_csv(FAHRZEUGE_CSV, ["Fahrzeug", "Fahrzeuge", "Auto"], fallback=["Unbekannt"])
    mannschaften = lade_csv(MANNSCHAFTEN_CSV, ["Verein", "Mannschaft", "Mannschaften", "Club"], fallback=["Kein Verein gelistet"])

    # Laufoptionen dynamisch laden
    lauf_optionen = lade_lauf_optionen()

    # Tabs
    tab1, tab2 = st.tabs(["🧍 Fahrer-Nennung", "🏁 Mannschafts-Nennung"])

    # --- Fahrer-Nennung ---
    with tab1:
        st.subheader("🧍 Fahrer:innen-Nennung")
        with st.form("fahrer_formular"):
            lauf = st.selectbox("Lauf auswählen", ["Bitte wählen..."] + lauf_optionen)
            name = st.text_input("Name des Fahrers / der Fahrerin")
            klasse = st.selectbox("Klasse", ["Bitte wählen..."] + klassen)
            startnummer = st.text_input("Startnummer")
            auto = st.selectbox("Fahrzeug", ["Bitte wählen..."] + fahrzeuge)
            verein = st.selectbox("Verein", ["Bitte wählen..."] + mannschaften)
            beifahrer = st.text_input("Beifahrer:in (optional)")

            absenden = st.form_submit_button("✅ Nennung absenden")
            if absenden:
                if not name or klasse=="Bitte wählen..." or auto=="Bitte wählen..." or verein=="Bitte wählen..." or lauf=="Bitte wählen...":
                    st.error("❗ Bitte alle Pflichtfelder ausfüllen!")
                else:
                    nennungen = lade_json(FAHRER_DATEI)
                    nennungen.append({
                        "name": name,
                        "klasse": klasse,
                        "startnummer": startnummer,
                        "auto": auto,
                        "verein": verein,
                        "beifahrer": beifahrer,
                        "lauf": lauf,
                        "nenn_datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # <-- hinzugefügt
                    })
                    speichere_json(FAHRER_DATEI, nennungen)
                    st.success(f"Nennung von **{name}** erfolgreich gespeichert! ✅")

    # --- Mannschafts-Nennung ---
    with tab2:
        st.subheader("🏁 Mannschafts-Nennung")
        with st.form("mannschaft_formular"):
            lauf = st.selectbox("Lauf auswählen", ["Bitte wählen..."] + lauf_optionen, key="team_lauf")
            verein = st.selectbox("Verein", ["Bitte wählen..."] + mannschaften)
            verantwortlicher = st.text_input("Verantwortliche Person")
            
            st.markdown("**Fahrer:innen der Mannschaft (max. 6)**")
            fahrer = [st.text_input(f"Fahrer:in {i+1}", key=f"fahrer_{i+1}") for i in range(6)]
            fahrer = [f for f in fahrer if f]

            absenden_team = st.form_submit_button("✅ Mannschaft anmelden")
            if absenden_team:
                if not verein or not verantwortlicher or lauf=="Bitte wählen..." or len(fahrer)==0:
                    st.error("❗ Bitte alle Pflichtfelder ausfüllen!")
                else:
                    teams = lade_json(MANNSCHAFT_DATEI)
                    teams.append({
                        "verein": verein,
                        "verantwortlicher": verantwortlicher,
                        "fahrer": fahrer,
                        "lauf": lauf,
                        "nenn_datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # <-- hinzugefügt
                    })
                    speichere_json(MANNSCHAFT_DATEI, teams)
                    st.success(f"Mannschaft **{verein}** erfolgreich für **{lauf}** angemeldet! 🏁")

    # --- Übersicht ---
    st.divider()
    with st.expander("📋 Bereits gespeicherte Nennungen anzeigen"):
        fahrer_data = lade_json(FAHRER_DATEI)
        team_data = lade_json(MANNSCHAFT_DATEI)
        if fahrer_data:
            st.subheader("Fahrer:innen")
            for f in fahrer_data:
                st.markdown(
                    f"- **{f['name']}** ({f['klasse']}, Startnr. {f['startnummer']}) – "
                    f"{f['verein']} – Lauf: {f.get('lauf','-')} – "
                    f"🕓 Nennung: {f.get('nenn_datum','unbekannt')}"
                )
        else:
            st.info("Noch keine Fahrer:innen-Nennungen vorhanden.")

        if team_data:
            st.subheader("Mannschaften")
            for t in team_data:
                st.markdown(
                    f"- **{t['verein']}** – {t['lauf']} (Verantwortlich: {t['verantwortlicher']}) "
                    f"🕓 Nennung: {t.get('nenn_datum','unbekannt')}"
                )
                st.markdown(f"  Fahrer:innen: {', '.join(t['fahrer'])}")
