import streamlit as st

st.set_page_config(
    page_title="VDGV App",
    page_icon="VDGV_Logo.png"
)

import streamlit as st
import json
import os

# --- Seiteneinstellungen ---
st.set_page_config(
    page_title="VDGV App",
    page_icon=":car:",
    layout="wide"
)

# --- CSS für Sidebar und Footer ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        width: 300px;
        position: relative;
        display: flex;
        flex-direction: column;
    }
    .sidebar-footer {
        margin-top: auto;
        text-align: center;
        font-size: 12px;
        color: gray;
        opacity: 0.8;
        padding-bottom: 10px;
        border-top: 1px solid #ddd;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# LOGIN SYSTEM
# ---------------------------
with st.sidebar:
    st.image("VDGV_Logo.png")

    st.subheader("Login")
    username = st.text_input("Benutzername", key="login_user")
    password = st.text_input("Passwort", type="password", key="login_pass")
    login_button = st.button("Anmelden", key="login_btn")

    # Admin-Logins zentral (einfach erweiterbar)
    ADMINS = {
        "Stoppa": "Anna97",
        "Pappers": "Jan90",
        "Bausch": "Jessi93",
        "Stiltz": "Manuel95",
        "Voss": "Jacky91",
        "May": "Thomas78",
    }

    if login_button:
        # --- Admins 1-6 ---
        if username in ADMINS and password == ADMINS[username]:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = "admin"  # alle Admins als "admin" behandeln
            st.success(f"Login erfolgreich! (Admin: {username})")

        # --- Klassensprecher ---
        elif username == "klassensprecher" and password == "klasse26":
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = "klassensprecher"
            st.success("Login erfolgreich! (Klassensprecher)")

        # --- Veranstalter ---
        elif username == "Trial" and password == "DGM26":
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = "veranstalter"
            st.success("Login erfolgreich! (Veranstalter)")

        # --- Nennbüro ---
        elif username == "Büro" and password == "VDGV":
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = "buero"
            st.success("Login erfolgreich! (Nennbüro)")

        # --- Abnahme (neu) ---
        elif username == "Abnahme" and password == "Auto":
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = "abnahme"
            st.success("Login erfolgreich! (Abnahme)")

        else:
            st.session_state["logged_in"] = False
            st.error("Benutzername oder Passwort falsch!")

    # ---------------------------
    # Navigation abhängig von Rolle
    # ---------------------------
    public_pages = ["Startseite", "Nennseite"]

    if st.session_state.get("logged_in"):
        role = st.session_state.get("role")

        if role == "klassensprecher":
            page_options = ["Startseite", "Nennseite", "Sektionsabnahme"]
            st.sidebar.success("Angemeldet als Klassensprecher")

        elif role == "admin":
            page_options = ["Startseite", "Nennseite", "Fahrzeugabnahme",
                            "Nennbüro", "Sektionsabnahme", "Adminbereich"]
            st.sidebar.success(f"Angemeldet als Admin: {st.session_state.get('username')}")

        elif role == "veranstalter":
            page_options = ["Startseite", "Nennseite", "Sektionsabnahme"]
            st.sidebar.success("Angemeldet als Veranstalter")

        elif role == "buero":
            page_options = ["Startseite", "Nennseite", "Fahrzeugabnahme", "Nennbüro"]
            st.sidebar.success("Angemeldet als Nennbüro")

        elif role == "abnahme":
            # Abnahme darf Fahrzeugabnahme (und ggf. später mehr)
            page_options = ["Startseite", "Nennseite", "Fahrzeugabnahme"]
            st.sidebar.success("Angemeldet als Abnahme")

        else:
            page_options = public_pages

    else:
        page_options = public_pages
        st.sidebar.warning("Für interne Bereiche bitte anmelden.")

    selected_page = st.radio("Seite auswählen", page_options, key="nav_radio")

    # Footer
    st.markdown('<div class="sidebar-footer">© 2025 DGM | Entwickelt von A. Stoppa</div>', unsafe_allow_html=True)


# ---------------------------
# SEITEN LADEN
# ---------------------------
if selected_page == "Startseite":
    import seiten.startseite as page
    termine = json.load(open("daten/termine.json", "r", encoding="utf-8"))
    page.show(termine)

elif selected_page == "Nennseite":
    import seiten.nennseite as page
    page.show()

elif selected_page == "Sektionsabnahme":
    import seiten.sektionsabnahme as page
    page.show()

elif selected_page == "Fahrzeugabnahme":
    # Admins dürfen alles, buero nur Übersicht (wie in fahrzeugabnahme.py geregelt), abnahme darf auch rein
    if st.session_state.get("role") in ["admin", "buero", "abnahme"]:
        import seiten.fahrzeugabnahme as page
        page.show()
    else:
        st.error("Nicht berechtigt!")

elif selected_page == "Nennbüro":
    # Admin + buero dürfen Nennbüro
    if st.session_state.get("role") in ["admin", "buero"]:
        import seiten.nennbuero as page
        page.show()
    else:
        st.error("Nicht berechtigt!")

elif selected_page == "Adminbereich":
    if st.session_state.get("role") == "admin":
        import seiten.adminbereich as page
        page.show()
    else:
        st.error("Nur Administratoren haben Zugriff!")
