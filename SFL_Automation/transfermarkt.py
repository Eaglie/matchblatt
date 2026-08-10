from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import unicodedata


# =========================================================
# TEAMNAMEN
# =========================================================

def _normalize_team(name):
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
    name = name.replace("&", "and")

    name = re.sub(
        r"[^a-z0-9]+",
        "",
        name
    )

    # FC Basel 1893 -> FC Basel
    name = re.sub(
        r"(18|19|20)\d{2}$",
        "",
        name
    )

    return name


def _team_match(input_team, page_team):
    a = _normalize_team(input_team)
    b = _normalize_team(page_team)

    if not a or not b:
        return False

    if a == b:
        return True

    prefixes = (
        "fc",
        "ac",
        "sc",
        "bc",
    )

    aa = a
    bb = b

    for prefix in prefixes:
        if aa.startswith(prefix):
            aa = aa[len(prefix):]

        if bb.startswith(prefix):
            bb = bb[len(prefix):]

    return bool(
        aa
        and bb
        and aa == bb
    )


# =========================================================
# SEITE LADEN
# =========================================================

def _load_page(page, url):
    """
    Lädt eine Transfermarkt-Seite.
    Transfermarkt kann die Navigation offen halten;
    deshalb verwenden wir domcontentloaded mit Fallback.
    """

    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )
    except Exception:
        pass

    page.wait_for_timeout(5000)

    html = page.content()

    if not html or len(html) < 1000:
        raise ValueError(
            "Transfermarkt-Seite konnte nicht "
            "ausreichend geladen werden."
        )

    return html


# =========================================================
# TEAMNAMEN AUS SPIELBERICHT
# =========================================================

def _extract_team_names(soup, teamname):
    """
    Ermittelt Heim- und Gastmannschaft.
    """

    # -----------------------------------------------------
    # Klassische Transfermarkt-Struktur
    # -----------------------------------------------------

    heim_box = soup.select_one(
        ".sb-team.sb-heim"
    )

    gast_box = soup.select_one(
        ".sb-team.sb-gast"
    )

    if heim_box and gast_box:

        heim_link = heim_box.select_one(
            "a[href*='/verein/']"
        )

        gast_link = gast_box.select_one(
            "a[href*='/verein/']"
        )

        if heim_link and gast_link:

            heim = heim_link.get_text(
                " ",
                strip=True
            )

            gast = gast_link.get_text(
                " ",
                strip=True
            )

            if (
                heim
                and gast
                and not _team_match(
                    heim,
                    gast
                )
            ):
                return heim, gast

    # -----------------------------------------------------
    # sb-team allgemein
    # -----------------------------------------------------

    gefunden = []

    for box in soup.select(
        ".sb-team"
    ):

        link = box.select_one(
            "a[href*='/verein/']"
        )

        if not link:
            continue

        name = link.get_text(
            " ",
            strip=True
        )

        if name and name not in gefunden:
            gefunden.append(name)

    if len(gefunden) == 2:

        if not _team_match(
            gefunden[0],
            gefunden[1]
        ):
            return (
                gefunden[0],
                gefunden[1]
            )

    # -----------------------------------------------------
    # H1 / Spielüberschrift
    # -----------------------------------------------------

    for element in soup.select(
        "h1"
    ):

        text = element.get_text(
            " ",
            strip=True
        )

        if " - " not in text:
            continue

        teile = text.split(
            " - ",
            1
        )

        if len(teile) != 2:
            continue

        heim = teile[0].strip()
        gast = teile[1].strip()

        if (
            heim
            and gast
            and not _team_match(
                heim,
                gast
            )
        ):
            return heim, gast

    # -----------------------------------------------------
    # Bekannter Transfermarkt-Titel
    # -----------------------------------------------------

    text = soup.get_text(
        " ",
        strip=True
    )

    match = re.search(
        r"([A-Za-zÄÖÜäöüÉÈÀÇçéèà' .\-]+?)\s+-\s+"
        r"([A-Za-zÄÖÜäöüÉÈÀÇçéèà' .\-]+?)"
        r"\s+\d+:\d+",
        text
    )

    if match:

        heim = match.group(1).strip()
        gast = match.group(2).strip()

        if (
            heim
            and gast
            and not _team_match(
                heim,
                gast
            )
        ):
            return heim, gast

    raise ValueError(
        "Transfermarkt: Heim- und Gastteam "
        "konnten nicht eindeutig bestimmt werden."
    )


