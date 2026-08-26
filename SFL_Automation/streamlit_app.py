import streamlit as st
from pathlib import Path
from playwright.sync_api import sync_playwright


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


def erstelle_pdf(html):

    pdf_path = Path("matchblatt.pdf")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1200,
                "height": 1600
            }
        )

        page.set_content(
            html,
            wait_until="networkidle"
        )

        page.emulate_media(
            media="screen"
        )

        page.add_style_tag(
            content="""
                * {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }

                /*
                 * SPIELER-CONTAINER:
                 * keine Fläche, kein Rahmen,
                 * kein Schatten, keine Umrandung
                 */
                .player,
                .player_name,
                .player_position {
                    background: transparent !important;
                    background-color: transparent !important;
                    border: none !important;
                    box-shadow: none !important;
                    outline: none !important;
                }

                /*
                 * DER SPIELERKREIS BLEIBT SICHTBAR
                 */
                .player_circle {
                    background: #111 !important;
                    background-color: #111 !important;
                    border: 2px solid white !important;
                    box-shadow: 0 3px 8px rgba(0,0,0,.25) !important;
                }
            """
        )

        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={
                "top": "0",
                "right": "0",
                "bottom": "0",
                "left": "0"
            }
        )

        browser.close()

    return pdf_path


with st.form(
    "matchblatt_form",
    clear_on_submit=False
):

    starten = st.form_submit_button(
        "MATCHBLATT ERSTELLEN",
        use_container_width=False
    )


if starten:

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
            80,
            text="Erstelle Matchblatt..."
        )

        erstelle_report(
            sfl,
            heim,
            gast
        )

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

        if not html.strip():
            raise ValueError(
                "report.html ist leer."
            )

        progress.progress(
            90,
            text="Erstelle PDF..."
        )

        pdf_path = erstelle_pdf(
            html
        )

        if not pdf_path.exists():
            raise FileNotFoundError(
                "PDF wurde nicht erstellt."
            )

        pdf_data = pdf_path.read_bytes()

        progress.progress(
            100,
            text="PDF fertig."
        )

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )

        st.download_button(
            label="📄 MATCHBLATT ALS PDF HERUNTERLADEN",
            data=pdf_data,
            file_name="matchblatt.pdf",
            mime="application/pdf",
            type="primary"
        )

    except Exception as e:

        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )

        st.exception(e)
