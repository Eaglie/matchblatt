import streamlit as st

from sfl import lade_sfl
from transfermarkt import lade_transfermarkt
from report import erstelle_report

st.set_page_config(page_title="Matchblatt", layout="wide")

st.title("MATCHBLATT")

sfl_url = st.text_input("SFL Matchcenter URL")
heim_url = st.text_input("Transfermarkt Heim")
gast_url = st.text_input("Transfermarkt Gast")

if st.button("MATCHBLATT ERSTELLEN"):

    st.write("Lade SFL...")
    sfl = lade_sfl(sfl_url)

    st.write("Lade Heim...")
    heim = lade_transfermarkt(heim_url, sfl["heim"])

    st.write("Lade Gast...")
    gast = lade_transfermarkt(gast_url, sfl["gast"])

    heim["letzter_gegner"] = sfl["gast"]
    gast["letzter_gegner"] = sfl["heim"]

    erstelle_report(sfl, gast, heim)

    st.success("Matchblatt erstellt!")
