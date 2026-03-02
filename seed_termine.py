import streamlit as st
from supabase_client import get_supabase

st.title("Seed Termine")

sb = get_supabase()

if st.button("Termin-Test einfügen"):
    sb.table("termine").insert({
        "datum": "2026-01-01",
        "beschreibung": "Testtermin"
    }).execute()
    st.success("Termin eingefügt!")

data = sb.table("termine").select("*").order("id", desc=True).limit(20).execute()
st.write(data.data)