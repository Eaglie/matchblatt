import json
import re
import requests
from bs4 import BeautifulSoup


ACCOUNT_KEY = "Os-hXumIK"


def lade_offizielle(opta_id):
    """
    Holt nur:
    - Schiedsrichter
    - VAR

    Gibt immer ein Tupel zurück:
    (schiedsrichter, var)
    """

    url = (
        "https://origins-widgets-orchestrator.origins-digital.com"
        "/api/header"
    )

    response = requests.get(
        url,
        params={"fixtureId": opta_id},
        headers={
            "Accept": "*/*",
            "Accept-Language": "de",
            "Origin": "https://sfl.ch",
            "Referer": "https://sfl.ch/",
            "User-Agent": "Mozilla/5.0",
            "x-account-key": ACCOUNT_KEY,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    schiedsrichter = ""
    var = ""

    def durchsuche(obj):

        nonlocal schiedsrichter
        nonlocal var

        if isinstance(obj, dict):

            typ = obj.get("type", "")

            if isinstance(typ, str):

                name = " ".join(
                    x
                    for x in (
                        obj.get("firstName", ""),
                        obj.get("lastName", "")
                    )
                    if isinstance(x, str) and x.strip()
                ).strip()

                if typ == "Main" and name:
                    schiedsrichter = name

                elif (
                    typ == "Video Assistant Referee"
                    and name
                ):
                    var = name

            for value in obj.values():
                durchsuche(value)

        elif isinstance(obj, list):

            for value in obj:
                durchsuche(value)

    durchsuche(data)

    return schiedsrichter, var


def lade_sfl(url):

    opta_id = url.rstrip("/").split("/")[-1]

    if not opta_id:
        raise ValueError(
            "Keine gültige SFL Matchcenter URL."
        )

    # Die SFL liefert die Matchdaten aktuell direkt in der
    # HTML-Seite im __NEXT_DATA__-Script. Die alte, fest
    # eingebaute _next/data-Build-ID ist nicht mehr zuverlässig.

    response = requests.get(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "de",
            "User-Agent": "Mozilla/5.0",
        },
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    next_data = soup.find("script", id="__NEXT_DATA__")

    if next_data is None or not next_data.string:
        raise ValueError(
            "SFL: __NEXT_DATA__ mit Matchdaten nicht gefunden."
        )

    data = json.loads(next_data.string)
    match_data = data["props"]["pageProps"]["matchData"]

    # ---------------------------------------------------------
    # SCHIEDSRICHTER / VAR
    # ---------------------------------------------------------

    try:
        schiedsrichter, var = lade_offizielle(opta_id)
    except Exception:
        schiedsrichter = ""
        var = ""

    # ---------------------------------------------------------
    # COMMENTARY
    # ---------------------------------------------------------

    commentary_url = (
        "https://origins-widgets-orchestrator.origins-digital.com"
        "/api/commentary"
    )

    commentary_response = requests.get(
        commentary_url,
        params={"fixtureId": opta_id},
        headers={
            "Accept": "*/*",
            "Accept-Language": "de",
            "Origin": "https://sfl.ch",
            "Referer": "https://sfl.ch/",
            "User-Agent": "Mozilla/5.0",
            "x-account-key": ACCOUNT_KEY,
        },
        timeout=30,
    )

    if commentary_response.ok:

        try:
            commentary = commentary_response.json()

        except Exception:
            commentary = {}

    else:
        commentary = {}

    # ---------------------------------------------------------
    # ABSENZEN-HTML AUS DER KOMPLETTEN COMMENTARY ANSCHAUEN
    # ---------------------------------------------------------

    def finde_absenzen_html(obj):

        if isinstance(obj, dict):

            for key, value in obj.items():

                if (
                    key == "comment"
                    and isinstance(value, str)
                    and "ABWESENDE SPIELER" in value.upper()
                ):
                    return value

                gefunden = finde_absenzen_html(value)

                if gefunden:
                    return gefunden

        elif isinstance(obj, list):

            for value in obj:

                gefunden = finde_absenzen_html(value)

                if gefunden:
                    return gefunden

        return ""

    html = finde_absenzen_html(commentary)

    # ---------------------------------------------------------
    # ABSENZEN
    # ---------------------------------------------------------

    def extrahiere_absenzen(teamname):

        leeres_ergebnis = {
            "gesperrt": [],
            "verletzt": [],
            "krank": [],
            "fraglich": [],
            "nicht_im_kader": []
        }

        if not html:
            return leeres_ergebnis

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # -----------------------------------------------------
        # Alle p-Elemente des gefundenen SFL-Blocks
        # -----------------------------------------------------

        elemente = soup.find_all("p")

        if not elemente:
            return leeres_ergebnis

        # -----------------------------------------------------
        # ABWESENDE SPIELER finden
        # -----------------------------------------------------

        absenzen_start = None

        for i, element in enumerate(elemente):

            text = element.get_text(
                " ",
                strip=True
            )

            if text.upper() == "ABWESENDE SPIELER":

                absenzen_start = i
                break

        if absenzen_start is None:
            return leeres_ergebnis

        # -----------------------------------------------------
        # Gewünschtes Team finden
        # -----------------------------------------------------

        team_index = None

        for i in range(
            absenzen_start + 1,
            len(elemente)
        ):

            element = elemente[i]

            text = element.get_text(
                " ",
                strip=True
            )

            if (
                text.lower()
                == teamname.strip().lower()
            ):

                team_index = i
                break

        if team_index is None:
            return leeres_ergebnis

        # -----------------------------------------------------
        # Kategorien
        # -----------------------------------------------------

        kategorien = {
    "Gesperrt": "gesperrt",
    "Verletzt": "verletzt",
    "Krank": "krank",
    "Fraglich": "fraglich",
    "Nicht im Aufgebot": "nicht_im_kader"
}

        ergebnis = leeres_ergebnis.copy()

        # -----------------------------------------------------
        # Teamblock auslesen
        # -----------------------------------------------------

        for element in elemente[team_index + 1:]:

            text = element.get_text(
                " ",
                strip=True
            )

            if not text:
                continue

            # Ein neues <strong>-Element nach dem Team
            # bedeutet den Beginn des nächsten Blocks.
            strong = element.find("strong")

            if strong is not None:

                neuer_titel = strong.get_text(
                    " ",
                    strip=True
                )

                if (
                    neuer_titel
                    and neuer_titel.lower()
                    != teamname.strip().lower()
                ):
                    break

            # -------------------------------------------------
            # Kategorie erkennen
            # -------------------------------------------------

            for bezeichnung, schluessel in kategorien.items():

                prefix = bezeichnung + ":"

                if text.lower().startswith(
                    prefix.lower()
                ):

                    wert = text[
                        len(prefix):
                    ].strip()

                    if wert in ("", "-", "..."):

                        ergebnis[schluessel] = []

                    else:

                        ergebnis[schluessel] = [
                            name.strip()
                            for name in wert.split(",")
                            if name.strip()
                        ]

                    break

        return ergebnis

    # ---------------------------------------------------------
    # DATUM / ZEIT
    # ---------------------------------------------------------

    datum = match_data.get("date", "")
    zeit = match_data.get("time", "")

    if datum.endswith("Z"):
        datum = datum[:-1]

    if zeit.endswith("Z"):
        zeit = zeit[:-1]

    if datum:
        jahr, monat, tag = datum.split("-")
        datum = f"{int(tag)}.{int(monat)}.{jahr}"

    zeit = zeit[:5]

    # ---------------------------------------------------------
    # REPORT-DATEN
    # ---------------------------------------------------------

    report = {
        "heim": match_data.get(
            "homeTeamName",
            ""
        ),

        "gast": match_data.get(
            "awayTeamName",
            ""
        ),

        "datum": datum,

        "zeit": zeit,

        "stadion": match_data.get(
            "venueLongName",
            ""
        ),

        "schiedsrichter": schiedsrichter,

        "var": var,

        "heim_abwesend": extrahiere_absenzen(
            match_data.get(
                "homeTeamName",
                ""
            )
        ),

        "gast_abwesend": extrahiere_absenzen(
            match_data.get(
                "awayTeamName",
                ""
            )
        ),

        "lineups": {},

        "heim_letztes_spiel": {
            "gegner": "",
            "resultat": "",
            "ausgang": ""
        },

        "gast_letztes_spiel": {
            "gegner": "",
            "resultat": "",
            "ausgang": ""
        }
    }

    return report


def _sauber(text):

    text = text.strip()

    if text in ("", "-", "..."):
        return []

    return [
        x.strip()
        for x in text.split(",")
        if x.strip()
    ]


def auswerten(header, commentary, lineups):
    return {}
