import streamlit as st
from supabase_client import get_supabase

sb = get_supabase()

st.title("Supabase Insert Test")

if st.button("Testfahrer einfügen"):

    sb.table("fahrer").insert({
        "vorname": "Anna",
        "nachname": "Stoppa",
        "startnummer": "999",
        "klasse": "Standard",
        "lizenz": "JA",
        "fahrzeug": "Suzuki Samurai",
        "verein": "VDGV"
    }).execute()

    st.success("Fahrer eingefügt!")

data = sb.table("fahrer").select("*").execute()

st.write(data.data)