# =========================================================
# RESULTAT
# =========================================================

def _extract_score(soup):

    selectors = [
        ".sb-core-info",
        ".sb-endstand",
        ".sb-result",
        ".sb-score",
        ".sb-final-score",
    ]

    for selector in selectors:

        for element in soup.select(
            selector
        ):

            for text in element.stripped_strings:

                match = re.fullmatch(
                    r"\s*(\d+)\s*:\s*(\d+)\s*",
                    text
                )

                if not match:
                    continue

                a = int(
                    match.group(1)
                )

                b = int(
                    match.group(2)
                )

                if (
                    0 <= a <= 30
                    and 0 <= b <= 30
                ):
                    return a, b

    # Fallback: komplette Seite
    kandidaten = []

    for text in soup.stripped_strings:

        match = re.fullmatch(
            r"\s*(\d+)\s*:\s*(\d+)\s*",
            text
        )

        if not match:
            continue

        a = int(
            match.group(1)
        )

        b = int(
            match.group(2)
        )

        if (
            0 <= a <= 30
            and 0 <= b <= 30
        ):
            kandidaten.append(
                (a, b)
            )

    if len(kandidaten) == 1:
        return kandidaten[0]

    raise ValueError(
        "Transfermarkt: Endresultat konnte "
        "nicht eindeutig gefunden werden."
    )


# =========================================================
# AUFSTELLUNG
# =========================================================

def _aufstellung_url(url):
    """
    Aus

    /spielbericht/index/spielbericht/4897293

    wird

    /spielbericht/aufstellung/spielbericht/4897293
    """

    match = re.search(
        r"/spielbericht/(?:index/)?spielbericht/(\d+)",
        url
    )

    if not match:
        raise ValueError(
            "Transfermarkt: Spielbericht-ID "
            "konnte aus der URL nicht gelesen werden."
        )

    spielbericht_id = match.group(1)

    return (
        "https://www.transfermarkt.de/"
        "spielbericht/aufstellung/spielbericht/"
        f"{spielbericht_id}"
    )


# =========================================================
# SPIELER AUS AUFSTELLUNGSSEITE
# =========================================================

