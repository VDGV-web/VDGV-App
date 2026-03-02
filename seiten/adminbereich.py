import streamlit as st
import json
import os
from datetime import datetime

# Pfade
TERMINE_DATEI = "daten/termine.json"
STARTSEITE_DATEI = "daten/startseite.json"

# --- Helper: JSON laden/speichern ---
def lade_json(datei, default):
    if os.path.exists(datei):
        with open(datei, "r") as f:
            try:
                return json.load(f)
            except Exception as e:
                st.error(f"❌ Fehler beim Laden von JSON: {e}")
                return default
    return default

def speichere_json(datei, data):
    with open(datei, "w") as f:
        json.dump(data, f, indent=4)

# --- Adminbereich anzeigen ---
def show():
    st.title("🛠 Adminbereich – Inhalte verwalten")

    # --- Tabs ---
    tab_termine, tab_infos = st.tabs(["📅 Termine", "📰 Startseiteninfos"])

    # ------------------ Termine ------------------
    with tab_termine:
        st.subheader("Termine verwalten")
        termine = lade_json(TERMINE_DATEI, [])

        # Termine nach Datum sortieren
        try:
            termine.sort(key=lambda x: datetime.strptime(x['datum'], "%d.%m.%Y"))
        except:
            pass

        # Neuen Termin hinzufügen
        neuer_datum = st.date_input("Neuen Termin hinzufügen: Datum", key="neu_datum")
        neue_beschreibung = st.text_input("Beschreibung", key="neu_beschreibung")
        wichtig = st.checkbox("Wichtig markieren", key="neu_wichtig")
        if st.button("Termin hinzufügen", key="hinzufuegen_termin"):
            termine.append({
                "datum": neuer_datum.strftime("%d.%m.%Y"),
                "beschreibung": neue_beschreibung,
                "wichtig": wichtig
            })
            speichere_json(TERMINE_DATEI, termine)
            st.success("Termin hinzugefügt!")

        st.divider()

        # Bestehende Termine bearbeiten/löschen
        if termine:
            i = 0
            while i < len(termine):
                t = termine[i]
                col1, col2, col3, col4 = st.columns([2,4,1,1])
                with col1:
                    try:
                        datum = st.date_input(
                            f"Datum {i+1}",
                            value=datetime.strptime(t.get("datum", "01.01.2000"), "%d.%m.%Y"),
                            key=f"datum_{i}"
                        )
                    except Exception:
                        datum = datetime.today()
                with col2:
                    beschreibung = st.text_input(
                        f"Beschreibung {i+1}",
                        value=t.get("beschreibung", ""),
                        key=f"beschreibung_{i}"
                    )
                with col3:
                    wichtig_checkbox = st.checkbox(
                        "Wichtig",
                        value=t.get("wichtig", False),
                        key=f"wichtig_{i}"
                    )
                with col4:
                    if st.button("Löschen", key=f"loeschen_{i}"):
                        termine.pop(i)
                        speichere_json(TERMINE_DATEI, termine)
                        st.success("Termin gelöscht!")
                        continue  # Index nicht erhöhen, da ein Eintrag gelöscht wurde

                # Änderungen speichern
                termine[i]["datum"] = datum.strftime("%d.%m.%Y")
                termine[i]["beschreibung"] = beschreibung
                termine[i]["wichtig"] = wichtig_checkbox
                i += 1

            if st.button("Alle Termine speichern", key="speichern_termine"):
                speichere_json(TERMINE_DATEI, termine)
                st.success("Termine aktualisiert!")
        else:
            st.info("Noch keine Termine vorhanden.")

    # ------------------ Startseiteninfos ------------------
    with tab_infos:
        st.subheader("Startseiteninformationen verwalten")
        startseite = lade_json(STARTSEITE_DATEI, {"aktuelles": []})
        aktuelles = startseite.get("aktuelles", [])

        # Alte String-Einträge in Dictionary konvertieren
        for i, info in enumerate(aktuelles):
            if isinstance(info, str):
                aktuelles[i] = {"text": info, "wichtig": False}

        # Neues Aktuelles hinzufügen
        neue_info = st.text_input("Neue Information hinzufügen", key="neu_info")
        wichtig_info = st.checkbox("Wichtig markieren", key="neu_info_wichtig")
        if st.button("Hinzufügen", key="hinzufuegen_info"):
            if neue_info.strip():
                aktuelles.append({"text": neue_info.strip(), "wichtig": wichtig_info})
                startseite["aktuelles"] = aktuelles
                speichere_json(STARTSEITE_DATEI, startseite)
                st.success("Information hinzugefügt!")

        st.divider()

        # Bestehende Informationen bearbeiten/löschen
        if aktuelles:
            i = 0
            while i < len(aktuelles):
                info = aktuelles[i]
                col1, col2, col3 = st.columns([5,1,1])
                with col1:
                    neuer_text = st.text_input(f"Info {i+1}", value=info.get("text",""), key=f"info_{i}")
                with col2:
                    wichtig_checkbox = st.checkbox("Wichtig", value=info.get("wichtig", False), key=f"wichtig_info_{i}")
                with col3:
                    if st.button("Löschen", key=f"loeschen_info_{i}"):
                        aktuelles.pop(i)
                        startseite["aktuelles"] = aktuelles
                        speichere_json(STARTSEITE_DATEI, startseite)
                        st.success("Information gelöscht!")
                        continue  # Index nicht erhöhen

                aktuelles[i]["text"] = neuer_text
                aktuelles[i]["wichtig"] = wichtig_checkbox
                i += 1

            if st.button("Alle Informationen speichern", key="speichern_infos"):
                startseite["aktuelles"] = aktuelles
                speichere_json(STARTSEITE_DATEI, startseite)
                st.success("Informationen aktualisiert!")
        else:
            st.info("Noch keine Informationen vorhanden.")
