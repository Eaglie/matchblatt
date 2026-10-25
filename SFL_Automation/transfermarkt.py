from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import unicodedata
from datetime import datetime
import requests


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

    name = re.sub(
        r"[^a-z0-9]",
        "",
        name
    )

    # Jahreszahl am Ende entfernen:
    # FC Basel 1893 -> FC Basel
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
    """
    Vergleicht SFL-Teamname mit Transfermarkt-Teamname.
    """

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

    return (
        bool(aa)
        and bool(bb)
        and aa == bb
    )


def _extract_team_names(
    soup,
    teamname
):
    """
    Ermittelt Heim- und Gastteam robust aus einer Transfermarkt-Spielberichtseite.

    Transfermarkt ändert die HTML-Struktur gelegentlich. Deshalb werden mehrere
    unabhängige Quellen verwendet:
    1. klassische sb-team-Struktur
    2. Seitentitel / H1 / og:title
    3. Vereinslinks der Spielseite
    4. sichtbare Überschriften als letzter Fallback
    """

    heim_team = ""
    gast_team = ""

    # ---------------------------------------------------------
    # 1. Klassische Transfermarkt-Struktur
    # ---------------------------------------------------------

    heim_box = (
        soup.select_one(".sb-team.sb-heim a.sb-club__link")
        or soup.select_one(".sb-team.sb-heim a")
        or soup.select_one(".sb-heim a")
    )

    gast_box = (
        soup.select_one(".sb-team.sb-gast a.sb-club__link")
        or soup.select_one(".sb-team.sb-gast a")
        or soup.select_one(".sb-gast a")
    )

    if heim_box:
        heim_team = heim_box.get_text(" ", strip=True)

    if gast_box:
        gast_team = gast_box.get_text(" ", strip=True)

    # ---------------------------------------------------------
    # 2. H1 / Seitentitel / og:title
    # ---------------------------------------------------------

    titel_quellen = []

    h1 = soup.select_one("h1")
    if h1:
        titel_quellen.append(h1.get_text(" ", strip=True))

    if soup.title:
        titel_quellen.append(soup.title.get_text(" ", strip=True))

    meta_title = soup.select_one('meta[property="og:title"]')
    if meta_title and meta_title.get("content"):
        titel_quellen.append(meta_title["content"].strip())

    for titel_text in titel_quellen:
        if not titel_text:
            continue

        # Transfermarkt verwendet normalerweise:
        # "Heimteam - Gastteam, Datum"
        match_paar = titel_text.split(",", 1)[0].strip()

        if " - " not in match_paar:
            continue

        t1, t2 = [
            x.strip()
            for x in match_paar.split(" - ", 1)
        ]

        if (
            t1
            and t2
            and _team_match(teamname, t1)
        ):
            heim_team = t1
            gast_team = t2
            break

        if (
            t1
            and t2
            and _team_match(teamname, t2)
        ):
            heim_team = t1
            gast_team = t2
            break

    # ---------------------------------------------------------
    # 3. NEU: Vereinslinks der eigentlichen Spielseite
    #
    # Das ist der wichtige zusätzliche Fallback. Die bisherige
    # Version war hier auf .sb-team / .sb-heim / .sb-gast
    # angewiesen. Diese Klassen sind auf aktuellen Transfermarkt-
    # Seiten nicht immer vorhanden.
    # ---------------------------------------------------------

    if not heim_team or not gast_team:
        team_links = []

        for a in soup.select('a[href*="/startseite/verein/"]'):
            text = a.get_text(" ", strip=True)

            if not text:
                continue

            # Vereinsnamen können mehrfach auf der Seite vorkommen.
            if text not in team_links:
                team_links.append(text)

        # Zuerst nach einem Paar suchen, bei dem eines der Teams
        # eindeutig dem eingegebenen Team entspricht.
        if team_links:
            own_index = None

            for i, text in enumerate(team_links):
                if _team_match(teamname, text):
                    own_index = i
                    break

            if own_index is not None:
                # Der zweite relevante Vereinslink auf der
                # Spielseite ist normalerweise der Gegner.
                for i, text in enumerate(team_links):
                    if i == own_index:
                        continue

                    if _team_match(teamname, text):
                        continue

                    heim_team = (
                        text
                        if own_index > i
                        else team_links[own_index]
                    )
                    gast_team = (
                        team_links[own_index]
                        if own_index > i
                        else text
                    )
                    break

    # ---------------------------------------------------------
    # 4. Breiter Fallback über sichtbare Überschriften
    # ---------------------------------------------------------

    kandidaten = []

    if not heim_team or not gast_team:
        for element in soup.select(
            "h1, h2, h3, h4, "
            ".sb-team, "
            "[class*='team'], "
            "[class*='club']"
        ):
            text = element.get_text(" ", strip=True)

            if not text:
                continue

            kandidaten.append(text)

            if " - " not in text:
                continue

            paar = text.split(",", 1)[0].strip()

            if " - " not in paar:
                continue

            t1, t2 = [
                x.strip()
                for x in paar.split(" - ", 1)
            ]

            if (
                t1
                and t2
                and _team_match(teamname, t1)
            ):
                heim_team = t1
                gast_team = t2
                break

            if (
                t1
                and t2
                and _team_match(teamname, t2)
            ):
                heim_team = t1
                gast_team = t2
                break

    # ---------------------------------------------------------
    # 5. Letzter Rohtext-Fallback
    # ---------------------------------------------------------

    if not heim_team or not gast_team:
        for text in kandidaten:
            match = re.search(
                r"([A-Za-zÀ-ÿ0-9.'’&()\- ]+?)"
                r"\s+-\s+"
                r"([A-Za-zÀ-ÿ0-9.'’&()\- ]+)",
                text
            )

            if not match:
                continue

            t1 = match.group(1).strip()
            t2 = match.group(2).strip()

            if _team_match(teamname, t1):
                heim_team = t1
                gast_team = t2
                break

            if _team_match(teamname, t2):
                heim_team = t1
                gast_team = t2
                break

    # ---------------------------------------------------------
    # Sicherheitsprüfungen
    # ---------------------------------------------------------

    if not heim_team or not gast_team:
        raise ValueError(
            "Transfermarkt: Heim- und Gastteam "
            "konnten nicht eindeutig gefunden werden."
        )

    if _team_match(heim_team, gast_team):
        raise ValueError(
            "Transfermarkt: Heimteam und Gastteam "
            "sind identisch."
        )

    heim_match = _team_match(teamname, heim_team)
    gast_match = _team_match(teamname, gast_team)

    if heim_match and gast_match:
        raise ValueError(
            f"Transfermarkt: '{teamname}' passt "
            "gleichzeitig auf Heim- und Gastteam."
        )

    if not heim_match and not gast_match:
        raise ValueError(
            f"Transfermarkt: '{teamname}' wurde "
            "nicht eindeutig gefunden.\n"
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
    """
    Holt das Endresultat.
    """

    raw_resultat = ""

    score_box = soup.select_one(
        ".sb-core-info"
    )

    if score_box:

        for txt in score_box.stripped_strings:

            if re.fullmatch(
                r"\d+:\d+",
                txt
            ):

                a, b = map(
                    int,
                    txt.split(":")
                )

                if (
                    a <= 20
                    and b <= 20
                ):

                    raw_resultat = txt
                    break

    if not raw_resultat:

        for txt in soup.stripped_strings:

            if re.fullmatch(
                r"\d+:\d+",
                txt
            ):

                a, b = map(
                    int,
                    txt.split(":")
                )

                if (
                    a <= 10
                    and b <= 10
                ):

                    raw_resultat = txt
                    break

    if not raw_resultat:
        raise ValueError(
            "Transfermarkt: Endresultat "
            "konnte nicht eindeutig gefunden werden."
        )

    return tuple(
        map(
            int,
            raw_resultat.split(":")
        )
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
    """
    Holt ausschließlich die Startelf des
    tatsächlich gewünschten Teams.
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

    # Falls die Teamcontainer nicht vorhanden sind:
    # komplette Liste nehmen und anhand der
    # Transfermarkt-Reihenfolge trennen.
    if not containers:

        alle = soup.select(
            "div.formation-player-container"
        )

        if len(alle) >= 22:

            if is_heim:
                containers = alle[:11]

            else:
                containers = alle[11:22]

        else:

            raise ValueError(
                "Transfermarkt: Die Startaufstellung "
                f"von '{teamname}' konnte nicht "
                "eindeutig gefunden werden."
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

        if (
            not top
            or not left
            or not nummer
            or not name
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

    # Doppelte Spieler entfernen
    eindeutig = []

    gesehen = set()

    for s in spieler:

        key = (
            s["name"],
            s["x"],
            s["y"]
        )

        if key in gesehen:
            continue

        gesehen.add(
            key
        )

        eindeutig.append(
            s
        )

    spieler = eindeutig

    if len(spieler) != 11:

        raise ValueError(
            "Transfermarkt: Für "
            f"'{teamname}' wurden nicht exakt "
            f"11 Startspieler gefunden "
            f"(gefunden: {len(spieler)})."
        )

    return spieler



def _extract_last_match_from_schedule(
    soup,
    teamname,
    current_url
):
    """
    Holt das letzte bereits gespielte Spiel des Teams aus dem
    Transfermarkt-Spielplan. Das aktuell eingegebene Spiel wird
    anhand seiner Spiel-ID ausgeschlossen.

    Wichtig: Das Resultat wird aus der Ergebnis-Spalte gelesen,
    niemals aus dem gesamten Zeilentext, weil dort auch die Uhrzeit
    im Format 16:30 steht.
    """

    current_match = re.search(
        r"spielbericht/(\d+)",
        current_url or ""
    )
    current_match_id = (
        current_match.group(1)
        if current_match
        else ""
    )

    team_link = None

    for a in soup.select("a[href]"):
        href = a.get("href", "")
        text = a.get_text(" ", strip=True)

        if "/startseite/verein/" not in href:
            continue

        if _team_match(teamname, text):
            team_link = href
            break

    if not team_link:
        return None

    id_match = re.search(
        r"/startseite/verein/(\d+)",
        team_link
    )
    if not id_match:
        return None

    verein_id = id_match.group(1)

    slug_match = re.search(
        r"/([^/]+)/startseite/verein/",
        team_link
    )
    if not slug_match:
        return None

    slug = slug_match.group(1)

    season_match = re.search(
        r"saison_id/(\d{4})",
        team_link
    )
    saison = (
        season_match.group(1)
        if season_match
        else str(datetime.now().year)
    )

    schedule_url = (
        "https://www.transfermarkt.de/"
        f"{slug}/spielplan/verein/{verein_id}/"
        f"saison_id/{saison}"
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
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

    for row in schedule_soup.select("tr"):
        row_text = row.get_text(" ", strip=True)
        if not row_text:
            continue

        # Aktuelles Spiel niemals als "letztes Spiel" verwenden.
        if current_match_id:
            row_ids = re.findall(
                r"spielbericht/(\d+)",
                " ".join(
                    a.get("href", "")
                    for a in row.select("a[href]")
                )
            )
            if current_match_id in row_ids:
                continue

        date_match = re.search(
            r"(\d{2}\.\d{2}\.\d{2,4})",
            row_text
        )
        if not date_match:
            continue

        date_text = date_match.group(1)
        date_format = (
            "%d.%m.%Y"
            if len(date_text.rsplit(".", 1)[1]) == 4
            else "%d.%m.%y"
        )

        try:
            match_date = datetime.strptime(
                date_text,
                date_format
            )
        except ValueError:
            continue

        # Vereinslinks liefern die beiden Teams zuverlässig.
        team_links = []
        for a in row.select("a[href]"):
            href = a.get("href", "")
            text = a.get_text(" ", strip=True)
            if "/startseite/verein/" in href and text:
                if text not in team_links:
                    team_links.append(text)

        if len(team_links) < 2:
            continue

        own_index = None
        for i, text in enumerate(team_links):
            if _team_match(teamname, text):
                own_index = i
                break

        if own_index is None:
            continue

        opponent = ""
        for i, text in enumerate(team_links):
            if i != own_index and not _team_match(teamname, text):
                opponent = text
                break

        if not opponent:
            continue

        # RESULTAT NUR AUS DER ERGEBNIS-ZELLE DES SPIELBERICHTS.
        # Uhrzeiten wie 16:30 werden nicht als Resultat verwendet.

        score_text = ""

        for cell in row.select("td"):

            if not cell.select_one('a[href*="/spielbericht/"]'):
                continue

            matches = re.findall(
                r"(?<!\d)(\d{1,2})\s*:\s*(\d{1,2})(?!\d)",
                cell.get_text(" ", strip=True)
            )

            for a, b in matches:

                a = int(a)
                b = int(b)

                # Keine Uhrzeit wie 16:30
                if b >= 60:
                    continue

                # Plausibler Fussball-Spielstand
                if a <= 20 and b <= 20:
                    score_text = f"{a}:{b}"

            if score_text:
                break

        if not score_text:
            continue

        # Ort-Spalte: H = eigenes Team zuhause, A = auswärts.
        cells = row.select("td")
        ha = None
        for cell in cells:
            cell_text = cell.get_text(" ", strip=True)
            if cell_text in ("H", "A"):
                ha = cell_text
                break

        if ha not in ("H", "A"):
            continue

        if ha == "H":
            eigenes = f"{a}:{b}"
            eigene_tore, fremde_tore = a, b
        else:
            eigenes = f"{b}:{a}"
            eigene_tore, fremde_tore = b, a

        if eigene_tore > fremde_tore:
            ausgang = "Sieg"
        elif eigene_tore < fremde_tore:
            ausgang = "Niederlage"
        else:
            ausgang = "Unentschieden"

        kandidaten.append({
            "datum": match_date,
            "resultat": eigenes,
            "gegner": opponent,
            "ausgang": ausgang,
        })

    if not kandidaten:
        return None

    kandidaten.sort(
        key=lambda x: x["datum"],
        reverse=True
    )

    return kandidaten[0]


# ---------------------------------------------------------
# TRANSFERMARKT JSON-API
# ---------------------------------------------------------

_TM_API_BASE = "https://transfermarkt-api.fly.dev"
_TM_LAST_API_CALL = 0.0


def _tm_api_wait():
    """Respektiert das öffentliche API-Limit von 2 Requests / 3 Sekunden."""
    global _TM_LAST_API_CALL
    import time
    now = time.monotonic()
    wait = 1.65 - (now - _TM_LAST_API_CALL)
    if wait > 0:
        time.sleep(wait)
    _TM_LAST_API_CALL = time.monotonic()


def _tm_api_get(path, timeout=20):
    _tm_api_wait()
    try:
        response = requests.get(
            _TM_API_BASE + path,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )
    except requests.RequestException:
        return None, "Transfermarkt-API konnte nicht erreicht werden."

    if response.status_code != 200:
        return None, f"Transfermarkt-API HTTP {response.status_code}."

    try:
        return response.json(), None
    except ValueError:
        return None, "Transfermarkt-API hat kein gültiges JSON geliefert."


def _tm_team_from_side(side):
    if not isinstance(side, dict):
        return "", None
    name = side.get("name") or ""
    team_id = side.get("id")
    return str(name).strip(), str(team_id) if team_id is not None else None


def _tm_player_value(player, *keys):
    if not isinstance(player, dict):
        return None
    for key in keys:
        value = player.get(key)
        if value not in (None, ""):
            return value
    return None


def _tm_make_coordinates(players, formation, is_home):
    """Erzeugt die x/y-Felder des bisherigen Matchblatt-Formats."""
    nums = [int(x) for x in re.findall(r"\d+", formation or "")]
    if sum(nums) != 10:
        nums = [4, 3, 3]

    rows = [1] + nums
    if sum(rows) != len(players):
        # Fallback anhand der API-Reihenfolge.
        rows = [1, len(players) - 1]

    y_values = [88.0, 70.0, 50.0, 31.0, 16.0]
    if len(rows) > len(y_values):
        y_values = [88.0 - i * (72.0 / max(1, len(rows) - 1)) for i in range(len(rows))]

    result = []
    index = 0
    for row_index, count in enumerate(rows):
        if count <= 0:
            continue
        y = y_values[min(row_index, len(y_values) - 1)]
        for j in range(count):
            if index >= len(players):
                break
            x = 50.0 if count == 1 else 12.0 + (76.0 * j / (count - 1))
            player = players[index]
            name = _tm_player_value(player, "name", "playerName", "fullName")
            number = _tm_player_value(player, "shirtNumber", "shirt_number", "number", "jerseyNumber")
            if name:
                result.append({
                    "nummer": str(number) if number is not None else "",
                    "name": str(name).strip(),
                    "x": x,
                    "y": y if is_home else 100.0 - y,
                })
            index += 1

    return result


def _tm_api_last_match(player_id, current_id, team_id):
    """Liest das letzte bereits gespielte Match eines Startspielers."""
    if not player_id:
        return None

    data, _ = _tm_api_get(f"/players/{player_id}/matches?page_number=1")
    if not isinstance(data, dict):
        return None

    matches = data.get("matches")
    if not isinstance(matches, list):
        return None

    for match in matches:
        if not isinstance(match, dict):
            continue

        game_id = str(match.get("gameId", match.get("game_id", "")))
        if game_id == str(current_id):
            continue

        club = match.get("club") or {}
        opponent = match.get("opponent") or {}
        club_id = club.get("id") if isinstance(club, dict) else None
        if team_id and club_id is not None and str(club_id) != str(team_id):
            continue

        club_name = club.get("name", "") if isinstance(club, dict) else ""
        opponent_name = opponent.get("name", "") if isinstance(opponent, dict) else ""
        club_goals = match.get("clubGoals", match.get("club_goals"))
        opponent_goals = match.get("opponentGoals", match.get("opponent_goals"))
        if not club_name or not opponent_name or club_goals is None or opponent_goals is None:
            continue

        return (
            str(club_name),
            str(opponent_name),
            int(club_goals),
            int(opponent_goals),
        )

    return None


def _lade_transfermarkt_api(url, teamname):
    """Lädt einen Spielbericht über die aktuelle Transfermarkt-JSON-API."""
    match = re.search(r"spielbericht/(?:index/)?spielbericht/(\d+)", url or "")
    if not match:
        match = re.search(r"spielbericht/(\d+)", url or "")
    if not match:
        return None

    match_id = match.group(1)
    root, error = _tm_api_get(f"/games/{match_id}")
    if not isinstance(root, dict):
        # API kann zeitweise 5xx/504 liefern. In diesem Fall NICHT abbrechen,
        # sondern den bereits vorhandenen Playwright/HTML-Abruf verwenden.
        return None

    # Aktuelles API-5.0-Schema: home/away sind direkt auf oberster Ebene.
    home_side = root.get("home")
    away_side = root.get("away")
    if not isinstance(home_side, dict) or not isinstance(away_side, dict):
        return None

    home_team, home_id = _tm_team_from_side(home_side)
    away_team, away_id = _tm_team_from_side(away_side)
    if not home_team or not away_team:
        return None

    if _team_match(teamname, home_team):
        is_home = True
        own_side = home_side
        own_team = home_team
        own_id = home_id
        opponent = away_team
    elif _team_match(teamname, away_team):
        is_home = False
        own_side = away_side
        own_team = away_team
        own_id = away_id
        opponent = home_team
    else:
        raise ValueError(
            f"Transfermarkt-API: Team '{teamname}' passt nicht zu '{home_team}' oder '{away_team}'."
        )

    # In der aktuellen API 5.x liegt der Spielstand NICHT unter
    # root["score"]. Er steht direkt in home["score"] und away["score"].
    # Die API kann je nach Pydantic-Serialisierung camelCase oder
    # snake_case liefern; die beiden Varianten werden deshalb akzeptiert.
    home_goals = _tm_player_value(home_side, "score", "goals")
    away_goals = _tm_player_value(away_side, "score", "goals")
    if home_goals is None or away_goals is None:
        # Letzter Fallback für ältere/abweichende API-Antworten.
        score = root.get("score")
        if isinstance(score, dict):
            home_goals = score.get("home")
            away_goals = score.get("away")
    if home_goals is None or away_goals is None:
        raise ValueError("Transfermarkt-API: Heim-/Gasttore fehlen.")

    own_goals, opp_goals = (
        (int(home_goals), int(away_goals)) if is_home
        else (int(away_goals), int(home_goals))
    )

    if own_goals > opp_goals:
        ausgang = "Sieg"
    elif own_goals < opp_goals:
        ausgang = "Niederlage"
    else:
        ausgang = "Unentschieden"

    formation = own_side.get("formation") or ""
    players = own_side.get("startingLineup")
    if players is None:
        players = own_side.get("starting_lineup")
    if not isinstance(players, list) or len(players) < 11:
        raise ValueError(
            f"Transfermarkt-API: Aufstellung für {own_team} fehlt oder enthält weniger als 11 Spieler."
        )
    players = [p for p in players if isinstance(p, dict)][:11]

    spieler = _tm_make_coordinates(players, str(formation), is_home)
    if len(spieler) != 11:
        raise ValueError(f"Transfermarkt-API: Es konnten nur {len(spieler)} Spieler der Startelf verarbeitet werden.")

    result = {
        "logo": "",
        "team": own_team,
        "formation": str(formation),
        "resultat": f"{own_goals}:{opp_goals}",
        "letzter_gegner": opponent,
        "gegner": opponent,
        "ausgang": ausgang,
        "spieler": spieler,
    }

    # Für das Matchblatt wird zusätzlich das letzte Spiel benötigt.
    # Nur EIN Spieler pro Team wird abgefragt; die API liefert dessen
    # komplette Match-Historie. So bleiben die Requests überschaubar.
    first_player_id = _tm_player_value(players[0], "id", "playerId", "player_id")
    last = _tm_api_last_match(first_player_id, match_id, own_id)
    if last:
        last_team, last_opponent, last_own, last_opp = last
        # Die Match-Historie bezieht sich auf den Spieler und damit auf sein Team.
        if _team_match(last_team, own_team):
            result["resultat"] = f"{last_own}:{last_opp}"
            result["gegner"] = last_opponent
            result["letzter_gegner"] = last_opponent
            if last_own > last_opp:
                result["ausgang"] = "Sieg"
            elif last_own < last_opp:
                result["ausgang"] = "Niederlage"
            else:
                result["ausgang"] = "Unentschieden"

    return result


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

    # Render wird von Transfermarkt auf der normalen HTML-Seite geblockt.
    # Deshalb zuerst die aktuelle Transfermarkt-JSON-API verwenden.
    api_result = _lade_transfermarkt_api(url, teamname)
    if api_result is not None:
        return api_result

    html = ""
    navigation_error = None
    response_status = None
    final_url = url
    page_title = ""

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        try:

            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                locale="de-CH",
                extra_http_headers={
                    "Accept-Language": "de-CH,de;q=0.9,en;q=0.8"
                }
            )

            try:

                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                if response is not None:
                    response_status = response.status

                final_url = page.url

            except Exception as exc:
                navigation_error = exc

            # Transfermarkt kann Inhalte erst nach dem Laden
            # nachziehen. Kurz warten, ohne von einem bestimmten
            # Selector abhängig zu sein.
            try:
                page.wait_for_timeout(2500)
            except Exception:
                pass

            try:
                page_title = page.title()
            except Exception:
                page_title = ""

            html = page.content()

        finally:

            browser.close()

    if not html:
        if navigation_error is not None:
            raise ValueError(
                "Transfermarkt-Seite konnte nicht geladen werden. "
                f"URL: {url} | Fehler: {navigation_error}"
            ) from navigation_error

        raise ValueError(
            "Transfermarkt-Seite konnte nicht geladen werden."
        )

    # ---------------------------------------------------------
    # DIAGNOSE: Block-/Challenge-Seite erkennen
    # ---------------------------------------------------------

    html_lower = html.lower()
    text_preview = BeautifulSoup(
        html,
        "html.parser"
    ).get_text(" ", strip=True)

    block_markers = (
        "access denied",
        "forbidden",
        "captcha",
        "verify you are human",
        "checking your browser",
        "just a moment",
        "robot",
        "bot detection",
        "aws waf",
        "cloudfront",
    )

    found_markers = [
        marker
        for marker in block_markers
        if marker in html_lower or marker in text_preview.lower()
    ]

    if (
        response_status is not None
        and response_status >= 400
    ) or found_markers:

        preview = re.sub(
            r"\s+",
            " ",
            text_preview
        )[:500]

        raise ValueError(
            "Transfermarkt liefert keine normale Spielseite. "
            f"HTTP-Status: {response_status}; "
            f"Titel: {page_title!r}; "
            f"End-URL: {final_url}; "
            f"Erkannte Hinweise: {', '.join(found_markers) or 'keine'}; "
            f"Seiteninhalt: {preview!r}"
        )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ---------------------------------------------------------
    # MANNSCHAFTEN
    # ---------------------------------------------------------

    (
        heim_team,
        gast_team,
        is_heim
    ) = _extract_team_names(
        soup,
        teamname
    )

    # ---------------------------------------------------------
    # GEGNER
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # RESULTAT
    # ---------------------------------------------------------

    (
        h_tore,
        g_tore
    ) = _extract_score(
        soup
    )

    if is_heim:

        eigenes_resultat = (
            f"{h_tore}:{g_tore}"
        )

        eigene = h_tore
        fremde = g_tore

    else:

        eigenes_resultat = (
            f"{g_tore}:{h_tore}"
        )

        eigene = g_tore
        fremde = h_tore

    # ---------------------------------------------------------
    # AUSGANG
    # ---------------------------------------------------------

    if eigene > fremde:

        ausgang = "Sieg"

    elif eigene < fremde:

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
        is_heim,
        teamname
    )

    # LETZTES SPIEL: Resultat und Gegner aus dem Vereins-Spielplan.
    letztes_spiel = _extract_last_match_from_schedule(
        soup,
        teamname,
        url
    )

    if letztes_spiel:
        eigenes_resultat = letztes_spiel["resultat"]
        gegner = letztes_spiel["gegner"]
        ausgang = letztes_spiel["ausgang"]

    # ---------------------------------------------------------
    # ABSCHLIESSENDE SICHERHEITSPRÜFUNGEN
    # ---------------------------------------------------------

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

        "resultat": eigenes_resultat,

        "letzter_gegner": gegner,

        "gegner": gegner,

        "ausgang": ausgang,

        "spieler": spieler,
    }
