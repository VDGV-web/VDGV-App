import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

# --- Pfade ---
TERMINE_DATEI = "daten/termine.json"
STAMMDATEN_FILE = "daten/FahrzeugAbnahme_Stammdaten.xlsx"
ABNAHMEN_DIR = "abnahmen"
ABNAHMEN_IMG_DIR = os.path.join(ABNAHMEN_DIR, "images")

os.makedirs(ABNAHMEN_DIR, exist_ok=True)
os.makedirs(ABNAHMEN_IMG_DIR, exist_ok=True)

# --- Daten laden ---
def lade_termine():
    if os.path.exists(TERMINE_DATEI):
        with open(TERMINE_DATEI, "r") as f:
            return json.load(f)
    return []

def lade_stammdaten():
    if os.path.exists(STAMMDATEN_FILE):
        df = pd.read_excel(STAMMDATEN_FILE, dtype=str)
        return df.fillna("")
    return pd.DataFrame()

# --- Seite anzeigen ---
def show():
    st.title("🛠️ Sektionsabnahme")
    termine = lade_termine()
    stammdaten = lade_stammdaten()

    role = st.session_state.get("role", "gast")
    tabs = st.tabs(["Abnahme durchführen", "Abnahmen ansehen"])

    # ----------------- ABNAHME DURCHFÜHREN -----------------
    if role in ["admin", "klassensprecher"]:
        with tabs[0]:
            st.subheader("Abnahme durchführen")
            lauf_optionen = [f"{t['datum']} – {t['beschreibung']}" for t in termine]
            lauf = st.selectbox("Lauf auswählen", ["Bitte wählen..."] + lauf_optionen)

            startnummer = st.selectbox("Fahrer auswählen", ["Bitte wählen..."] + stammdaten["Startnummer"].tolist())
            if startnummer != "Bitte wählen...":
                fahrer = stammdaten[stammdaten["Startnummer"] == startnummer].iloc[0]
                st.markdown(f"**Name:** {fahrer['Vorname']} {fahrer['Nachname']}  \n**Klasse:** {fahrer['Klasse']}")

                sektionen = list(range(2, 12)) if "proto" in fahrer["Klasse"].lower() else list(range(1, 11))
                abnahme_data = {}

                for sek in sektionen:
                    with st.expander(f"Sektion {sek}", expanded=True):
                        abnahme_data[f"sektion_{sek}_text"] = st.text_area(
                            "Bemerkungen", key=f"{startnummer}_{sek}_text"
                        )
                        abnahme_data[f"sektion_{sek}_bilder"] = st.file_uploader(
                            "Bilder hochladen", accept_multiple_files=True, key=f"{startnummer}_{sek}_img"
                        )

                unterschrift = st.text_input("Unterschrift (Name)")

                if st.button("✅ Abnahme speichern"):
                    abnahme_record = {
                        "startnummer": startnummer,
                        "name": f"{fahrer['Vorname']} {fahrer['Nachname']}",
                        "klasse": fahrer["Klasse"],
                        "lauf": lauf,
                        "sektionen": {},
                        "unterschrift": unterschrift,
                        "datum": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    for sek in sektionen:
                        bilder = []
                        uploaded_files = abnahme_data.get(f"sektion_{sek}_bilder", [])
                        for file in uploaded_files:
                            safe_name = file.name.replace(" ", "_")
                            bild_pfad = os.path.join(ABNAHMEN_IMG_DIR, f"{startnummer}_{sek}_{safe_name}")
                            with open(bild_pfad, "wb") as f:
                                f.write(file.getbuffer())
                            bilder.append(bild_pfad)
                        abnahme_record["sektionen"][sek] = {
                            "text": abnahme_data.get(f"sektion_{sek}_text", ""),
                            "bilder": bilder,
                            "status": "Offen",
                            "kommentar": "",
                            "veranstalter_unterschrift": "",
                            "veranstalter_bilder": []
                        }

                    lauf_str = lauf.split("–")[0].strip()
                    abnahme_datei = os.path.join(ABNAHMEN_DIR, f"{startnummer}_{lauf_str}.json")
                    with open(abnahme_datei, "w", encoding="utf-8") as f:
                        json.dump(abnahme_record, f, indent=4, ensure_ascii=False)

                    st.success("Abnahme erfolgreich gespeichert!")

    # ----------------- ABNAHMEN ANSEHEN -----------------
    with tabs[1]:
        st.subheader("Abnahmen ansehen")
        abnahmen_files = [f for f in os.listdir(ABNAHMEN_DIR) if f.endswith(".json")]
        if not abnahmen_files:
            st.info("Noch keine Abnahmen vorhanden.")
        else:
            for file in sorted(abnahmen_files, reverse=True):
                pfad = os.path.join(ABNAHMEN_DIR, file)
                with open(pfad, "r", encoding="utf-8") as f:
                    record = json.load(f)

                with st.expander(f"{record['name']} ({record['klasse']}) – {record['lauf']}"):
                    st.markdown(f"📅 Datum: {record['datum']}")
                    st.markdown(f"✍️ Unterschrift Klassensprecher/in: {record.get('unterschrift','-')}")

                    for sek, sek_data in record["sektionen"].items():
                        st.markdown(f"**Sektion {sek}**: {sek_data['text']}")
                        for bild in sek_data["bilder"]:
                            if os.path.exists(bild):
                                st.image(bild, width=200)

                        # Veranstalter Bearbeitung nur wenn Klassensprecher etwas hinterlegt hat
                        if role == "veranstalter" and sek_data["text"]:
                            st.markdown("### Veranstalter Bearbeitung")
                            status = st.selectbox(f"Status Sektion {sek}", ["Offen", "Erledigt"],
                                                  index=["Offen", "Erledigt"].index(sek_data.get("status", "Offen")),
                                                  key=f"status_{file}_{sek}")
                            kommentar = st.text_area("Kommentar", value=sek_data.get("kommentar",""), key=f"kommentar_{file}_{sek}")
                            uploaded_files = st.file_uploader("Bilder hochladen", accept_multiple_files=True, key=f"v_img_{file}_{sek}")
                            unterschrift_v = st.text_input("Unterschrift Veranstalter (Pflichtfeld)",
                                                           value=sek_data.get("veranstalter_unterschrift",""),
                                                           key=f"unterschrift_{file}_{sek}")

                            # Bilder speichern
                            for file_u in uploaded_files:
                                safe_name = file_u.name.replace(" ", "_")
                                bild_pfad = os.path.join(ABNAHMEN_IMG_DIR, f"veranstalter_{record['startnummer']}_{sek}_{safe_name}")
                                with open(bild_pfad, "wb") as f_img:
                                    f_img.write(file_u.getbuffer())
                                if "veranstalter_bilder" not in sek_data:
                                    sek_data["veranstalter_bilder"] = []
                                sek_data["veranstalter_bilder"].append(bild_pfad)

                            # Änderungen speichern nur mit Unterschrift
                            if st.button("✅ Änderungen speichern", key=f"save_{file}_{sek}"):
                                if not unterschrift_v.strip():
                                    st.error("Bitte tragen Sie Ihre Unterschrift ein, um die Änderungen zu speichern!")
                                else:
                                    sek_data["status"] = status
                                    sek_data["kommentar"] = kommentar
                                    sek_data["veranstalter_unterschrift"] = unterschrift_v
                                    with open(pfad, "w", encoding="utf-8") as f_update:
                                        json.dump(record, f_update, indent=4, ensure_ascii=False)
                                    st.success(f"Sektion {sek} aktualisiert!")

                        # Klassensprecher kann nur lesen
                        elif role == "klassensprecher" and sek_data.get("veranstalter_unterschrift"):
                            st.markdown("### Veranstalter Ergänzungen (nur Ansicht)")
                            st.markdown(f"**Status:** {sek_data.get('status','-')}")
                            st.markdown(f"**Kommentar:** {sek_data.get('kommentar','-')}")
                            st.markdown(f"**Unterschrift Veranstalter:** {sek_data.get('veranstalter_unterschrift','-')}")
                            for bild in sek_data.get("veranstalter_bilder", []):
                                if os.path.exists(bild):
                                    st.image(bild, width=200)


