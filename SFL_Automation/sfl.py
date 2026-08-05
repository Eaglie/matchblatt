import json
import re
import subprocess
import requests
from bs4 import BeautifulSoup


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
        }
    )

    response.raise_for_status()

    data = response.json()
    match_data = data["pageProps"]["matchData"]

    cmd = [
        "curl",
        "https://origins-widgets-orchestrator.origins-digital.com/api/commentary",
        "--get",
        "--data-urlencode", f"fixtureId={opta_id}",
        "-H", "Accept: */*",
        "-H", "Accept-Language: de",
        "-H", "Origin: https://sfl.ch",
        "-H", "Referer: https://sfl.ch/",
        "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15",
        "-H", "x-account-key: Os-hXumIK",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    commentary = json.loads(result.stdout)

    html = ""

    try:
        html = commentary["commentary"]["messages"][0]["message"][0]["comment"]
    except Exception:
        html = ""

    def extrahiere_absenzen(teamname):

        soup = BeautifulSoup(html, "html.parser")
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
            m = re.search(rf"{feld}:\s*(.*)", block)
            if not m:
                return []

            wert = m.group(1).strip()

            if wert in ("", "-", "..."):
                return []

            return [x.strip() for x in wert.split(",")]

        return {
            "gesperrt": hole("Gesperrt"),
            "verletzt": hole("Verletzt"),
            "krank": hole("Krank"),
            "fraglich": hole("Fraglich"),
            "nicht_im_kader": []
        }

    # Datum/Zeit formatieren
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

    report = {
        "heim": match_data.get("homeTeamName", ""),
        "gast": match_data.get("awayTeamName", ""),

        "datum": datum,
        "zeit": zeit,

        "stadion": match_data.get("venueLongName", ""),

        "schiedsrichter": "",
        "var": "",

        "heim_abwesend": extrahiere_absenzen(match_data.get("homeTeamName", "")),
        "gast_abwesend": extrahiere_absenzen(match_data.get("awayTeamName", "")),

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

    return [x.strip() for x in text.split(",") if x.strip()]


def auswerten(header, commentary, lineups):
    return {}