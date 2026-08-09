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

    json_url = (
        "https://sfl.ch/_next/data/"
        "Y-9NZGIm1S6FvFeQABSly/"
        f"de/match-center/{opta_id}.json"
        f"?optaId={opta_id}"
    )

    response = requests.get(
        json_url,
        headers={
            "x-nextjs-data": "1",
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    match_data = data["pageProps"]["matchData"]

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

    html = (
        commentary
        .get("commentary", {})
        .get("messages", [{}])[0]
        .get("message", [{}])[0]
        .get("comment", "")
    )

    # ---------------------------------------------------------
    # ABSENZEN
    # ---------------------------------------------------------

    def extrahiere_absenzen(teamname):

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        text = soup.get_text("\n")

        teile = text.split(teamname)

        if len(teile) < 2:
            return {
                "gesperrt": [],
                "verletzt": [],
                "krank": [],
                "fraglich": [],
                "nicht_im_kader": []
            }

        block = teile[1]

        def hole(feld):

            m = re.search(
                rf"{feld}:\s*(.*)",
                block
            )

            if not m:
                return []

            wert = m.group(1).strip()

            if wert in ("", "-", "..."):
                return []

            return [
                x.strip()
                for x in wert.split(",")
                if x.strip()
            ]

        return {
            "gesperrt": hole("Gesperrt"),
            "verletzt": hole("Verletzt"),
            "krank": hole("Krank"),
            "fraglich": hole("Fraglich"),
            "nicht_im_kader": []
        }

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
