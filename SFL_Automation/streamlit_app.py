import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

from sfl import lade_sfl
from transfermarkt import lade_transfermarkt
from report import erstelle_report


st.set_page_config(
    page_title="Matchblatt",
    layout="wide"
)

st.title("MATCHBLATT")


sfl_url = st.text_input("SFL Matchcenter URL")
heim_url = st.text_input("Transfermarkt Heim")
gast_url = st.text_input("Transfermarkt Gast")


if st.button("MATCHBLATT ERSTELLEN"):

    if not sfl_url.strip():
        st.error("Bitte die SFL Matchcenter URL eingeben.")
        st.stop()

    if not heim_url.strip():
        st.error("Bitte die Transfermarkt-URL des Heimteams eingeben.")
        st.stop()

    if not gast_url.strip():
        st.error("Bitte die Transfermarkt-URL des Gastteams eingeben.")
        st.stop()


    try:

        with st.spinner("Lade SFL..."):
            sfl = lade_sfl(sfl_url)


        with st.spinner("Lade Heimteam von Transfermarkt..."):
            heim = lade_transfermarkt(
                heim_url,
                sfl["heim"]
            )


        with st.spinner("Lade Gastteam von Transfermarkt..."):
            gast = lade_transfermarkt(
                gast_url,
                sfl["gast"]
            )


        heim["letzter_gegner"] = sfl["gast"]
        gast["letzter_gegner"] = sfl["heim"]


        with st.spinner("Erstelle Matchblatt..."):
            erstelle_report(
                sfl,
                gast,
                heim
            )


        report_path = Path("report.html")


        if not report_path.exists():
            raise FileNotFoundError(
                "report.html wurde nach der Erstellung nicht gefunden."
            )


        html = report_path.read_text(
            encoding="utf-8"
        )


        st.success("✅ Matchblatt erfolgreich erstellt.")


        components.html(
            html,
            height=3000,
            scrolling=True
        )


    except Exception as e:

        st.error("❌ Fehler beim Erstellen des Matchblatts.")
        st.exception(e)
