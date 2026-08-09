import json
import re
import subprocess
import requests
from bs4 import BeautifulSoup


ACCOUNT_KEY = "Os-hXumIK"

HEADERS = {
    "Origin": "https://sfl.ch",
    "Referer": "https://sfl.ch/",
    "User-Agent": "Mozilla/5.0",
    "x-account-key": ACCOUNT_KEY,
}


def _hole_header(opta_id):
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

    return response.json()


def _name_aus_objekt(obj):
    if not isinstance(obj, dict):
        return ""

    # Häufige Varianten
    for key in (
        "name",
        "displayName",
        "fullName",
        "personName",
        "officialName",
    ):
        wert = obj.get(key)
        if isinstance(wert, str) and wert.strip():
            return wert.strip()

    # Verschachtelte Person
    for key in (
        "person",
        "official",
        "individual",
        "player",
    ):
        wert = obj.get(key)
        if isinstance(wert, dict):
            name = _name_aus_objekt(wert)
            if name:
                return name

    return ""


def _rolle_text(obj):
    if not isinstance(obj, dict):
        return ""

    teile = []

    for key in (
        "role",
        "type",
        "position",
        "function",
        "officialType",
        "officialRole",
        "designation",
        "title",
        "label",
    ):
        wert = obj.get(key)

        if isinstance(wert, str):
            teile.append(wert)

        elif isinstance(wert, dict):
            for subkey in ("name", "label", "title", "value"):
                subwert = wert.get(subkey)
                if isinstance(subwert, str):
                    teile.append(subwert)

    return " ".join(teile).lower()


def _alle_objekte(obj):
    """
    Durchsucht die komplette Header-Response rekursiv.
    Dadurch ist der Parser nicht von einer einzigen JSON-Verschachtelung
    abhängig.
    """

    if isinstance(obj, dict):

        yield obj

        for wert in obj.values():
            yield from _alle_objekte(wert)

    elif isinstance(obj, list):

        for wert in obj:
            yield from _alle_objekte(wert)


def _extrahiere_offizielle(header):
    result = {
        "schiedsrichter": "",
        "assistent1": "",
        "assistent2": "",
        "vierter_offizieller": "",
        "var": "",
        "avar": "",
    }

    assistenten = []

    for obj in _alle_objekte(header):

        name = _name_aus_objekt(obj)
        rolle = _rolle_text(obj)

        if not name:
            continue

        # SCHIEDSRICHTER
        if (
            "referee" in rolle
            or "schiedsrichter" in rolle
            or rolle.strip() == "sr"
        ):

            if (
                "assistant" not in rolle
                and "assistent" not in rolle
                and "var" not in rolle
                and "avar" not in rolle
            ):
                if not result["schiedsrichter"]:
                    result["schiedsrichter"] = name
                continue

        # VAR
        if (
            re.search(r"\bvar\b", rolle)
            or "video assistant referee" in rolle
            or "video-schiedsrichter" in rolle
        ):
            if "avar" not in rolle and not result["var"]:
                result["var"] = name
            continue

        # AVAR
        if (
            "avar" in rolle
            or "assistant video assistant" in rolle
            or "video assistant referee assistant" in rolle
        ):
            if not result["avar"]:
                result["avar"] = name
            continue

        # 4. OFFIZIELLER
        if (
            "fourth" in rolle
            or "4th" in rolle
            or "4." in rolle
            or "vierter" in rolle
            or "4ème" in rolle
        ):
            if not result["vierter_offizieller"]:
                result["vierter_offizieller"] = name
            continue

        # ASSISTENT
        if (
            "assistant referee" in rolle
            or "assistant" in rolle
            or "assistent" in rolle
            or "linesman" in rolle
            or "assistant referee" in rolle
        ):
            if name not in assistenten:
                assistenten.append(name)

    if assistenten:
        result["assistent1"] = assistenten[0]

    if len(assistenten) > 1:
        result["assistent2"] = assistenten[1]

    return result


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
    # OFFIZIELLE DIREKT AUS DEM SFL MATCHCENTER
    # ---------------------------------------------------------

    try:
        header_data = _hole_header(opta_id)
        offizielle = _extrahiere_offizielle(header_data)
    except Exception:
        offizielle = {
            "schiedsrichter": "",
            "assistent1": "",
            "assistent2": "",
            "vierter_offizieller": "",
            "var": "",
            "avar": "",
        }

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
            result.stderr or "Fehler beim Abrufen der SFL-Kommentare."
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
    # REPORT
    # ---------------------------------------------------------

    report = {
        "heim": match_data.get("homeTeamName", ""),
        "gast": match_data.get("awayTeamName", ""),

        "datum": datum,
        "zeit": zeit,

        "stadion": match_data.get("venueLongName", ""),

        # Offizielle automatisch aus SFL
        "schiedsrichter": offizielle["schiedsrichter"],
        "assistent1": offizielle["assistent1"],
        "assistent2": offizielle["assistent2"],
        "vierter_offizieller": offizielle["vierter_offizieller"],
        "var": offizielle["var"],
        "avar": offizielle["avar"],

        "heim_abwesend": extrahiere_absenzen(
            match_data.get("homeTeamName", "")
        ),

        "gast_abwesend": extrahiere_absenzen(
            match_data.get("awayTeamName", "")
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
