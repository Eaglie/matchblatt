import streamlit as st

st.set_page_config(
    page_title="Matchblatt",
    layout="wide"
)

st.title("MATCHBLATT")

sfl_url = st.text_input("SFL Matchcenter URL")
heim_url = st.text_input("Transfermarkt Heim")
gast_url = st.text_input("Transfermarkt Gast")

st.button("MATCHBLATT ERSTELLEN")
