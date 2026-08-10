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


# ---------------------------------------------------------
# Status
# ---------------------------------------------------------

if "report_ready" not in st.session_state:
    st.session_state["report_ready"] = False


# ---------------------------------------------------------
# Matchblatt erstellen
# ---------------------------------------------------------

if st.button("MATCHBLATT ERSTELLEN"):

    st.session_state["report_ready"] = False

    if not sfl_url.strip():
        st.error(
            "Bitte die SFL Matchcenter URL eingeben."
        )
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

        # -------------------------------------------------
        # SFL
        # -------------------------------------------------

        with st.spinner("Lade SFL..."):
            sfl = lade_sfl(
                sfl_url.strip()
            )

        # -------------------------------------------------
        # Heimteam
        # -------------------------------------------------

        with st.spinner("Lade Heimteam..."):
            heim = lade_transfermarkt(
                heim_url.strip(),
                sfl["heim"]
            )

        # -------------------------------------------------
        # Gastteam
        # -------------------------------------------------

        with st.spinner("Lade Gastteam..."):
            gast = lade_transfermarkt(
                gast_url.strip(),
                sfl["gast"]
            )

        # -------------------------------------------------
        # Matchblatt erstellen
        # -------------------------------------------------

        with st.spinner("Erstelle Matchblatt..."):
            erstelle_report(
                sfl,
                heim,
                gast
            )

        # -------------------------------------------------
        # Prüfen
        # -------------------------------------------------

        report_path = Path("report.html")

        if not report_path.exists():
            raise FileNotFoundError(
                "report.html wurde nicht erstellt."
            )

        # -------------------------------------------------
        # Für Streamlit Static Serving bereitstellen
        # -------------------------------------------------

        static_dir = Path(".streamlit") / "static"

        static_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        static_report = static_dir / "report.html"

        html = report_path.read_text(
            encoding="utf-8"
        )

        static_report.write_text(
            html,
            encoding="utf-8"
        )

        st.session_state["report_ready"] = True

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )

    except Exception as e:

        st.session_state["report_ready"] = False

        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )

        st.exception(e)


# ---------------------------------------------------------
# Automatisches Öffnen
# ---------------------------------------------------------

if st.session_state["report_ready"]:

    components.html(
        """
        <script>
            window.parent.postMessage(
                {
                    type: "OPEN_MATCHBLATT"
                },
                "*"
            );
        </script>
        """,
        height=0
    )

    st.markdown(
        """
        <script>
        (function() {

            const url = "/static/report.html";

            const tab = window.open(
                url,
                "matchblatt"
            );

            if (tab) {
                tab.focus();
            }

        })();
        </script>
        """,
        unsafe_allow_html=True
    )
