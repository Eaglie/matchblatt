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

        # CSS aus dem fertigen Report holen
        css_start = html.find("<style>")
        css_end = html.find("</style>")

        if css_start == -1 or css_end == -1:
            raise ValueError(
                "CSS im report.html nicht gefunden."
            )

        css = html[
            css_start + len("<style>"):
            css_end
        ]

        # Den bereits fertigen .page-Block unverändert übernehmen
        page_start = html.find('<div class="page">')

        if page_start == -1:
            raise ValueError(
                'Der Bereich <div class="page"> wurde nicht gefunden.'
            )

        page_end = html.rfind("</div>")

        if page_end == -1 or page_end <= page_start:
            raise ValueError(
                "Der Matchblatt-Container konnte nicht gefunden werden."
            )

        page = html[
            page_start:
            page_end + len("</div>")
        ]

        # Eigenständige Darstellung für Streamlit
        embedded_html = f"""
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">

<style>

{css}

/* Streamlit-Darstellung */
html,
body {{
    margin: 0;
    padding: 0;
    background: transparent;
}}

body {{
    width: 100%;
    overflow-x: hidden;
}}

.page {{
    width: 210mm;
    margin: 8px auto;
    transform: scale(0.72);
    transform-origin: top center;
}}

</style>

</head>

<body>

{page}

</body>
</html>
"""

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )

        components.html(
            embedded_html,
            height=1250,
            scrolling=True
        )

    except Exception as e:

        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )

        st.exception(e)
