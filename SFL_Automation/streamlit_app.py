import streamlit as st
from pathlib import Path

from sfl import lade_sfl
from transfermarkt import lade_transfermarkt
from report import erstelle_report


st.set_page_config(
    page_title="Matchblatt",
    layout="wide"
)

st.title("MATCHBLATT")

sfl_url = st.text_input(
    "SFL Matchcenter URL",
    value="https://sfl.ch/de/match-center/1ljl51o6tne2kfcjop1qutes4"
)

heim_url = st.text_input(
    "Transfermarkt Heim",
    value="https://www.transfermarkt.de/spielbericht/index/spielbericht/4973730"
)

gast_url = st.text_input(
    "Transfermarkt Gast",
    value="https://www.transfermarkt.de/spielbericht/index/spielbericht/4897298"
)


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

        with st.spinner("Erstelle Matchblatt..."):
            erstelle_report(
                sfl,
                heim,
                gast
            )

        report_path = Path("report.html")

        if not report_path.exists():
            raise FileNotFoundError(
                "report.html wurde nach der Erstellung nicht gefunden."
            )

        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)

        static_report = static_dir / "report.html"

        static_report.write_text(
            report_path.read_text(encoding="utf-8"),
            encoding="utf-8"
        )

        st.success("✅ Matchblatt erfolgreich erstellt.")

        st.link_button(
            "MATCHBLATT ÖFFNEN",
            "/app/static/report.html"
        )

    except Exception as e:
        st.error("❌ Fehler beim Erstellen des Matchblatts.")
        st.exception(e)
