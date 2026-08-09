import streamlit as st
import base64
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
    "SFL Matchcenter URL"
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

        heim["letzter_gegner"] = heim.get("letzter_gegner", "")
        gast["letzter_gegner"] = gast.get("letzter_gegner", "")

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

        html = report_path.read_text(
            encoding="utf-8"
        )

        encoded = base64.b64encode(
            html.encode("utf-8")
        ).decode("ascii")

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )

        st.markdown(
            f"""
            <a
                href="data:text/html;base64,{encoded}"
                target="_blank"
                style="
                    display:inline-block;
                    padding:12px 20px;
                    background:#ffffff;
                    border:1px solid #999;
                    border-radius:6px;
                    text-decoration:none;
                    color:#222;
                    font-weight:600;
                "
            >
                MATCHBLATT ÖFFNEN
            </a>
            """,
            unsafe_allow_html=True
        )

    except Exception as e:

        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )

        st.exception(e)
