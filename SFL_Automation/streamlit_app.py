import streamlit as st
from pathlib import Path
import shutil

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
    "Transfermarkt Heim"
)

gast_url = st.text_input(
    "Transfermarkt Gast"
)


if st.button("MATCHBLATT ERSTELLEN"):

    if not sfl_url.strip():
        st.error("Bitte die SFL Matchcenter URL eingeben.")
        st.stop()

    if not heim_url.strip():
        st.error(
            "Bitte die Transfermarkt-URL des Heimteams eingeben."
        )
        st.stop()

    if not gast_url.strip():
        st.error(
            "Bitte die Transfermarkt-URL des Gastteams eingeben."
        )
        st.stop()

    try:

        with st.spinner("Lade SFL..."):
            sfl = lade_sfl(
                sfl_url.strip()
            )

        with st.spinner("Lade Heimteam..."):
            heim = lade_transfermarkt(
                heim_url.strip(),
                sfl["heim"]
            )

        with st.spinner("Lade Gastteam..."):
            gast = lade_transfermarkt(
                gast_url.strip(),
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
                "report.html wurde nicht erstellt."
            )

        static_dir = Path("static")
        static_dir.mkdir(
            exist_ok=True
        )

        static_report = static_dir / "report.html"

        shutil.copyfile(
            report_path,
            static_report
        )

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )

        html_content = report_path.read_text(
            encoding="utf-8"
)

 components.html(
     html_content,
     height=3000,
     scrolling=True
)

    except Exception as e:

        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )

        st.exception(e)
