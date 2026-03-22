# Datei: D:\App_DGM\seiten\fahrzeugabnahme.py

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json
from supabase_client import get_supabase

def show():

    # --------------------
    # Rollenprüfung
    # --------------------
    role = st.session_state.get("role", "")

    # erlaubt:
    # - admin: alles
    # - abnahme: alles (inkl. Übersicht)
    # - buero: nur Übersicht
    if role not in ["admin", "admin2", "abnahme", "buero"]:
        st.error("Keine Berechtigung für Fahrzeugabnahme.")
        return

    # --------------------
    # Seiteneinstellungen
    # --------------------
    st.set_page_config(page_title="Fahrzeugabnahme DGM", layout="wide")
    st.title("Deutsche Geländewagen Meisterschaft – Fahrzeugabnahme DGM")

    # --------------------
    # Pfade
    # --------------------
    stammdaten_file = r"D:\App_DGM\daten\FahrzeugAbnahme_Stammdaten.xlsx"
    termine_file = r"D:\App_DGM\daten\termine.json"
    nennungen_fahrer_file = r"D:\App_DGM\daten\nennungen_fahrer.json"
    ABNAHMEN_ROOT = r"Abnahmen"  # ggf. r"D:\App_DGM\Abnahmen" falls du dort speicherst

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
    # Stammdaten laden/speichern
    # --------------------
    df = load_stammdaten(stammdaten_file)
    sb = get_supabase()
    response = sb.table("fahrer").select("*").execute()
    data = response.data if response.data else []

    if not data:
        return pd.DataFrame(columns=[
            "Vorname", "Nachname", "Startnummer", "Klasse",
            "Lizenz", "Fahrzeug", "Verein", "Abnahme_Historie"
        ])

    df_local = pd.DataFrame(data)

    # Spalten aus Supabase auf deine bisherigen Namen umbenennen
    rename_map = {
        "vorname": "Vorname",
        "nachname": "Nachname",
        "startnummer": "Startnummer",
        "klasse": "Klasse",
        "lizenz": "Lizenz",
        "fahrzeug": "Fahrzeug",
        "verein": "Verein"
    }

    df_local = df_local.rename(columns=rename_map)

    # Falls Spalten fehlen, ergänzen
    for c in ["Vorname", "Nachname", "Startnummer", "Klasse", "Lizenz", "Fahrzeug", "Verein", "Abnahme_Historie"]:
        if c not in df_local.columns:
            df_local[c] = ""

    for c in df_local.columns:
        df_local[c] = df_local[c].astype(str).str.strip()

    return df_local

    def save_stammdaten(df_local, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df_local.to_excel(path, index=False)

    df = load_stammdaten(stammdaten_file)

    # --------------------
    # Abnahmen scannen + "letzte Abnahme pro Startnr+Jahr+Klasse"
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
        try:
            # fallback: "16.11.2025_18-06-35" -> aus filename ggf. schon so
            s2 = s.replace("_", " ").replace("-", ":")
            return datetime.strptime(s2, "%d.%m.%Y %H:%M:%S")
        except Exception:
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

        # latest per (Startnummer, Jahr, Klasse)
        latest = {}
        for r in rows:
            key = (r["Startnummer"], r["Jahr"], r.get("Klasse", ""))
            if key not in latest:
                latest[key] = r
            else:
                if (r.get("_dt") or datetime.min) > (latest[key].get("_dt") or datetime.min):
                    latest[key] = r

        out = list(latest.values())
        for r in out:
            r.pop("_dt", None)
        return out

    # --------------------
    # Termine / Lauf-Filter
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
    # Tabs je nach Rolle
    # --------------------
    if role in ["admin", "admin2", "abnahme"]:
        tabs = st.tabs(["🔧 Fahrzeugabnahme", "📚 Historie", "📅 Jahresübersicht"])
        tab_abnahme, tab_hist, tab_jahr = tabs
    else:
        tabs = st.tabs(["📅 Jahresübersicht"])
        tab_jahr = tabs[0]
        tab_abnahme = None
        tab_hist = None

    # ==========================
    # Fahrzeugabnahme (admin/abnahme)
    # ==========================
    if role in ["admin", "admin2", "abnahme"]:
        with tab_abnahme:
            st.header("🔧 Fahrzeugabnahme durchführen")

            search = st.text_input("Fahrer suchen (Vorname, Nachname, Startnummer)", key="abn_search")

            if search:
                res = df[
                    df["Vorname"].str.contains(search, case=False, na=False) |
                    df["Nachname"].str.contains(search, case=False, na=False) |
                    df["Startnummer"].str.contains(search, case=False, na=False)
                ]

                if res.empty:
                    st.warning("Kein Fahrer gefunden.")
                else:
                    sel = st.selectbox(
                        "Fahrer auswählen",
                        res.apply(lambda x: f"{x['Vorname']} {x['Nachname']} #{x['Startnummer']} ({x['Klasse']})", axis=1),
                        key="abn_sel"
                    )
                    startnr = sel.split("#")[1].split(" ")[0].strip()
                    fahrer = df[df["Startnummer"] == startnr].iloc[0]

                    st.markdown("### Stammdaten")
                    st.write(f"**Vorname:** {fahrer.get('Vorname','')}")
                    st.write(f"**Nachname:** {fahrer.get('Nachname','')}")
                    st.write(f"**Startnummer:** {fahrer.get('Startnummer','')}")
                    st.write(f"**Klasse:** {fahrer.get('Klasse','')}")
                    st.write(f"**Fahrzeug:** {fahrer.get('Fahrzeug','')}")
                    st.write(f"**Verein:** {fahrer.get('Verein','')}")

                    unterschrift = st.text_input(
                        "Unterschrift (Abnehmende Person)",
                        value=st.session_state.get("username", ""),
                        key="abn_sign"
                    )

                    # Typ wählbar (damit Tagesabnahme möglich ist)
                    typ_sel = st.selectbox(
                        "Abnahme-Typ",
                        ["Jahresabnahme", "Tagesabnahme"],
                        index=0,
                        key="abn_typ"
                    )

                    if st.button("💾 Abnahme speichern", key="abn_save"):
                        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                        folder = os.path.join(ABNAHMEN_ROOT, startnr)
                        os.makedirs(folder, exist_ok=True)

                        data = {
                            "Datum": now,
                            "Typ": typ_sel,
                            "Klasse": fahrer.get("Klasse", ""),
                            "Unterschrift": unterschrift,
                            "Ergebnisse": {}  # leer in diesem Minimal-Workflow
                        }

                        filename = os.path.join(folder, now.replace(":", "-").replace(" ", "_") + ".json")
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)

                        st.success("✅ Abnahme gespeichert.")

    # ==========================
    # Historie (admin/abnahme)
    # ==========================
    if role in ["admin", "admin2", "abnahme"]:
        with tab_hist:
            st.header("📚 Historie / Stammdaten")
            st.dataframe(df, use_container_width=True, hide_index=True)

    # ==========================
    # Jahresübersicht (admin/abnahme/buero)
    # ==========================
    with tab_jahr:
        st.header("📅 Jahresübersicht: Filter & Übersicht")

        rows = scan_abnahmen_latest()
        if not rows:
            st.info("Keine Abnahmen vorhanden.")
            return

        ov = pd.DataFrame(rows)

        # Join mit Stammdaten (für Name/Verein/Fahrzeug)
        df_join = df.copy()
        df_join["Startnummer"] = df_join["Startnummer"].astype(str).str.strip()
        ov["Startnummer"] = ov["Startnummer"].astype(str).str.strip()
        merged = ov.merge(df_join, on=["Startnummer", "Klasse"], how="left")

        # ---------- Filter UI ----------
        years = sorted([y for y in merged["Jahr"].dropna().unique().tolist() if y is not None], reverse=True)
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

        search = st.text_input("Suche (Name / Startnr / Verein / Fahrzeug)", key="ov_search").strip().lower()

        # ---------- Filter anwenden ----------
        view = merged[merged["Jahr"] == year_sel].copy()

        # Lauf/Termin filter via nennungen_fahrer.json
        if termin_sel != "(kein Filter)":
            nenn = load_nennungen_for_lauf(termin_sel)
            teilnehmer_sn = set(str(x.get("startnummer", "")).strip() for x in nenn if str(x.get("startnummer", "")).strip())
            if teilnehmer_sn:
                view = view[view["Startnummer"].astype(str).isin(teilnehmer_sn)].copy()
            else:
                view = view.iloc[0:0].copy()

        # Typ filter
        if typ_filter != "Alle":
            view = view[view["Typ"].astype(str).str.strip().str.lower() == typ_filter.lower()].copy()

        # Status filter
        if status_filter == "Nur bestanden":
            view = view[view["Bestanden"] == "Ja"].copy()
        elif status_filter == "Nur nicht bestanden":
            view = view[view["Bestanden"] == "Nein"].copy()

        # Suche
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

        # Sortierung
        try:
            view["Startnr_sort"] = pd.to_numeric(view["Startnummer"], errors="coerce").fillna(999999).astype(int)
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

        # KPIs
        c1, c2, c3 = st.columns(3)
        c1.metric("Bestanden", int((view["Bestanden"] == "Ja").sum()) if "Bestanden" in view.columns else 0)
        c2.metric("Nicht bestanden", int((view["Bestanden"] == "Nein").sum()) if "Bestanden" in view.columns else 0)
        c3.metric("Gesamt", int(len(view)))


if __name__ == "__main__":
    show()