import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import base64

st.set_page_config(
    page_title="Matchblatt",
    layout="wide"
)

st.title("MATCHBLATT")

sfl_url = st.text_input("SFL Matchcenter URL")
heim_url = st.text_input("Transfermarkt Heim")
gast_url = st.text_input("Transfermarkt Gast")


@st.cache_data(ttl=300, show_spinner=False)
def lade_sfl_cached(url):
    from sfl import lade_sfl
    return lade_sfl(url)


@st.cache_data(ttl=300, show_spinner=False)
def lade_tm_cached(url, teamname):
    from transfermarkt import lade_transfermarkt
    return lade_transfermarkt(url, teamname)


# Formular statt normalem st.button:
# Dadurch wird der Start eindeutig mit EINEM Submit ausgelöst.
with st.form("matchblatt_form", clear_on_submit=False):

    starten = st.form_submit_button(
        "MATCHBLATT ERSTELLEN",
        use_container_width=False
    )


if starten:

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
        from report import erstelle_report

        progress = st.progress(
            0,
            text="Lade SFL..."
        )

        sfl = lade_sfl_cached(
            sfl_url.strip()
        )

        progress.progress(
            25,
            text="SFL geladen – lade Heimteam..."
        )

        heim = lade_tm_cached(
            heim_url.strip(),
            sfl["heim"]
        )

        progress.progress(
            60,
            text="Heimteam geladen – lade Gastteam..."
        )

        gast = lade_tm_cached(
            gast_url.strip(),
            sfl["gast"]
        )

        progress.progress(
            85,
            text="Erstelle Matchblatt..."
        )

        # Transfermarkt liefert bereits das tatsächliche
        # letzte Spiel inklusive Gegner und Resultat.
        # Diese Daten NICHT mit dem aktuellen SFL-Gegner überschreiben.
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

        html = report_path.read_text(
            encoding="utf-8"
        )

        if not html.strip():
            raise ValueError(
                "report.html ist leer."
            )

        progress.progress(
            100,
            text="Matchblatt fertig."
        )

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )

        html_b64 = base64.b64encode(
            html.encode("utf-8")
        ).decode("ascii")

        st.markdown(
            f'''
            <a href="data:text/html;base64,{html_b64}"
               target="_blank"
               style="
                   display:inline-block;
                   padding:0.5rem 1rem;
                   background:#ff4b4b;
                   color:white;
                   text-decoration:none;
                   border-radius:0.25rem;
                   font-weight:600;
               ">
               MATCHBLATT IN NEUEM TAB ÖFFNEN
            </a>
            ''',
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )
        st.exception(e)