def _extract_players_from_lineup(
    soup,
    teamname,
    heim_team,
    gast_team
):
    """
    Liest die Startelf aus der Transfermarkt-
    Aufstellungsseite.

    Transfermarkt stellt die beiden Startaufstellungen
    nacheinander dar:

        1. Heimteam: 11 Spieler
        2. Gastteam: 11 Spieler

    Die grafische x/y-Position wird NICHT zur
    Teamzuordnung verwendet.
    """

    # ---------------------------------------------------------
    # Alle Formation-Spieler in DOM-Reihenfolge
    # ---------------------------------------------------------

    containers = soup.select(
        "div.formation-player-container"
    )

    if not containers:

        containers = soup.select(
            ".formation-player-container"
        )

    if len(containers) != 22:

        raise ValueError(
            "Transfermarkt: Es wurden nicht exakt "
            f"22 Formation-Spieler gefunden. "
            f"Gefunden: {len(containers)}."
        )

    # ---------------------------------------------------------
    # Spieler aus einem Container lesen
    # ---------------------------------------------------------

    def lese_spieler(div):

        nummer = div.select_one(
            ".tm-shirt-number"
        )

        name = div.select_one(
            ".formation-number-name"
        )

        if not nummer or not name:
            return None

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

        if not top or not left:
            return None

        return {
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

    # ---------------------------------------------------------
    # Alle 22 Spieler auslesen
    # ---------------------------------------------------------

    alle_spieler = []

    for div in containers:

        spieler = lese_spieler(
            div
        )

        if spieler is None:
            continue

        alle_spieler.append(
            spieler
        )

    # ---------------------------------------------------------
    # Es müssen exakt 22 gültige Spieler sein.
    # ---------------------------------------------------------

    if len(alle_spieler) != 22:

        raise ValueError(
            "Transfermarkt: Von den 22 "
            "Formation-Spielern konnten nur "
            f"{len(alle_spieler)} eindeutig "
            "ausgelesen werden."
        )

    # ---------------------------------------------------------
    # Heim/Gast anhand der Transfermarkt-
    # Aufstellungsreihenfolge.
    # ---------------------------------------------------------

    if _team_match(
        teamname,
        heim_team
    ):

        spieler = alle_spieler[:11]

    elif _team_match(
        teamname,
        gast_team
    ):

        spieler = alle_spieler[11:22]

    else:

        raise ValueError(
            f"Transfermarkt: '{teamname}' "
            "konnte keiner der beiden "
            "Aufstellungen zugeordnet werden.\n"
            f"Heim: {heim_team}\n"
            f"Gast: {gast_team}"
        )

    # ---------------------------------------------------------
    # Sicherheitsprüfung
    # ---------------------------------------------------------

    if len(spieler) != 11:

        raise ValueError(
            "Transfermarkt: Die zugeordnete "
            f"Startelf enthält {len(spieler)} "
            "statt 11 Spieler."
        )

    # Keine doppelten Spieler

    namen = [
        (
            p["nummer"],
            p["name"]
        )
        for p in spieler
    ]

    if len(set(namen)) != 11:

        raise ValueError(
            "Transfermarkt: Die zugeordnete "
            "Startelf enthält doppelte Spieler."
        )

    return spieler


# =========================================================
# FORMATION
# =========================================================

def _extract_formation(
    soup
):

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


# =========================================================
# HAUPTFUNKTION
# =========================================================

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

            try:

                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

            except Exception:
                pass

            page.wait_for_timeout(
                5000
            )

            html = page.content()

        finally:

            browser.close()

    if not html:

        raise ValueError(
            "Transfermarkt-Seite konnte "
            "nicht geladen werden."
        )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ---------------------------------------------------------
    # TEAMS
    # ---------------------------------------------------------

    (
        heim_team,
        gast_team
    ) = _extract_team_names(
        soup,
        teamname
    )

    # ---------------------------------------------------------
    # TEAMZUORDNUNG
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
            f"Transfermarkt: '{teamname}' "
            "passt gleichzeitig auf Heim "
            f"'{heim_team}' und Gast "
            f"'{gast_team}'."
        )

    if not heim_match and not gast_match:

        raise ValueError(
            f"Transfermarkt: '{teamname}' "
            "wurde nicht gefunden.\n"
            f"Heim: {heim_team}\n"
            f"Gast: {gast_team}"
        )

    is_heim = heim_match

    # ---------------------------------------------------------
    # GEGNER
    # ---------------------------------------------------------

    gegner = (
        gast_team
        if is_heim
        else heim_team
    )

    if _team_match(
        teamname,
        gegner
    ):

        raise ValueError(
            "Transfermarkt: Eigenes Team "
            "und Gegner sind identisch."
        )

    # ---------------------------------------------------------
    # RESULTAT
    # ---------------------------------------------------------

    heim_tore, gast_tore = (
        _extract_score(
            soup
        )
    )

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

    # ---------------------------------------------------------
    # AUSGANG
    # ---------------------------------------------------------

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
    # AUFSTELLUNG
    # ---------------------------------------------------------

    lineup_url = _aufstellung_url(
        url
    )

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

            try:

                page.goto(
                    lineup_url,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

            except Exception:
                pass

            page.wait_for_timeout(
                5000
            )

            lineup_html = page.content()

        finally:

            browser.close()

    if not lineup_html:

        raise ValueError(
            "Transfermarkt-Aufstellungsseite "
            "konnte nicht geladen werden."
        )

    lineup_soup = BeautifulSoup(
        lineup_html,
        "html.parser"
    )

    # ---------------------------------------------------------
    # SPIELER
    # ---------------------------------------------------------

    spieler = _extract_players_from_lineup(
        lineup_soup,
        teamname,
        heim_team,
        gast_team
    )

    # ---------------------------------------------------------
    # ABSCHLIESSENDE SICHERHEITSPRÜFUNG
    # ---------------------------------------------------------

    erkannter_verein = (
        heim_team
        if is_heim
        else gast_team
    )

    if not _team_match(
        teamname,
        erkannter_verein
    ):

        raise ValueError(
            "Transfermarkt: "
            "Teamzuordnung fehlgeschlagen."
        )

    if _team_match(
        erkannter_verein,
        gegner
    ):

        raise ValueError(
            "Transfermarkt: Eigenes Team "
            "und Gegner sind identisch."
        )

    if len(spieler) != 11:

        raise ValueError(
            "Transfermarkt: Es wurden nicht "
            "exakt 11 Spieler zugeordnet."
        )

    return {
        "logo": "",

        "team": erkannter_verein,

        "formation": formation,

        "resultat": eigenes_resultat,

        "letzter_gegner": gegner,

        "gegner": gegner,

        "ausgang": ausgang,

        "spieler": spieler,
    }
