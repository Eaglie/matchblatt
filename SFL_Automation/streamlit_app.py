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
        # SFL LADEN
        # -------------------------------------------------

        with st.spinner("Lade SFL..."):

            sfl = lade_sfl(
                sfl_url
            )


        # -------------------------------------------------
        # HEIMTEAM LADEN
        # -------------------------------------------------

        with st.spinner(
            "Lade Heimteam von Transfermarkt..."
        ):

            heim = lade_transfermarkt(
                heim_url,
                sfl["heim"]
            )


        # -------------------------------------------------
        # GASTTEAM LADEN
        # -------------------------------------------------

        with st.spinner(
            "Lade Gastteam von Transfermarkt..."
        ):

            gast = lade_transfermarkt(
                gast_url,
                sfl["gast"]
            )


        # -------------------------------------------------
        # LETZTER GEGNER
        # -------------------------------------------------

        heim["letzter_gegner"] = sfl["gast"]
        gast["letzter_gegner"] = sfl["heim"]


        # -------------------------------------------------
        # MATCHBLATT ERSTELLEN
        # -------------------------------------------------

        with st.spinner(
            "Erstelle Matchblatt..."
        ):

            erstelle_report(
                sfl,
                heim,
                gast
            )


        # -------------------------------------------------
        # ERZEUGTE HTML-DATEI LESEN
        # -------------------------------------------------

        report_path = Path(
            "report.html"
        )


        if not report_path.exists():

            raise FileNotFoundError(
                "report.html wurde nicht erstellt."
            )


        html = report_path.read_text(
            encoding="utf-8"
        )


        # -------------------------------------------------
        # CSS AUS REPORT HOLEN
        # -------------------------------------------------

        style_start = html.find(
            "<style>"
        )

        style_end = html.find(
            "</style>"
        )


        if style_start == -1 or style_end == -1:

            raise ValueError(
                "CSS aus report.html konnte nicht gelesen werden."
            )


        css = html[
            style_start + len("<style>"):
            style_end
        ]


        # -------------------------------------------------
        # BODY-INHALT HOLEN
        # -------------------------------------------------

        body_start = html.find(
            "<body"
        )

        body_start = html.find(
            ">",
            body_start
        )


        body_end = html.rfind(
            "</body>"
        )


        if body_start == -1 or body_end == -1:

            raise ValueError(
                "Inhalt aus report.html konnte nicht gelesen werden."
            )


        body = html[
            body_start + 1:
            body_end
        ]


        # -------------------------------------------------
        # MATCHBLATT DIREKT IN STREAMLIT
        # -------------------------------------------------

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )


        st.markdown(
            f"""
<style>

{css}

/* ---------------------------------------------
   STREAMLIT MATCHBLATT
   --------------------------------------------- */

.matchblatt_container {{
    width: 100%;
    overflow-x: auto;
    overflow-y: visible;
    padding-top: 8px;
    padding-bottom: 20px;
}}

.matchblatt_container .page {{
    zoom: 0.72;
    margin-left: auto;
    margin-right: auto;
}}

</style>

<div class="matchblatt_container">

{body}

</div>
""",
            unsafe_allow_html=True
        )


    except Exception as e:

        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )

        st.exception(e)
