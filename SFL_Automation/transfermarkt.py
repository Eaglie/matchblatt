from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import unicodedata


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

    # Jahreszahlen am Ende entfernen
    # z.B. FC Basel 1893 -> FC Basel
    name = re.sub(
        r"(18|19|20)\d{2}$",
        "",
        name
    )

    return name


def _team_match(input_team, page_team):
    """
    Vergleicht Vereinsnamen robust.

    Beispiele:
    FC Basel 1893 == FC Basel
    FC St. Gallen 1879 == FC St. Gallen
    FC Lausanne-Sport == Lausanne-Sport
    """

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

    a_without_prefix = a
    b_without_prefix = b

    for prefix in prefixes:

        if a_without_prefix.startswith(prefix):
            a_without_prefix = (
                a_without_prefix[len(prefix):]
            )

        if b_without_prefix.startswith(prefix):
            b_without_prefix = (
                b_without_prefix[len(prefix):]
            )

    if (
        a_without_prefix
        and b_without_prefix
        and a_without_prefix == b_without_prefix
    ):
        return True

    return False


def _find_team_links(soup):
    kandidaten = []

    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a.get(
            "href",
            ""
        )

        text = a.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        if "/verein/" not in href:
            continue

        if len(text) < 2:
            continue

        item = (
            text,
            href
        )

        if item not in kandidaten:
            kandidaten.append(item)

    return kandidaten


def _extract_team_names(
    soup,
    teamname
):
    """
    Ermittelt Heim- und Gastmannschaft.
    Es wird niemals geraten.
    """

    # ---------------------------------------------------------
    # 1. Klassische Transfermarkt-Struktur
    # ---------------------------------------------------------

    heim_box = soup.select_one(
        ".sb-team.sb-heim"
    )

    gast_box = soup.select_one(
        ".sb-team.sb-gast"
    )

    if heim_box and gast_box:

        heim_link = heim_box.select_one(
            "a.sb-club__link"
        )

        gast_link = gast_box.select_one(
            "a.sb-club__link"
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
                and _normalize_team(heim)
                != _normalize_team(gast)
            ):
                return heim, gast

    # ---------------------------------------------------------
    # 2. Überschrift
    # ---------------------------------------------------------

    for selector in [
        "h1",
        ".sb-headline",
        ".sb-ansicht-verein",
    ]:

        element = soup.select_one(
            selector
        )

        if not element:
            continue

        text = element.get_text(
            " ",
            strip=True
        )

        match = re.search(
            r"(.+?)\s+-\s+(.+?)(?:\s*,|\s*$)",
            text
        )

        if not match:
            continue

        heim = match.group(1).strip()
        gast = match.group(2).strip()

        if (
            heim
            and gast
            and _normalize_team(heim)
            != _normalize_team(gast)
        ):

            return heim, gast

    # ---------------------------------------------------------
    # 3. Vereinslinks
    # ---------------------------------------------------------

    links = _find_team_links(
        soup
    )

    normalized_requested = _normalize_team(
        teamname
    )

    passende = []

    for name, href in links:

        if _team_match(
            teamname,
            name
        ):
            passende.append(
                (name, href)
            )

    if len(passende) == 1:

        eigener_name = passende[0][0]

        andere = []

        for item in links:

            if not _team_match(
                teamname,
                item[0]
            ):
                andere.append(
                    item
                )

        # Genau ein möglicher Gegner
        if len(andere) == 1:

            teams = soup.select(
                ".sb-team"
            )

            ordered = []

            for team in teams:

                link = team.select_one(
                    "a[href*='/verein/']"
                )

                if not link:
                    continue

                name = link.get_text(
                    " ",
                    strip=True
                )

                if name:
                    ordered.append(
                        name
                    )

            if len(ordered) == 2:

                return (
                    ordered[0],
                    ordered[1]
                )

            raise ValueError(
                "Transfermarkt: Das gewünschte Team "
                "wurde gefunden, aber die Heim-/Gast-"
                "Reihenfolge konnte nicht eindeutig "
                "bestimmt werden."
            )

    raise ValueError(
        "Transfermarkt: Heim- und Gastteam konnten "
        "nicht eindeutig bestimmt werden."
    )


def _extract_score(soup):

    score_box = soup.select_one(
        ".sb-core-info"
    )

    if not score_box:

        score_box = soup.select_one(
            ".sb-endstand"
        )

    if not score_box:

        score_box = soup.select_one(
            ".sb-result"
        )

    if score_box:

        for text in score_box.stripped_strings:

            text = text.strip()

            match = re.fullmatch(
                r"(\d+)\s*:\s*(\d+)",
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

    raise ValueError(
        "Transfermarkt: Endresultat konnte "
        "nicht eindeutig gefunden werden."
    )


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


def _extract_players(
    soup,
    is_heim
):
    """
    Holt ausschließlich die Startelf des
    eindeutig bestimmten Teams.
    """

    if is_heim:

        container = soup.select_one(
            "div.sb-aufstellung-heim"
        )

        team_label = "Heim"

    else:

        container = soup.select_one(
            "div.sb-aufstellung-gast"
        )

        team_label = "Gast"

    if not container:

        raise ValueError(
            f"Transfermarkt: {team_label}-Aufstellung "
            "nicht gefunden."
        )

    containers = container.select(
        "div.formation-player-container"
    )

    if not containers:

        raise ValueError(
            f"Transfermarkt: Keine Spieler in der "
            f"{team_label}-Aufstellung gefunden."
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

        if not (
            top
            and left
            and nummer
            and name
        ):
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

    # ---------------------------------------------------------
    # DUPLIKATE ENTFERNEN
    # ---------------------------------------------------------

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

        gesehen.add(
            key
        )

        eindeutig.append(
            spieler_daten
        )

    if len(eindeutig) != 11:

        raise ValueError(
            f"Transfermarkt: Die {team_label}-Startelf "
            f"enthält nicht exakt 11 Spieler. "
            f"Gefunden: {len(eindeutig)}."
        )

    return eindeutig


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

                # Transfermarkt kann die Navigation
                # offen halten. Bereits geladenes HTML
                # trotzdem auswerten.
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
    # HEIM / GAST
    # ---------------------------------------------------------

    heim_team, gast_team = (
        _extract_team_names(
            soup,
            teamname
        )
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
            f"Transfermarkt: '{teamname}' passt "
            f"gleichzeitig auf Heim '{heim_team}' "
            f"und Gast '{gast_team}'."
        )

    if not heim_match and not gast_match:

        raise ValueError(
            f"Transfermarkt: '{teamname}' wurde "
            f"nicht gefunden.\n"
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

    if _normalize_team(
        gegner
    ) == _normalize_team(
        teamname
    ):

        raise ValueError(
            "Transfermarkt: Eigener Verein und "
            "Gegner sind identisch."
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
    # SPIELER
    # ---------------------------------------------------------

    spieler = _extract_players(
        soup,
        is_heim
    )

    # ---------------------------------------------------------
    # LETZTE SICHERHEITSPRÜFUNG
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
            "Transfermarkt: Sicherheitsprüfung "
            "der Teamzuordnung fehlgeschlagen."
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
