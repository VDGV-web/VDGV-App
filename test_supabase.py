import streamlit as st
from supabase_client import get_supabase

sb = get_supabase()

data = sb.table("fahrer").select("*").execute()

st.write(data.data)