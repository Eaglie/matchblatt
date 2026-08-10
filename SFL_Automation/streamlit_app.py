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
# Echten Browser-Button erzeugen
# ---------------------------------------------------------

components.html(
    """
    <button
        id="matchblatt-button"
        style="
            padding: 10px 18px;
            border-radius: 6px;
            border: 1px solid #cccccc;
            background: white;
            font-size: 16px;
            cursor: pointer;
        "
    >
        MATCHBLATT ERSTELLEN
    </button>

    <script>
        const button =
            document.getElementById("matchblatt-button");

        button.addEventListener("click", function () {

            /*
             * Der neue Tab wird DIREKT innerhalb
             * des echten Mausklicks geöffnet.
             *
             * Dadurch kann Safari ihn nicht als
             * nachträgliches Popup behandeln.
             */
            const tab = window.open(
                "about:blank",
                "_blank"
            );

            if (!tab) {
                alert(
                    "Safari hat das Öffnen eines neuen Tabs blockiert."
                );
                return;
            }

            /*
             * Der neue Tab wartet auf report.html.
             *
             * Sobald Render die Datei bereitgestellt hat,
             * wird der Tab automatisch dorthin umgeleitet.
             */
            tab.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Matchblatt wird erstellt...</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            padding: 40px;
                        }
                    </style>
                </head>
                <body>
                    <h2>Matchblatt wird erstellt...</h2>
                    <p>Bitte kurz warten.</p>
                </body>
                </html>
            `);

            /*
             * URL des fertigen Reports.
             */
            const reportUrl =
                window.location.origin +
                "/static/report.html";

            /*
             * Prüfen, ob report.html bereits existiert.
             */
            const checkReport = setInterval(
                async function () {

                    try {

                        const response =
                            await fetch(
                                reportUrl,
                                {
                                    method: "HEAD",
                                    cache: "no-store"
                                }
                            );

                        if (response.ok) {

                            clearInterval(
                                checkReport
                            );

                            tab.location.href =
                                reportUrl;

                            tab.focus();
                        }

                    } catch (error) {
                        // Noch nicht vorhanden.
                    }

                },
                1000
            );

            /*
             * Streamlit mitteilen:
             * Jetzt Matchblatt erstellen.
             */
            window.parent.postMessage(
                {
                    type: "CREATE_MATCHBLATT"
                },
                "*"
            );
        });
    </script>
    """,
    height=55
)


# ---------------------------------------------------------
# Streamlit verarbeitet den Auftrag
# ---------------------------------------------------------

if st.query_params.get("create") == "1":

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

        report_path = Path(
            "report.html"
        )

        if not report_path.exists():
            raise FileNotFoundError(
                "report.html wurde nicht erstellt."
            )

        static_dir = (
            Path(".streamlit") /
            "static"
        )

        static_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        static_report = (
            static_dir /
            "report.html"
        )

        static_report.write_text(
            report_path.read_text(
                encoding="utf-8"
            ),
            encoding="utf-8"
        )

        st.success(
            "✅ Matchblatt erfolgreich erstellt."
        )

    except Exception as e:

        st.error(
            "❌ Fehler beim Erstellen des Matchblatts."
        )

        st.exception(e)
