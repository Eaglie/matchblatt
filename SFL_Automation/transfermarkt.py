from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import unicodedata
from datetime import datetime


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

    name = re.sub(
        r"[^a-z0-9]",
        "",
        name.lower()
    )

    name = re.sub(
        r"(18|19|20)\d{2}$",
        "",
        name
    )

    return name


def _team_match(
    input_team,
    page_team
):
    a = _normalize_team(
        input_team
    )

    b = _normalize_team(
        page_team
    )

    if not a or not b:
        return False

    if a == b:
        return True

    for prefix in (
        "fc",
        "ac",
        "sc",
        "bc",
    ):
        if a.startswith(prefix):
            a = a[len(prefix):]

        if b.startswith(prefix):
            b = b[len(prefix):]

    return bool(
        a
        and b
        and a == b
    )


def _extract_team_names(
    soup,
    teamname
):
    heim_team = ""
    gast_team = ""

    heim = soup.select_one(
        ".sb-team.sb-heim a.sb-club__link, "
        ".sb-team.sb-heim a, "
        ".sb-heim a"
    )

    gast = soup.select_one(
        ".sb-team.sb-gast a.sb-club__link, "
        ".sb-team.sb-gast a, "
        ".sb-gast a"
    )

    if heim:
        heim_team = heim.get_text(
            " ",
            strip=True
        )

    if gast:
        gast_team = gast.get_text(
            " ",
            strip=True
        )

    if not heim_team or not gast_team:

        texts = []

        for element in soup.select(
            "h1, h2, h3, h4, "
            ".sb-team, "
            "[class*='team'], "
            "[class*='club']"
        ):

            text = element.get_text(
                " ",
                strip=True
            )

            if (
                text
                and " - " in text
            ):
                texts.append(text)

        sources = []

        h1 = soup.select_one(
            "h1"
        )

        if h1:
            sources.append(
                h1.get_text(
                    " ",
                    strip=True
                )
            )

        if soup.title:
            sources.append(
                soup.title.get_text(
                    " ",
                    strip=True
                )
            )

        meta = soup.select_one(
            'meta[property="og:title"]'
        )

        if (
            meta
            and meta.get("content")
        ):
            sources.append(
                meta.get("content")
            )

        for text in sources + texts:

            pair = text.split(
                ",",
                1
            )[0].strip()

            if " - " not in pair:
                continue

            t1, t2 = [
                x.strip()
                for x in pair.split(
                    " - ",
                    1
                )
            ]

            if _team_match(
                teamname,
                t1
            ):

                heim_team = t1
                gast_team = t2
                break

            if _team_match(
                teamname,
                t2
            ):

                heim_team = t1
                gast_team = t2
                break

    if (
        not heim_team
        or not gast_team
    ):

        raise ValueError(
            "Transfermarkt: Heim- und "
            "Gastteam konnten nicht "
            "eindeutig gefunden werden."
        )

    heim_match = _team_match(
        teamname,
        heim_team
    )

    gast_match = _team_match(
        teamname,
        gast_team
    )

    if heim_match == gast_match:

        raise ValueError(
            f"Transfermarkt: '{teamname}' "
            "konnte nicht eindeutig einem "
            "Team zugeordnet werden.\n"
            f"Heim: {heim_team}\n"
            f"Gast: {gast_team}"
        )

    return (
        heim_team,
        gast_team,
        heim_match
    )


