from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import unicodedata


def _normalize_team(name):
    """
    Vereinheitlicht Mannschaftsnamen für einen sicheren Vergleich.
    Beispiele:
    FC St.Gallen 1879
    FC St. Gallen 1879
    -> fcstgallen1879
    """

    if not name:
        return ""

    name = unicodedata.normalize(
        "NFKD",
        name
    ).encode(
        "ascii",
        "ignore"
    ).decode(
        "ascii"
    )

    name = name.lower()

    # Alles ausser Buchstaben/Zahlen entfernen
    name = re.sub(
        r"[^a-z0-9]",
        "",
        name
    )

    return name


def _team_match(input_team, page_team):
    """
    Prüft, ob der von SFL gelieferte Teamname
    eindeutig dem Transfermarkt-Team entspricht.
    """

    a = _normalize_team(input_team)
    b = _normalize_team(page_team)

    if not a or not b:
        return False

    return a == b


def _extract_score(soup):
    """
    Holt das Endresultat aus dem Spielbericht.
    """

    score_box = soup.select_one(
        ".sb-core-info"
    )

    kandidaten = []

    if score_box:
        kandidaten.extend(
            list(score_box.stripped_strings)
        )

    if not kandidaten:
        kandidaten.extend(
            list(soup.stripped_strings)
        )

    for txt in kandidaten:

        txt = txt.strip()

        if not re.fullmatch(
            r"\d+:\d+",
            txt
        ):
            continue

        try:
            a, b = map(
                int,
                txt.split(":")
            )
        except ValueError:
            continue

        # Fussballresultate plausibilisieren
        if 0 <= a <= 30 and 0 <= b <= 30:
            return a, b

    return None


def _extract_team_names(soup):
    """
    Liest die beiden Mannschaften direkt
    aus den Transfermarkt-Teamblöcken.
    """

    heim_box = soup.select_one(
        ".sb-team.sb-heim a.sb-club__link"
    )

    gast_box = soup.select_one(
        ".sb-team.sb-gast a.sb-club__link"
    )

    if not heim_box:
        raise ValueError(
            "Transfermarkt: Heimteam konnte nicht eindeutig gefunden werden."
        )

    if not gast_box:
        raise ValueError(
            "Transfermarkt: Gastteam konnte nicht eindeutig gefunden werden."
        )

    heim = heim_box.get_text(
        " ",
        strip=True
    )

    gast = gast_box.get_text(
        " ",
        strip=True
    )

    if not heim or not gast:
        raise ValueError(
            "Transfermarkt: Mannschaftsnamen sind leer."
        )

    if _normalize_team(heim) == _normalize_team(gast):
        raise ValueError(
            f"Transfermarkt lieferte zweimal dasselbe Team: "
            f"'{heim}' / '{gast}'"
        )

    return heim, gast


def _extract_players(soup, is_heim):
    """
    Holt ausschließlich die Startelf des gewünschten Teams.
    """

    if is_heim:

        containers = soup.select(
            "div.sb-aufstellung-heim "
            "div.formation-player-container"
        )

    else:

        containers = soup.select(
            "div.sb-aufstellung-gast "
            "div.formation-player-container"
        )

    if not containers:

        raise ValueError(
            "Transfermarkt: Keine Spieler der "
            + ("Heim" if is_heim else "Gast")
            + "mannschaft gefunden."
        )

    spieler = []

    for div in containers:

        style = div.get(
            "style",
            ""
        )

        top = re.search(
            r"top:\s*([\d.]+)%",
            style
        )

        left = re.search(
            r"left:\s*([\d.]+)%",
            style
        )

        nummer = div.select_one(
            ".tm-shirt-number"
        )

        name = div.select_one(
            ".formation-number-name"
        )

        if not top:
            continue

        if not left:
            continue

        if not nummer:
            continue

        if not name:
            continue

        spieler.append(
            {
                "nummer": nummer.get_text(
                    strip=True
                ),
                "name": name.get_text(
                    " ",
                    strip=True
                ),
                "x": float(
                    left.group(1)
                ),
                "y": float(
                    top.group(1)
                ),
            }
        )

    # Doppelte Spieler entfernen
    eindeutig = []

    gesehen = set()

    for spieler_daten in spieler:

        key = (
            spieler_daten["nummer"],
            spieler_daten["name"],
            spieler_daten["x"],
            spieler_daten["y"],
        )

        if key in gesehen:
            continue

        gesehen.add(key)

        eindeutig.append(
            spieler_daten
        )

    spieler = eindeutig

    if len(spieler) != 11:

        raise ValueError(
            "Transfermarkt: Es wurden nicht exakt "
            f"11 Startspieler gefunden "
            f"({'Heim' if is_heim else 'Gast'}: "
            f"{len(spieler)} Spieler)."
        )

    return spieler


