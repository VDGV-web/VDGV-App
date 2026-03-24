# Datei: D:\App_DGM\seiten\fahrzeugabnahme.py

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import json
import base64
from supabase_client import get_supabase


def show():
   
    # --------------------
    # Rollenprüfung
    # --------------------
    role = st.session_state.get("role", "")
    if role not in ["admin", "admin2", "abnahme", "buero"]:
        st.error("Keine Berechtigung für Fahrzeugabnahme.")
        return

    # --------------------
    # Seiteneinstellungen
    # --------------------
    try:
        st.set_page_config(page_title="Fahrzeugabnahme DGM", layout="wide")
    except Exception:
        pass

    # --------------------
    # Pfade
    # --------------------
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    reglement_file = os.path.join(BASE_DIR, "daten", "VDGV_Reglement_Vergleich_2025.xlsx")
    termine_file = os.path.join(BASE_DIR, "daten", "termine.json")
    nennungen_fahrer_file = os.path.join(BASE_DIR, "daten", "nennungen_fahrer.json")
    ABNAHMEN_ROOT = os.path.join(BASE_DIR, "Abnahmen")
    logo_path = os.path.join(BASE_DIR, "VDGV_Logo.png")

    # --------------------
    # Kopfbereich
    # --------------------
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        if os.path.exists(logo_path):
            st.image(logo_path, width=120)
    with col_title:
        st.title("Deutsche Geländewagen Meisterschaft – Fahrzeugabnahme DGM")

    # --------------------
    # Helper: JSON
    # --------------------
    def load_json(path, default=None):
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    # --------------------
    # Stammdaten aus Supabase laden
    # --------------------
    def load_stammdaten():
        try:
            sb = get_supabase()
            response = sb.table("fahrer").select("*").execute()
            data = response.data if response.data else []

            if not data:
                return pd.DataFrame(columns=[
                    "Vorname", "Nachname", "Startnummer", "Klasse",
                    "Lizenz", "Fahrzeug", "Verein", "Abnahme_Historie"
                ])

            df_local = pd.DataFrame(data)

            rename_map = {
                "vorname": "Vorname",
                "nachname": "Nachname",
                "startnummer": "Startnummer",
                "klasse": "Klasse",
                "lizenz": "Lizenz",
                "fahrzeug": "Fahrzeug",
                "verein": "Verein",
                "abnahme_historie": "Abnahme_Historie"
            }
            df_local = df_local.rename(columns=rename_map)

            for c in [
                "Vorname", "Nachname", "Startnummer", "Klasse",
                "Lizenz", "Fahrzeug", "Verein", "Abnahme_Historie"
            ]:
                if c not in df_local.columns:
                    df_local[c] = ""

            for c in df_local.columns:
                df_local[c] = df_local[c].astype(str).str.strip()

            return df_local.reset_index(drop=True)

        except Exception as e:
            st.error(f"Fehler beim Laden der Stammdaten aus Supabase: {e}")
            return pd.DataFrame(columns=[
                "Vorname", "Nachname", "Startnummer", "Klasse",
                "Lizenz", "Fahrzeug", "Verein", "Abnahme_Historie"
            ])

    def next_free_startnummer(df_local):
        try:
            nums = pd.to_numeric(
                df_local["Startnummer"].astype(str).replace("", pd.NA),
                errors="coerce"
            ).dropna().astype(int)
            return int(nums.max() + 1) if not nums.empty else 1
        except Exception:
            return 1

    def save_new_fahrer_supabase(neuer_fahrer: dict):
        try:
            sb = get_supabase()
            payload = {
                "vorname": str(neuer_fahrer.get("Vorname", "")).strip(),
                "nachname": str(neuer_fahrer.get("Nachname", "")).strip(),
                "startnummer": str(neuer_fahrer.get("Startnummer", "")).strip(),
                "klasse": str(neuer_fahrer.get("Klasse", "")).strip(),
                "lizenz": str(neuer_fahrer.get("Lizenz", "")).strip().lower() in ["true", "1", "yes", "ja"],
                "fahrzeug": str(neuer_fahrer.get("Fahrzeug", "")).strip(),
                "verein": str(neuer_fahrer.get("Verein", "")).strip(),
                "abnahme_historie": str(neuer_fahrer.get("Abnahme_Historie", "")).strip()
            }
            sb.table("fahrer").insert(payload).execute()
            return True
        except Exception as e:
            st.error(f"Fehler beim Speichern des Fahrers in Supabase: {e}")
            return False

    def update_abnahme_historie_supabase(startnr, klasse, neuer_eintrag):
        try:
            sb = get_supabase()

            response = (
                sb.table("fahrer")
                .select("abnahme_historie,startnummer,klasse")
                .eq("startnummer", str(startnr).strip())
                .eq("klasse", str(klasse).strip())
                .limit(1)
                .execute()
            )

            data = response.data if response.data else []

            if data:
                alter_hist = str(data[0].get("abnahme_historie", "") or "").strip()

                if not alter_hist:
                    neue_hist = neuer_eintrag
                else:
                    neue_hist = f"{alter_hist} | {neuer_eintrag}"

                (
                    sb.table("fahrer")
                    .update({"abnahme_historie": neue_hist})
                    .eq("startnummer", str(startnr).strip())
                    .eq("klasse", str(klasse).strip())
                    .execute()
                )
            else:
                st.warning(
                    f"Kein Fahrer-Datensatz für Startnummer {startnr} / Klasse {klasse} in Supabase gefunden. "
                    "Abnahme wurde als JSON gespeichert, Historie konnte aber nicht aktualisiert werden."
                )

        except Exception as e:
            st.error(f"Fehler beim Aktualisieren der Abnahme-Historie in Supabase: {e}")

    df = load_stammdaten()

    # --------------------
    # Reglement laden
    # --------------------
    if os.path.exists(reglement_file):
        try:
            reglement_df = pd.read_excel(reglement_file, sheet_name=0)
            reglement_df.columns = reglement_df.columns.astype(str).str.strip()
        except Exception as e:
            st.error(f"Fehler beim Einlesen der Reglement-Datei: {e}")
            reglement_df = None
    else:
        st.warning("Reglement-Datei nicht gefunden.")
        reglement_df = None

    # --------------------
    # Klassenfarben
    # --------------------
    klassen_farben = {
        "Original": "#1E90FF",
        "Standard": "#FFFFFF",
        "Modified": "#FFD700",
        "ProModified": "#000000",
        "Prototype": "#FF4B4B",
        "Junior-Cup": "#8A2BE2",
        "Fun-Cup": "#00C853",
        "Offene Klasse": "#FF8C00"
    }

    def anzeigen_klassenbalken(klasse):
        farbe = klassen_farben.get(str(klasse).strip(), "#CCCCCC")
        rahmenfarbe = "#D3D3D3" if farbe == "#FFFFFF" else farbe
        textfarbe = "black" if farbe == "#FFFFFF" else "white"
        st.markdown(
            f"""
            <div style="height:40px;background-color:{farbe};border:2px solid {rahmenfarbe};
            border-radius:8px;margin-bottom:10px;text-align:center;line-height:40px;
            font-weight:bold;color:{textfarbe};">
                {str(klasse).upper() if klasse else 'KLASSE UNBEKANNT'}
            </div>
            """,
            unsafe_allow_html=True
        )

    def zeige_fahrer_info(fahrer):
        with st.expander("Fahrerinformationen", expanded=True):
            st.write(f"**Vorname:** {fahrer.get('Vorname', '')}")
            st.write(f"**Nachname:** {fahrer.get('Nachname', '')}")
            st.write(f"**Startnummer:** {fahrer.get('Startnummer', '')}")
            st.write(f"**Klasse:** {fahrer.get('Klasse', '')}")
            st.write(f"**Fahrzeug:** {fahrer.get('Fahrzeug', '')}")
            liz = str(fahrer.get("Lizenz", "")).strip().lower()
            st.write(f"**Lizenz:** {'Ja' if liz in ['true', '1', 'yes', 'ja'] else 'Nein'}")
            st.write(f"**Verein:** {fahrer.get('Verein', 'Keine Angabe')}")
            hist = str(fahrer.get("Abnahme_Historie", "")).strip()
            st.write(f"**Abnahme-Historie:** {hist if hist else 'Keine'}")

    # --------------------
    # Fahrer suchen & auswählen
    # --------------------
    def suche_und_waehle_fahrer(df_local, suchbegriff, key_prefix):
        if suchbegriff:
            search_clean = str(suchbegriff).strip()

            treffer = df_local[
                df_local["Vorname"].astype(str).str.strip().str.contains(search_clean, case=False, na=False) |
                df_local["Nachname"].astype(str).str.strip().str.contains(search_clean, case=False, na=False) |
                df_local["Startnummer"].astype(str).str.strip().str.contains(search_clean, case=False, na=False)
            ]

            if not treffer.empty:
                options = [
                    f"{r['Vorname']} {r['Nachname']} ({r['Klasse']}) [#{r['Startnummer']}]"
                    for _, r in treffer.iterrows()
                ]
                selected_opt = st.selectbox("Fahrer auswählen:", options, key=f"{key_prefix}_select")

                startnr = selected_opt.split("#")[-1].strip("]").strip()
                klasse = selected_opt.split("(")[-1].split(")")[0].strip()

                fahrer_row = df_local[
                    (df_local["Startnummer"].astype(str).str.strip() == str(startnr).strip()) &
                    (df_local["Klasse"].astype(str).str.strip() == klasse)
                ].iloc[0]

                fahrer = fahrer_row.to_dict()
                st.session_state["selected_fahrer"] = fahrer
                anzeigen_klassenbalken(fahrer.get("Klasse", ""))
                zeige_fahrer_info(fahrer)
                return fahrer
            else:
                st.warning("Kein Fahrer gefunden.")
        return None

    # --------------------
    # PDF / Excel Export
    # --------------------
    styles_global = getSampleStyleSheet()

    def pdf_fahrer(fahrer_info, abnahmen_list):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        elements.append(
            Paragraph(
                f"Abnahmehistorie: {fahrer_info.get('Vorname', '')} {fahrer_info.get('Nachname', '')}",
                styles_global["Heading2"]
            )
        )
        elements.append(Spacer(1, 8))

        for abnahme_data in abnahmen_list:
            elements.append(
                Paragraph(
                    f"{abnahme_data.get('Datum', '')} – {abnahme_data.get('Typ', '')}",
                    styles_global["Heading3"]
                )
            )
            elements.append(
                Paragraph(
                    f"Abnehmende Person: {abnahme_data.get('Unterschrift', '–')}",
                    styles_global["Normal"]
                )
            )
            for bauteil, daten in abnahme_data.get("Ergebnisse", {}).items():
                elements.append(
                    Paragraph(
                        f"{bauteil} – {daten.get('Status', '')}",
                        styles_global["Normal"]
                    )
                )
                if daten.get("Bemerkung"):
                    elements.append(
                        Paragraph(
                            f"Bemerkung: {daten.get('Bemerkung', '')}",
                            styles_global["Normal"]
                        )
                    )
            elements.append(Spacer(1, 10))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    def excel_fahrer(fahrer_info, abnahmen_list):
        rows = []
        for abnahme_data in abnahmen_list:
            datum = abnahme_data.get("Datum", "")
            abn_typ = abnahme_data.get("Typ", "")
            unterschrift = abnahme_data.get("Unterschrift", "–")

            for bauteil, daten in abnahme_data.get("Ergebnisse", {}).items():
                rows.append({
                    "Vorname": fahrer_info.get("Vorname", ""),
                    "Nachname": fahrer_info.get("Nachname", ""),
                    "Startnummer": fahrer_info.get("Startnummer", ""),
                    "Klasse": fahrer_info.get("Klasse", ""),
                    "Datum": datum,
                    "Typ": abn_typ,
                    "Abnehmende Person": unterschrift,
                    "Bauteil": bauteil,
                    "Status": daten.get("Status", ""),
                    "Bemerkung": daten.get("Bemerkung", "")
                })

        df_out = pd.DataFrame(rows)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_out.to_excel(writer, index=False, sheet_name="Historie")
        buffer.seek(0)
        return buffer

    def pdf_alle_fahrer(df_all):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        data_all = [["Vorname", "Nachname", "Startnummer", "Klasse", "Letzte Abnahme"]]
        for _, row in df_all.iterrows():
            letzte = row.get("Abnahme_Historie", "Keine")
            if pd.isna(letzte) or str(letzte).strip() == "":
                letzte = "Keine"

            data_all.append([
                str(row.get("Vorname", "")),
                str(row.get("Nachname", "")),
                str(row.get("Startnummer", "")),
                str(row.get("Klasse", "")),
                str(letzte)
            ])

        t_all = Table(data_all, colWidths=[80, 80, 60, 80, 200])
        t_all.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
        ]))

        elements.append(t_all)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    def excel_alle_fahrer(df_all):
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_all.to_excel(writer, index=False, sheet_name="Alle_Fahrer")
        buffer.seek(0)
        return buffer

    # --------------------
    # Sidebar Exporte
    # --------------------
    if role in ["admin", "admin2", "abnahme"]:
        st.sidebar.header("📤 Exporte")
        st.sidebar.download_button(
            "📄 PDF aller Fahrer",
            pdf_alle_fahrer(df),
            file_name="Alle_Fahrer.pdf",
            mime="application/pdf"
        )
        st.sidebar.download_button(
            "📊 Excel aller Fahrer",
            excel_alle_fahrer(df),
            file_name="Alle_Fahrer.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --------------------
    # Abnahmen scannen + letzte Abnahme pro Startnr/Jahr/Klasse
    # --------------------
    def parse_dt(datum_str: str):
        if not datum_str:
            return None
        s = str(datum_str).strip()
        for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                pass
        return None

    def hat_maengel(abn: dict) -> bool:
        for b in (abn.get("Ergebnisse", {}) or {}).values():
            if str(b.get("Status", "")).strip().lower() == "mangel vorhanden":
                return True
        return False

    def scan_abnahmen_latest():
        rows = []
        if not os.path.exists(ABNAHMEN_ROOT):
            return rows

        for startnr in os.listdir(ABNAHMEN_ROOT):
            folder = os.path.join(ABNAHMEN_ROOT, startnr)
            if not os.path.isdir(folder):
                continue

            for jf in os.listdir(folder):
                if not jf.lower().endswith(".json"):
                    continue

                path = os.path.join(folder, jf)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        abn = json.load(f)
                except Exception:
                    continue

                if not isinstance(abn, dict):
                    continue

                datum = str(abn.get("Datum", "")).strip()
                typ = str(abn.get("Typ", "")).strip()
                klasse = str(abn.get("Klasse", "")).strip()
                unterschrift = str(abn.get("Unterschrift", "")).strip()

                dt = parse_dt(datum)
                jahr = dt.year if dt else None
                if jahr is None:
                    continue

                maengel = hat_maengel(abn)
                bestanden = (typ.lower() == "jahresabnahme") and (not maengel)

                rows.append({
                    "Startnummer": str(startnr).strip(),
                    "Jahr": jahr,
                    "Datum": datum,
                    "_dt": dt,
                    "Klasse": klasse,
                    "Typ": typ,
                    "Bestanden": "Ja" if bestanden else "Nein",
                    "Mängel": "Ja" if maengel else "Nein",
                    "Unterschrift": unterschrift
                })

        latest = {}
        for r in rows:
            key = (r["Startnummer"], r["Jahr"], r.get("Klasse", ""))
            if key not in latest or (r.get("_dt") or datetime.min) > (latest[key].get("_dt") or datetime.min):
                latest[key] = r

        out = list(latest.values())
        for r in out:
            r.pop("_dt", None)
        return out

    # --------------------
    # Lauf-Filter
    # --------------------
    def load_termine_options():
        termine = load_json(termine_file, default=[])
        opts = []
        if isinstance(termine, list):
            for t in termine:
                if isinstance(t, dict) and "datum" in t and "beschreibung" in t:
                    opts.append(f"{t['datum']} – {t['beschreibung']}")
        return sorted(opts)

    def load_nennungen_for_lauf(lauf_str: str):
        data = load_json(nennungen_fahrer_file, default=[])
        if not isinstance(data, list):
            return []
        return [x for x in data if str(x.get("lauf", "")).strip() == str(lauf_str).strip()]

    # --------------------
    # Tabs
    # --------------------
    if role in ["admin", "admin2", "abnahme"]:
        tabs = st.tabs(["🏁 Startseite", "🔧 Fahrzeugabnahme", "📚 Historie", "📅 Jahresübersicht"])
        tab_start, tab_abnahme, tab_hist, tab_jahr = tabs
    else:
        tabs = st.tabs(["📅 Jahresübersicht"])
        tab_jahr = tabs[0]
        tab_start = None
        tab_abnahme = None
        tab_hist = None

    # ==========================
    # TAB 1: Startseite
    # ==========================
    if role in ["admin", "admin2", "abnahme"]:
        with tab_start:
            st.header("🔍 Fahrersuche & Übersicht")

            fahrer = suche_und_waehle_fahrer(
                df,
                st.text_input("Vorname, Nachname oder Startnummer eingeben:", key="start_suche"),
                "start"
            )

            if not fahrer:
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.subheader("➕ Neuen Fahrer anlegen")

                with st.form("neuer_fahrer_form"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        vorname = st.text_input("Vorname")
                        nachname = st.text_input("Nachname")

                    with col2:
                        klasse = st.selectbox("Klasse", list(klassen_farben.keys()))
                        startnummer = st.number_input(
                            "Startnummer",
                            min_value=1,
                            value=next_free_startnummer(df),
                            step=1
                        )

                    with col3:
                        fahrzeug = st.text_input("Fahrzeug")
                        verein = st.text_input("Verein")
                        lizenz = st.checkbox("Lizenz vorhanden?")

                    submitted = st.form_submit_button("🚀 Fahrer speichern")

                    if submitted:
                        if not vorname.strip() or not nachname.strip():
                            st.error("Bitte Vorname und Nachname angeben.")
                        else:
                            exists = df[
                                (df["Startnummer"].astype(str).str.strip() == str(startnummer).strip()) &
                                (df["Klasse"].astype(str).str.strip() == str(klasse).strip())
                            ]

                            if not exists.empty:
                                st.warning(
                                    "⚠️ Ein Fahrer mit dieser Startnummer und Klasse existiert bereits. "
                                    "Eintrag wird trotzdem hinzugefügt."
                                )

                            neuer_fahrer = {
                                "Vorname": vorname.strip(),
                                "Nachname": nachname.strip(),
                                "Startnummer": int(startnummer),
                                "Klasse": klasse,
                                "Lizenz": lizenz,
                                "Fahrzeug": fahrzeug.strip(),
                                "Verein": verein.strip(),
                                "Abnahme_Historie": ""
                            }

                            if save_new_fahrer_supabase(neuer_fahrer):
                                os.makedirs(os.path.join(ABNAHMEN_ROOT, str(startnummer)), exist_ok=True)
                                st.success(
                                    f"✅ Neuer Fahrer '{vorname} {nachname}' in Klasse '{klasse}' gespeichert!"
                                )
                                st.balloons()

    # ==========================
    # TAB 2: Fahrzeugabnahme
    # ==========================
    if role in ["admin", "admin2", "abnahme"]:
        with tab_abnahme:
            st.header("🛠️ Fahrzeugabnahme durchführen")

            fahrer = suche_und_waehle_fahrer(
                df,
                st.text_input(
                    "Fahrer suchen (Vorname, Nachname oder Startnummer):",
                    key="abnahme_suche"
                ),
                "abnahme"
            )

            if fahrer:
                startnr = fahrer["Startnummer"]
                klasse = fahrer["Klasse"]
                ergebnisse = {}
                bestanden = True

                # Reglement je Klasse laden
                if reglement_df is not None:
                    klassen_spalten = [
                        c for c in reglement_df.columns
                        if str(c).strip().lower() == str(klasse).strip().lower()
                    ]

                    if klassen_spalten:
                        spalte = klassen_spalten[0]
                        if "Punkt/Bauteil" in reglement_df.columns:
                            punkte_df = reglement_df[["Punkt/Bauteil", spalte]].dropna(subset=["Punkt/Bauteil"])
                            punkte_df.columns = ["Bauteil", "Beschreibung"]
                        else:
                            st.error("Die Reglement-Datei muss eine Spalte 'Punkt/Bauteil' enthalten.")
                            punkte_df = pd.DataFrame({"Bauteil": [], "Beschreibung": []})
                    else:
                        st.warning(f"Keine Reglement-Spalte für Klasse '{klasse}' gefunden.")
                        punkte_df = pd.DataFrame({"Bauteil": [], "Beschreibung": []})
                else:
                    st.warning("Keine Reglement-Datei gefunden.")
                    punkte_df = pd.DataFrame({"Bauteil": [], "Beschreibung": []})

                # Prüfpunkte anzeigen
                for _, row in punkte_df.iterrows():
                    bauteil = str(row["Bauteil"])
                    beschreibung = str(row["Beschreibung"])

                    with st.expander(f"{bauteil}", expanded=True):
                        st.markdown(
                            f"<div style='background:#f5f5f5;padding:8px;border-radius:6px;'>{beschreibung}</div>",
                            unsafe_allow_html=True
                        )

                        status = st.radio(
                            f"Ist {bauteil} in Ordnung?",
                            ["Erfüllt", "Mangel vorhanden"],
                            key=f"status_{bauteil}_{klasse}_{startnr}",
                            horizontal=True
                        )

                        bemerkung = st.text_area(
                            f"Bemerkung zu {bauteil}",
                            key=f"bem_{bauteil}_{klasse}_{startnr}",
                            height=60
                        )

                        bilder = st.file_uploader(
                            f"Bilder zu {bauteil} hochladen",
                            accept_multiple_files=True,
                            type=["png", "jpg", "jpeg"],
                            key=f"bilder_{bauteil}_{klasse}_{startnr}"
                        )

                        b64_list = []
                        if bilder:
                            for b in bilder:
                                b64_list.append(base64.b64encode(b.read()).decode())

                        if status != "Erfüllt":
                            bestanden = False

                        ergebnisse[bauteil] = {
                            "Status": status,
                            "Bemerkung": bemerkung,
                            "Bilder": b64_list
                        }

                lizenz_hat = str(fahrer.get("Lizenz", "")).strip().lower() in ["true", "1", "yes", "ja"]
                abnahme_typ = "Tagesabnahme" if not (lizenz_hat and bestanden) else "Jahresabnahme"

                st.markdown("---")
                st.subheader("📋 Abnahmeergebnis")
                if abnahme_typ == "Jahresabnahme":
                    st.success("✅ Fahrer erfüllt alle Bedingungen – Jahresabnahme erteilt!")
                else:
                    st.warning("⚠️ Fahrer erhält nur eine Tagesabnahme.")

                unterschrift = st.text_input(
                    "Technischer Vorstand / Abnehmende Person:",
                    value=st.session_state.get("username", ""),
                    key="abn_unterschrift"
                )

                if st.button("💾 Abnahme speichern", key="save_abnahme"):
                    os.makedirs(os.path.join(ABNAHMEN_ROOT, str(startnr)), exist_ok=True)
                    datum_now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

                    daten = {
                        "Datum": datum_now,
                        "Typ": abnahme_typ,
                        "Ergebnisse": ergebnisse,
                        "Unterschrift": unterschrift,
                        "Klasse": klasse
                    }

                    filename = os.path.join(
                        ABNAHMEN_ROOT,
                        str(startnr),
                        f"{datum_now.replace(':', '-').replace(' ', '_')}.json"
                    )
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(daten, f, ensure_ascii=False, indent=2)

                    neuer_eintrag = (
                        f"{datum_now} – {abnahme_typ} "
                        f"({'Bestanden' if bestanden else 'Mängel'}) "
                        f"durch {unterschrift} ({klasse})"
                    )

                    update_abnahme_historie_supabase(startnr, klasse, neuer_eintrag)

                    st.success(f"✅ Abnahme gespeichert ({abnahme_typ})")
                    st.balloons()

    # ==========================
    # TAB 3: Historie
    # ==========================
    if role in ["admin", "admin2", "abnahme"]:
        with tab_hist:
            st.header("📜 Abnahmehistorie & Exporte")

            fahrer = suche_und_waehle_fahrer(
                df,
                st.text_input("Fahrer suchen (Historie):", key="hist_suche"),
                "hist"
            )

            if fahrer:
                startnr = fahrer["Startnummer"]
                klasse = fahrer["Klasse"]
                abnahme_dir = os.path.join(ABNAHMEN_ROOT, str(startnr))
                abnahmen_list = []

                if os.path.exists(abnahme_dir):
                    for jfile in sorted(os.listdir(abnahme_dir)):
                        if jfile.endswith(".json"):
                            try:
                                with open(os.path.join(abnahme_dir, jfile), "r", encoding="utf-8") as f:
                                    abnahme_data = json.load(f)
                                    if abnahme_data.get("Klasse") == klasse:
                                        abnahmen_list.append(abnahme_data)
                            except Exception:
                                continue

                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📄 PDF dieser Abnahmen",
                        pdf_fahrer(fahrer, abnahmen_list),
                        file_name=f"{fahrer['Vorname']}_{fahrer['Nachname']}.pdf",
                        mime="application/pdf"
                    )

                with col2:
                    st.download_button(
                        "📊 Excel dieser Abnahmen",
                        excel_fahrer(fahrer, abnahmen_list),
                        file_name=f"{fahrer['Vorname']}_{fahrer['Nachname']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                st.markdown("---")

                if not abnahmen_list:
                    st.info("Keine Abnahmen für diesen Fahrer vorhanden.")
                else:
                    for abnahme_data in sorted(
                        abnahmen_list,
                        key=lambda x: x.get("Datum", ""),
                        reverse=True
                    ):
                        label = f"{abnahme_data.get('Datum', '')} – {abnahme_data.get('Typ', '')}"
                        ergebnisse = abnahme_data.get("Ergebnisse", {})
                        hat_maengel_local = any(
                            d.get("Status") == "Mangel vorhanden"
                            for d in (ergebnisse or {}).values()
                        )

                        if abnahme_data.get("Typ") == "Jahresabnahme" and not hat_maengel_local:
                            farbe = "#4CAF50"
                        elif abnahme_data.get("Typ") == "Tagesabnahme" and hat_maengel_local:
                            farbe = "#FF9800"
                        else:
                            farbe = "#F44336"

                        with st.expander(label, expanded=False):
                            st.markdown(
                                f"<div style='background-color:{farbe}; padding:10px; border-radius:8px; color:white;'>",
                                unsafe_allow_html=True
                            )
                            st.markdown(f"**🧾 Abnehmende Person:** {abnahme_data.get('Unterschrift', '–')}")
                            st.markdown(f"**📋 Abnahme-Typ:** {abnahme_data.get('Typ', '–')}")
                            st.markdown(f"**🚘 Klasse:** {abnahme_data.get('Klasse', '–')}")
                            st.markdown("---")

                            for bauteil, daten in (ergebnisse or {}).items():
                                st.markdown(f"🔧 **{bauteil}** – {daten.get('Status', '')}")
                                if daten.get("Bemerkung"):
                                    st.markdown(f"🗒️ _{daten.get('Bemerkung', '')}_")
                                if daten.get("Bilder"):
                                    for b64img in daten.get("Bilder"):
                                        try:
                                            st.image(base64.b64decode(b64img), width=200)
                                        except Exception:
                                            st.text("Bild konnte nicht angezeigt werden.")

                            st.markdown("</div>", unsafe_allow_html=True)

    # ==========================
    # TAB 4: Jahresübersicht
    # ==========================
    with tab_jahr:
        st.header("📅 Jahresübersicht: Filter & Übersicht")

        rows = scan_abnahmen_latest()
        if not rows:
            st.info("Keine Abnahmen vorhanden.")
            return

        ov = pd.DataFrame(rows)

        df_join = df.copy()
        df_join["Startnummer"] = df_join["Startnummer"].astype(str).str.strip()
        ov["Startnummer"] = ov["Startnummer"].astype(str).str.strip()
        merged = ov.merge(df_join, on=["Startnummer", "Klasse"], how="left")

        years = sorted(
            [y for y in merged["Jahr"].dropna().unique().tolist() if y is not None],
            reverse=True
        )
        if not years:
            st.warning("Keine Jahre gefunden.")
            st.dataframe(merged, use_container_width=True)
            return

        col1, col2, col3, col4 = st.columns([1, 2, 2, 2])

        year_sel = col1.selectbox("Jahr", years, index=0, key="ov_year")

        termin_opts = ["(kein Filter)"] + load_termine_options()
        termin_sel = col2.selectbox("Lauf/Termin", termin_opts, index=0, key="ov_termin")

        typ_filter = col3.selectbox(
            "Abnahme-Typ",
            ["Alle", "Jahresabnahme", "Tagesabnahme"],
            index=0,
            key="ov_typ"
        )

        status_filter = col4.selectbox(
            "Status",
            ["Alle", "Nur bestanden", "Nur nicht bestanden"],
            index=0,
            key="ov_status"
        )

        search = st.text_input(
            "Suche (Name / Startnr / Verein / Fahrzeug)",
            key="ov_search"
        ).strip().lower()

        view = merged[merged["Jahr"] == year_sel].copy()

        if termin_sel != "(kein Filter)":
            nenn = load_nennungen_for_lauf(termin_sel)
            teilnehmer_sn = set(
                str(x.get("startnummer", "")).strip()
                for x in nenn
                if str(x.get("startnummer", "")).strip()
            )
            if teilnehmer_sn:
                view = view[view["Startnummer"].astype(str).isin(teilnehmer_sn)].copy()
            else:
                view = view.iloc[0:0].copy()

        if typ_filter != "Alle":
            view = view[
                view["Typ"].astype(str).str.strip().str.lower() == typ_filter.lower()
            ].copy()

        if status_filter == "Nur bestanden":
            view = view[view["Bestanden"] == "Ja"].copy()
        elif status_filter == "Nur nicht bestanden":
            view = view[view["Bestanden"] == "Nein"].copy()

        if search:
            def row_contains(r):
                s = " ".join([
                    str(r.get("Vorname", "")),
                    str(r.get("Nachname", "")),
                    str(r.get("Startnummer", "")),
                    str(r.get("Verein", "")),
                    str(r.get("Fahrzeug", "")),
                    str(r.get("Klasse", "")),
                    str(r.get("Typ", "")),
                    str(r.get("Datum", "")),
                ]).lower()
                return search in s

            view = view[view.apply(row_contains, axis=1)].copy()

        try:
            view["Startnr_sort"] = pd.to_numeric(
                view["Startnummer"],
                errors="coerce"
            ).fillna(999999).astype(int)
        except Exception:
            view["Startnr_sort"] = 999999

        view = view.sort_values(["Klasse", "Startnr_sort"])

        cols = [
            "Vorname", "Nachname", "Startnummer", "Klasse", "Verein", "Fahrzeug",
            "Datum", "Typ", "Bestanden", "Mängel", "Unterschrift"
        ]
        for c in cols:
            if c not in view.columns:
                view[c] = ""

        st.dataframe(view[cols], use_container_width=True, hide_index=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Bestanden", int((view["Bestanden"] == "Ja").sum()) if "Bestanden" in view.columns else 0)
        c2.metric("Nicht bestanden", int((view["Bestanden"] == "Nein").sum()) if "Bestanden" in view.columns else 0)
        c3.metric("Gesamt", int(len(view)))

    # --------------------
    # Footer
    # --------------------
    st.markdown("""
    <hr>
    <div style='text-align:right; color:gray; font-size:0.9em;'>
    Erstellt von <b>A. Stoppa</b> © 2025
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    show()