def _extract_score(
    soup
):
    score_box = soup.select_one(
        ".sb-core-info"
    )

    sources = []

    if score_box:
        sources.extend(
            score_box.stripped_strings
        )

    sources.extend(
        soup.stripped_strings
    )

    for text in sources:

        text = text.strip()

        if not re.fullmatch(
            r"\d{1,2}:\d{1,2}",
            text
        ):
            continue

        a, b = map(
            int,
            text.split(":")
        )

        if (
            a <= 20
            and b <= 20
        ):

            return (
                a,
                b
            )

    raise ValueError(
        "Transfermarkt: Endresultat "
        "konnte nicht eindeutig "
        "gefunden werden."
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
        return match.group(
            1
        ).strip()

    return ""


def _extract_players(
    soup,
    is_heim,
    teamname
):
    if is_heim:

        selector = (
            "div.sb-aufstellung-heim "
            "div.formation-player-container"
        )

    else:

        selector = (
            "div.sb-aufstellung-gast "
            "div.formation-player-container"
        )

    containers = soup.select(
        selector
    )

    if not containers:

        alle = soup.select(
            "div.formation-player-container"
        )

        if len(alle) >= 22:

            if is_heim:
                containers = alle[:11]
            else:
                containers = alle[11:22]

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

    eindeutig = []
    gesehen = set()

    for player in spieler:

        key = (
            player["name"],
            player["x"],
            player["y"]
        )

        if key in gesehen:
            continue

        gesehen.add(
            key
        )

        eindeutig.append(
            player
        )

    spieler = eindeutig

    if len(spieler) != 11:

        raise ValueError(
            "Transfermarkt: Für "
            f"'{teamname}' wurden nicht "
            "exakt 11 Startspieler "
            f"gefunden (gefunden: "
            f"{len(spieler)})."
        )

    return spieler


def _parse_date(
    text
):
    match = re.search(
        r"(\d{2}\.\d{2}\.\d{2,4})",
        text
    )

    if not match:
        return None

    value = match.group(
        1
    )

    if len(
        value.rsplit(
            ".",
            1
        )[1]
    ) == 4:

        date_format = "%d.%m.%Y"

    else:

        date_format = "%d.%m.%y"

    try:

        return datetime.strptime(
            value,
            date_format
        )

    except ValueError:

        return None


def _get_schedule_url(
    soup,
    teamname
):
    for a in soup.select(
        "a[href]"
    ):

        href = a.get(
            "href",
            ""
        )

        text = a.get_text(
            " ",
            strip=True
        )

        if (
            "/startseite/verein/"
            not in href
        ):
            continue

        if not _team_match(
            teamname,
            text
        ):
            continue

        id_match = re.search(
            r"/startseite/verein/(\d+)",
            href
        )

        if not id_match:
            continue

        verein_id = (
            id_match.group(1)
        )

        slug_match = re.search(
            r"/([^/]+)/startseite/verein/",
            href
        )

        if not slug_match:
            continue

        slug = slug_match.group(
            1
        )

        season_match = re.search(
            r"saison_id/(\d{4})",
            href
        )

        if season_match:

            season = (
                season_match.group(1)
            )

        else:

            season = str(
                datetime.now().year
            )

        return (
            "https://www.transfermarkt.de/"
            f"{slug}/spielplan/verein/"
            f"{verein_id}/saison_id/"
            f"{season}"
        )

    return None


def _extract_last_match_from_schedule(
    soup,
    teamname,
    current_url
):
    current_id_match = re.search(
        r"spielbericht/(\d+)",
        current_url or ""
    )

    current_id = (
        current_id_match.group(1)
        if current_id_match
        else None
    )

    schedule_url = _get_schedule_url(
        soup,
        teamname
    )

    if not schedule_url:
        return None

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True
            )

            try:

                page = browser.new_page()

                page.goto(
                    schedule_url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                try:

                    page.wait_for_load_state(
                        "networkidle",
                        timeout=10000
                    )

                except Exception:

                    pass

                schedule_soup = BeautifulSoup(
                    page.content(),
                    "html.parser"
                )

            finally:

                browser.close()

    except Exception:

        return None

    kandidaten = []

    heute = datetime.now().date()

    for row in schedule_soup.select(
        "tr"
    ):

        row_text = row.get_text(
            " ",
            strip=True
        )

        if not row_text:
            continue

        match_date = _parse_date(
            row_text
        )

        if not match_date:
            continue

        if match_date.date() > heute:
            continue

        links = row.select(
            "a[href]"
        )

        report_links = []

        for a in links:

            href = a.get(
                "href",
                ""
            )

            if "/spielbericht/" in href:
                report_links.append(
                    href
                )

        if not report_links:
            continue

        if current_id:

            aktuelles_spiel = False

            for href in report_links:

                match = re.search(
                    r"spielbericht/(\d+)",
                    href
                )

                if (
                    match
                    and match.group(1)
                    == current_id
                ):

                    aktuelles_spiel = True
                    break

            if aktuelles_spiel:
                continue

        # ---------------------------------------------
        # Beide Mannschaften aus den Vereinslinks holen
        # ---------------------------------------------

        teams = []

        for a in links:

            href = a.get(
                "href",
                ""
            )

            text = a.get_text(
                " ",
                strip=True
            )

            if (
                "/startseite/verein/"
                in href
                and text
                and text not in teams
            ):

                teams.append(
                    text
                )

        if len(teams) < 2:
            continue

        own_index = None

        for i, team in enumerate(
            teams
        ):

            if _team_match(
                teamname,
                team
            ):

                own_index = i
                break

        if own_index is None:
            continue

        if own_index == 0:

            opponent = teams[1]

        else:

            opponent = teams[0]

        # ---------------------------------------------
        # Heim/Auswärts
        # ---------------------------------------------

        cells = row.select(
            "td"
        )

        ha = None

        for cell in cells:

            cell_text = cell.get_text(
                " ",
                strip=True
            )

            if cell_text in (
                "H",
                "A"
            ):

                ha = cell_text
                break

        if ha not in (
            "H",
            "A"
        ):

            continue

        # ---------------------------------------------
        # Resultat NUR aus Ergebniszelle
        # ---------------------------------------------

        score = None

        for cell in cells:

            if not cell.select_one(
                'a[href*="/spielbericht/"]'
            ):
                continue

            cell_text = cell.get_text(
                " ",
                strip=True
            )

            matches = re.findall(
                r"(?<!\d)"
                r"(\d{1,2})"
                r"\s*:\s*"
                r"(\d{1,2})"
                r"(?!\d)",
                cell_text
            )

            for a_str, b_str in matches:

                a = int(
                    a_str
                )

                b = int(
                    b_str
                )

                # Uhrzeiten wie 16:30
                # ausschliessen

                if b >= 60:
                    continue

                if (
                    a <= 20
                    and b <= 20
                ):

                    score = (
                        a,
                        b
                    )

                    break

            if score:
                break

        if not score:
            continue

        home_goals, away_goals = score

        if ha == "H":

            own_goals = home_goals
            opponent_goals = away_goals

        else:

            own_goals = away_goals
            opponent_goals = home_goals

        resultat = (
            f"{own_goals}:"
            f"{opponent_goals}"
        )

        if own_goals > opponent_goals:

            ausgang = "Sieg"

        elif own_goals < opponent_goals:

            ausgang = "Niederlage"

        else:

            ausgang = "Unentschieden"

        kandidaten.append(
            {
                "datum": match_date,
                "resultat": resultat,
                "gegner": opponent,
                "ausgang": ausgang,
            }
        )

    if not kandidaten:
        return None

    kandidaten.sort(
        key=lambda x: x["datum"],
        reverse=True
    )

    return kandidaten[0]


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
    navigation_error = None

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        try:

            page = browser.new_page()

            try:

                page.goto(
                    url,
                    wait_until="commit",
                    timeout=30000
                )

            except Exception as exc:

                navigation_error = exc

            try:

                page.wait_for_selector(
                    "div.formation-player-container",
                    timeout=8000
                )

            except Exception:

                pass

            html = page.content()

        finally:

            browser.close()

    if not html:

        if navigation_error:

            raise ValueError(
                "Transfermarkt-Seite konnte "
                "nicht geladen werden: "
                f"{navigation_error}"
            ) from navigation_error

        raise ValueError(
            "Transfermarkt-Seite konnte "
            "nicht geladen werden."
        )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ---------------------------------------------
    # Mannschaften
    # ---------------------------------------------

    (
        heim_team,
        gast_team,
        is_heim
    ) = _extract_team_names(
        soup,
        teamname
    )

    # ---------------------------------------------
    # Gegner
    # ---------------------------------------------

    if is_heim:

        gegner = gast_team

    else:

        gegner = heim_team

    if _team_match(
        teamname,
        gegner
    ):

        raise ValueError(
            "Transfermarkt: Gegner entspricht "
            "dem eigenen Team."
        )

    # ---------------------------------------------
    # Resultat der aktuellen Spielberichtseite
    # ---------------------------------------------

    (
        h_tore,
        g_tore
    ) = _extract_score(
        soup
    )

    if is_heim:

        eigene = h_tore
        fremde = g_tore

    else:

        eigene = g_tore
        fremde = h_tore

    aktuelles_resultat = (
        f"{eigene}:{fremde}"
    )

    if eigene > fremde:

        aktueller_ausgang = "Sieg"

    elif eigene < fremde:

        aktueller_ausgang = "Niederlage"

    else:

        aktueller_ausgang = "Unentschieden"

    # ---------------------------------------------
    # Formation
    # ---------------------------------------------

    formation = _extract_formation(
        soup
    )

    # ---------------------------------------------
    # Spieler
    # ---------------------------------------------

    spieler = _extract_players(
        soup,
        is_heim,
        teamname
    )

    # ---------------------------------------------
    # LETZTES SPIEL
    # ---------------------------------------------

    letztes_spiel = (
        _extract_last_match_from_schedule(
            soup,
            teamname,
            url
        )
    )

    if letztes_spiel:

        aktuelles_resultat = (
            letztes_spiel["resultat"]
        )

        gegner = (
            letztes_spiel["gegner"]
        )

        aktueller_ausgang = (
            letztes_spiel["ausgang"]
        )

    # ---------------------------------------------
    # Sicherheitsprüfungen
    # ---------------------------------------------

    erkanntes_team = (
        heim_team
        if is_heim
        else gast_team
    )

    if not _team_match(
        teamname,
        erkanntes_team
    ):

        raise ValueError(
            "Transfermarkt: Sicherheitsprüfung "
            "der Teamzuordnung fehlgeschlagen."
        )

    if _team_match(
        erkanntes_team,
        gegner
    ):

        raise ValueError(
            "Transfermarkt: Eigenes Team und "
            "Gegner sind identisch."
        )

    if len(spieler) != 11:

        raise ValueError(
            "Transfermarkt: Es müssen exakt "
            "11 Startspieler vorhanden sein."
        )

    return {
        "logo": "",
        "team": erkanntes_team,
        "formation": formation,
        "resultat": aktuelles_resultat,
        "letzter_gegner": gegner,
        "gegner": gegner,
        "ausgang": aktueller_ausgang,
        "spieler": spieler,
    }
