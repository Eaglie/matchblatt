import json
import re
import subprocess
import requests
from bs4 import BeautifulSoup


ACCOUNT_KEY = "Os-hXumIK"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "de",
    "Origin": "https://sfl.ch",
    "Referer": "https://sfl.ch/",
    "User-Agent": "Mozilla/5.0",
    "x-account-key": ACCOUNT_KEY,
}


def hole_offizielle(opta_id):
    """
    Holt die offiziellen Spieloffiziellen direkt aus dem
    SFL/Origins-Matchcenter.

    Wir übernehmen bewusst nur:
    - Schiedsrichter
    - VAR
    """

    url = (
        "https://origins-widgets-orchestrator.origins-digital.com"
        f"/api/header?fixtureId={opta_id}"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    offizielle = (
        data
        .get("liveData", {})
        .get("matchDetailsExtra", {})
        .get("matchOfficial", [])
    )

    schiedsrichter = ""
    var = ""

    for person in offizielle:

        typ = person.get("type", "")

        vorname = (
            person.get("firstName", "")
            or person.get("shortFirstName", "")
        )

        nachname = (
            person.get("lastName", "")
            or person.get("shortLastName", "")
        )

        name = f"{vorname} {nachname}".strip()

        if typ == "Main":
            schiedsrichter = name

        elif typ == "Video Assistant Referee":
            var = name

    return schiedsrichter, var


def lade_sfl(url):

    opta_id = url.rstrip("/").split("/")[-1]

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
    # SCHIEDSRICHTER + VAR
    # ---------------------------------------------------------

    try:
        schiedsrichter, var = hole_offizielle(opta_id)
    except Exception:
        schiedsrichter = ""
        var = ""

    # ---------------------------------------------------------
    # COMMENTARY
    # ---------------------------------------------------------

    cmd = [
        "curl",
        "https://origins-widgets-orchestrator.origins-digital.com/api/commentary",
        "--get",
        "--data-urlencode", f"fixtureId={opta_id}",
        "-H", "Accept: */*",
        "-H", "Accept-Language: de",
        "-H", "Origin: https://sfl.ch",
        "-H", "Referer: https://sfl.ch/",
        "-H", "User-Agent: Mozilla/5.0",
        "-H", f"x-account-key: {ACCOUNT_KEY}",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise Exception(
            result.stderr or
            "Fehler beim Abrufen der SFL-Kommentare."
        )

    try:
        commentary = json.loads(result.stdout)
    except json.JSONDecodeError:
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

        datum = (
            f"{int(tag)}."
            f"{int(monat)}."
            f"{jahr}"
        )

    zeit = zeit[:5]

    # ---------------------------------------------------------
    # REPORT
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

        # NUR diese beiden Offiziellen
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

    if text == "-":
        return []

    if text == "...":
        return []

    if not text:
        return []

    return [
        x.strip()
        for x in text.split(",")
        if x.strip()
    ]


def auswerten(header, commentary, lineups):
    return {}
