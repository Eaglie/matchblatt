import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import re

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

        style_match = re.search(
            r"<style[^>]*>(.*?)</style>",
            html,
            re.DOTALL | re.IGNORECASE
        )

        body_match = re.search(
            r"<body[^>]*>(.*?)</body>",
            html,
            re.DOTALL | re.IGNORECASE
        )

        if not style_match:
            raise ValueError(
                "CSS konnte aus report.html nicht gelesen werden."
            )

        if not body_match:
            raise ValueError(
                "Body konnte aus report.html nicht gelesen werden."
            )

        css = style_match.group(1)
        body = body_match.group(1)

        embedded_html = f"""
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">

<style>

{css}

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
    transform: scale(0.78);
    transform-origin: top left;

    margin: 10px 0 0 0;

    width: 210mm;
}}

</style>

</head>

<body>

{body}

</body>
</html>
"""

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )

        components.html(
            embedded_html,
            height=1900,
            scrolling=True
        )

    except Exception as e:

        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )

        st.exception(e)
