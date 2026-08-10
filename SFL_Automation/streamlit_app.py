import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


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
        from report import erstelle_report

        progress = st.progress(0, text="Lade SFL...")

        sfl = lade_sfl_cached(sfl_url.strip())
        progress.progress(25, text="SFL geladen – Transfermarkt wird geladen...")

        # Heim und Gast gleichzeitig laden.
        with ThreadPoolExecutor(max_workers=2) as executor:

            future_heim = executor.submit(
                lade_tm_cached,
                heim_url.strip(),
                sfl["heim"]
            )

            future_gast = executor.submit(
                lade_tm_cached,
                gast_url.strip(),
                sfl["gast"]
            )

            heim = future_heim.result()
            progress.progress(62, text="Heimteam geladen – Gastteam wird fertig geladen...")

            gast = future_gast.result()

        progress.progress(80, text="Erstelle Matchblatt...")

        heim["letzter_gegner"] = sfl["gast"]
        gast["letzter_gegner"] = sfl["heim"]

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

        progress.progress(100, text="Matchblatt fertig.")

        st.success("✅ Matchblatt erfolgreich erstellt.")

        components.html(
            html,
            height=1900,
            scrolling=True
        )

    except Exception as e:
        st.error("❌ Fehler beim Erstellen des Matchblatts.")
        st.exception(e)
