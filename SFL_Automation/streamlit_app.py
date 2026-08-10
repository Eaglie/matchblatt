import streamlit as st
from pathlib import Path
import streamlit.components.v1 as components

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


if "report_html" not in st.session_state:
    st.session_state["report_html"] = None


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

        # Matchblatt als statische Datei ablegen
        static_dir = Path(".streamlit/static")
        static_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        static_report = static_dir / "report.html"

        static_report.write_text(
            report_path.read_text(
                encoding="utf-8"
            ),
            encoding="utf-8"
        )

        st.session_state["report_ready"] = True

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )

        # Neue Seite in neuem Tab öffnen
        components.html(
            """
            <script>
                window.open(
                    '/app/static/report.html',
                    '_blank'
                );
            </script>
            """,
            height=0
        )

    except Exception as e:

        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )

        st.exception(e)


if st.session_state.get("report_ready"):

    st.markdown(
        """
        <a href="/app/static/report.html"
           target="_blank"
           style="
               display:inline-block;
               padding:10px 18px;
               background:#163b76;
               color:white;
               text-decoration:none;
               border-radius:6px;
               font-weight:bold;
           ">
           MATCHBLATT IN NEUEM TAB ÖFFNEN
        </a>
        """,
        unsafe_allow_html=True
    )
