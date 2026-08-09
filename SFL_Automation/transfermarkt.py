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
    # 2. Alle sb-team Elemente
    # ---------------------------------------------------------

    teams = soup.select(
        ".sb-team"
    )

    gefunden = []

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

        if not name:
            continue

        if name not in gefunden:
            gefunden.append(
                name
            )

    if len(gefunden) >= 2:

        # Nur die ersten zwei Mannschaften
        heim = gefunden[0]
        gast = gefunden[1]

        if (
            _normalize_team(heim)
            != _normalize_team(gast)
        ):
            return heim, gast

    # ---------------------------------------------------------
    # 3. H1 / Überschrift
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

        # z.B.
        # FC Basel - Lausanne-Sport
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
    # 4. Vereinslinks
    # ---------------------------------------------------------

    links = _find_team_links(
        soup
    )

    passende = [
        name
        for name, href in links
        if _team_match(
            teamname,
            name
        )
    ]

    if len(passende) == 1:

        andere = [
            name
            for name, href in links
            if not _team_match(
                teamname,
                name
            )
        ]

        if len(andere) == 1:

            # Heim/Gast-Reihenfolge muss aus
            # der Seite stammen.
            ordered = []

            for team in soup.select(
                ".sb-team"
            ):

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
        "Transfermarkt: Heim- und Gastteam "
        "konnten nicht eindeutig bestimmt werden."
    )


def _score_from_text(text):

    if not text:
        return None

    match = re.fullmatch(
        r"\s*(\d+)\s*:\s*(\d+)\s*",
        text
    )

    if not match:
        return None

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
        return (
            a,
            b
        )

    return None


def _extract_score(soup):

    # ---------------------------------------------------------
    # Direkter Ergebnisbereich
    # ---------------------------------------------------------

    selectors = [
        ".sb-core-info",
        ".sb-endstand",
        ".sb-result",
        ".sb-score",
        ".sb-final-score",
    ]

    for selector in selectors:

        elements = soup.select(
            selector
        )

        for element in elements:

            for text in element.stripped_strings:

                score = _score_from_text(
                    text
                )

                if score:
                    return score

    # ---------------------------------------------------------
    # Text des oberen Spielbereichs
    # ---------------------------------------------------------

    for element in soup.find_all(
        ["div", "span"]
    ):

        classes = " ".join(
            element.get(
                "class",
                []
            )
        ).lower()

        if not any(
            x in classes
            for x in [
                "score",
                "result",
                "spielstand",
                "endstand",
                "core-info",
            ]
        ):
            continue

        score = _score_from_text(
            element.get_text(
                " ",
                strip=True
            )
        )

        if score:
            return score

    raise ValueError(
        "Transfermarkt: Endresultat konnte "
        "nicht eindeutig gefunden werden."
    )


def _player_from_div(div):

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


def _deduplicate_players(
    players
):

    result = []
    seen = set()

    for player in players:

        key = (
            player["nummer"],
            player["name"],
            player["x"],
            player["y"],
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            player
        )

    return result


def _extract_players(
    soup,
    is_heim
):

    # ---------------------------------------------------------
    # 1. Normaler Heim-/Gast-Container
    # ---------------------------------------------------------

    if is_heim:

        selectors = [
            "div.sb-aufstellung-heim",
            ".sb-aufstellung-heim",
        ]

        label = "Heim"

    else:

        selectors = [
            "div.sb-aufstellung-gast",
            ".sb-aufstellung-gast",
        ]

        label = "Gast"

    for selector in selectors:

        container = soup.select_one(
            selector
        )

        if not container:
            continue

        divs = container.select(
            "div.formation-player-container"
        )

        players = []

        for div in divs:

            player = _player_from_div(
                div
            )

            if player:
                players.append(
                    player
                )

        players = _deduplicate_players(
            players
        )

        if len(players) == 11:
            return players

    # ---------------------------------------------------------
    # 2. Alle Formation-Spieler
    #
    # Wenn Transfermarkt die Teamcontainer geändert hat,
    # stehen die Spieler häufig trotzdem gemeinsam im DOM.
    # Die Reihenfolge der beiden Aufstellungen wird dabei
    # anhand der y/x-Positionen nicht erraten.
    # ---------------------------------------------------------

    alle = soup.select(
        "div.formation-player-container"
    )

    if not alle:

        alle = soup.select(
            ".formation-player-container"
        )

    if not alle:

        raise ValueError(
            f"Transfermarkt: Keine "
            f"Formation-Spieler für {label} gefunden."
        )

    players = []

    for div in alle:

        player = _player_from_div(
            div
        )

        if player:
            players.append(
                player
            )

    players = _deduplicate_players(
        players
    )

    # ---------------------------------------------------------
    # 3. Genau 22 Spieler:
    # Transfermarkt liefert Heim und Gast gemeinsam.
    # Die beiden Gruppen werden anhand der horizontalen
    # Feldposition getrennt.
    # ---------------------------------------------------------

    if len(players) == 22:

        links = [
            p
            for p in players
            if p["x"] < 50
        ]

        rechts = [
            p
            for p in players
            if p["x"] >= 50
        ]

        if (
            len(links) == 11
            and len(rechts) == 11
        ):

            # Bei Transfermarkt ist die Aufstellung
            # des Heimteams links und die des Gastteams rechts.
            if is_heim:
                return links

            return rechts

    # ---------------------------------------------------------
    # 4. Niemals einfach [:11] / [11:] nehmen.
    # ---------------------------------------------------------

    raise ValueError(
        f"Transfermarkt: Die {label}-Startelf "
        "konnte nicht eindeutig bestimmt werden. "
        f"Gefundene Formation-Spieler: {len(players)}."
    )


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
    # HEIM / GAST
    # ---------------------------------------------------------

    heim_team, gast_team = (
        _extract_team_names(
            soup,
            teamname
        )
    )

    # ---------------------------------------------------------
    # EIGENES TEAM
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
            "nicht gefunden.\n"
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