def _extract_formation(soup):
    text = soup.get_text(
        "\n"
    )

    match = re.search(
        r"Startaufstellung:\s*([0-9\- ]+)",
        text
    )

    if match:
        return match.group(1).strip()

    return ""


def lade_transfermarkt(
    url,
    teamname=""
):

    if not url:
        raise ValueError(
            "Transfermarkt-URL fehlt."
        )

    if not teamname:
        raise ValueError(
            "Teamname fehlt."
        )

    html = ""

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        try:

            page = browser.new_page()

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(
                3000
            )

            html = page.content()

        finally:

            browser.close()

    if not html:
        raise ValueError(
            "Transfermarkt-Seite konnte nicht geladen werden."
        )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ---------------------------------------------------------
    # MANNSCHAFTEN EINDEUTIG ERMITTELN
    # ---------------------------------------------------------

    heim_team, gast_team = (
        _extract_team_names(soup)
    )

    # ---------------------------------------------------------
    # GEWÜNSCHTES TEAM EINDEUTIG ZUORDNEN
    # ---------------------------------------------------------

    heim_match = _team_match(
        teamname,
        heim_team
    )

    gast_match = _team_match(
        teamname,
        gast_team
    )

    if heim_match and gast_match:

        raise ValueError(
            f"Team '{teamname}' passt gleichzeitig auf "
            f"Heim '{heim_team}' und Gast '{gast_team}'."
        )

    if not heim_match and not gast_match:

        raise ValueError(
            f"Team '{teamname}' wurde im Transfermarkt-Spielbericht "
            f"nicht gefunden.\n"
            f"Gefunden wurde:\n"
            f"Heim: {heim_team}\n"
            f"Gast: {gast_team}"
        )

    is_heim = heim_match

    gegner = (
        gast_team
        if is_heim
        else heim_team
    )

    # ---------------------------------------------------------
    # RESULTAT
    # ---------------------------------------------------------

    score = _extract_score(
        soup
    )

    if score is None:

        raise ValueError(
            f"Kein eindeutiges Endresultat gefunden für:\n"
            f"{heim_team} - {gast_team}"
        )

    heim_tore, gast_tore = score

    if is_heim:

        eigenes_resultat = (
            f"{heim_tore}:{gast_tore}"
        )

        eigene_tore = heim_tore
        gegentore = gast_tore

    else:

        eigenes_resultat = (
            f"{gast_tore}:{heim_tore}"
        )

        eigene_tore = gast_tore
        gegentore = heim_tore

    if eigene_tore > gegentore:
        ausgang = "Sieg"

    elif eigene_tore < gegentore:
        ausgang = "Niederlage"

    else:
        ausgang = "Unentschieden"

    # ---------------------------------------------------------
    # FORMATION
    # ---------------------------------------------------------

    formation = _extract_formation(
        soup
    )

    # ---------------------------------------------------------
    # SPIELER
    # ---------------------------------------------------------

    spieler = _extract_players(
        soup,
        is_heim
    )

    # ---------------------------------------------------------
    # ENDKONTROLLE
    # ---------------------------------------------------------

    if not _team_match(
        teamname,
        heim_team if is_heim else gast_team
    ):

        raise ValueError(
            "Sicherheitsprüfung der Mannschaftszuordnung "
            "fehlgeschlagen."
        )

    if _normalize_team(gegner) == _normalize_team(teamname):

        raise ValueError(
            "Sicherheitsprüfung fehlgeschlagen: "
            "Gegner entspricht dem eigenen Team."
        )

    return {
        "logo": "",

        "team": (
            heim_team
            if is_heim
            else gast_team
        ),

        "formation": formation,

        "resultat": eigenes_resultat,

        "letzter_gegner": gegner,

        "gegner": gegner,

        "ausgang": ausgang,

        "spieler": spieler,
    }
