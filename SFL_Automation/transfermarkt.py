from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import unicodedata
from datetime import datetime
import requests
from urllib.parse import quote


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

    # Transfermarkt verwendet bei einigen Schweizer Vereinen Kurz-/Spitznamen.
    aliases = {
        "grasshopperclubzurich": {"grasshoppers", "grasshopper"},
        "grasshoppers": {"grasshopperclubzurich", "grasshopper"},
        "grasshopper": {"grasshopperclubzurich", "grasshoppers"},
        "fcstgallen": {"fcstgallen1879", "stgallen"},
        "fcstgallen1879": {"fcstgallen", "stgallen"},
        "stgallen": {"fcstgallen", "fcstgallen1879"},
    }

    if b in aliases.get(a, set()) or a in aliases.get(b, set()):
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
    """

    heim_team = ""
    gast_team = ""

    # 1. Klassische Transfermarkt-Struktur
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

    # 2. H1 / Seitentitel / og:title
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

        match_paar = titel_text.split(",", 1)[0].strip()

        if " - " not in match_paar:
            continue

        t1, t2 = [
            x.strip()
            for x in match_paar.split(" - ", 1)
        ]

        if t1 and t2 and (_team_match(teamname, t1) or _team_match(teamname, t2)):
            heim_team = t1
            gast_team = t2
            break

    # 3. Vereinslinks der Spielseite
    if not heim_team or not gast_team:
        team_links = []

        for a in soup.select('a[href*="/startseite/verein/"]'):
            text = a.get_text(" ", strip=True)
            if text and text not in team_links:
                team_links.append(text)

        if team_links:
            own_index = None
            for i, text in enumerate(team_links):
                if _team_match(teamname, text):
                    own_index = i
                    break

            if own_index is not None:
                for i, text in enumerate(team_links):
                    if i == own_index or _team_match(teamname, text):
                        continue

                    heim_team = text if own_index > i else team_links[own_index]
                    gast_team = team_links[own_index] if own_index > i else text
                    break

    if not heim_team or not gast_team:
        raise ValueError(
            "Transfermarkt: Heim- und Gastteam konnten nicht eindeutig gefunden werden."
        )

    heim_match = _team_match(teamname, heim_team)
    gast_match = _team_match(teamname, gast_team)

    if heim_match and gast_match:
        raise ValueError(f"Transfermarkt: '{teamname}' passt gleichzeitig auf Heim- und Gastteam.")

    if not heim_match and not gast_match:
        raise ValueError(
            f"Transfermarkt: '{teamname}' wurde nicht eindeutig gefunden.\n"
            f"Heim: {heim_team}\nGast: {gast_team}"
        )

    return heim_team, gast_team, heim_match


def _extract_score(soup):
    raw_resultat = ""
    score_box = soup.select_one(".sb-core-info")

    if score_box:
        for txt in score_box.stripped_strings:
            if re.fullmatch(r"\d+:\d+", txt):
                a, b = map(int, txt.split(":"))
                if a <= 20 and b <= 20:
                    raw_resultat = txt
                    break

    if not raw_resultat:
        for txt in soup.stripped_strings:
            if re.fullmatch(r"\d+:\d+", txt):
                a, b = map(int, txt.split(":"))
                if a <= 10 and b <= 10:
                    raw_resultat = txt
                    break

    if not raw_resultat:
        raise ValueError("Transfermarkt: Endresultat konnte nicht eindeutig gefunden werden.")

    return tuple(map(int, raw_resultat.split(":")))


def _extract_formation(soup):
    text = soup.get_text("\n")
    match = re.search(r"Startaufstellung:\s*([0-9\- ]+)", text)
    if match:
        return match.group(1).strip()
    return ""


def _extract_players(soup, is_heim, teamname):
    containers = soup.select(
        "div.sb-aufstellung-heim div.formation-player-container" if is_heim
        else "div.sb-aufstellung-gast div.formation-player-container"
    )

    if not containers:
        containers = soup.select("div.formation-player-container")
        if len(containers) >= 22:
            containers = containers[:11] if is_heim else containers[11:22]
        else:
            raise ValueError(f"Transfermarkt: Die Startaufstellung von '{teamname}' konnte nicht gefunden werden.")

    spieler = []
    for div in containers:
        style = div.get("style", "")
        top = re.search(r"top:\s*([\d.]+)%", style)
        left = re.search(r"left:\s*([\d.]+)%", style)
        nummer = div.select_one(".tm-shirt-number")
        name = div.select_one(".formation-number-name")

        if not top or not left or not nummer or not name:
            continue

        spieler.append({
            "nummer": nummer.get_text(strip=True),
            "name": name.get_text(" ", strip=True),
            "x": float(left.group(1)),
            "y": float(top.group(1)),
        })

    # Doppelte entfernen
    eindeutig = []
    gesehen = set()
    for s in spieler:
        key = (s["name"], s["x"], s["y"])
        if key not in gesehen:
            gesehen.add(key)
            eindeutig.append(s)

    if len(eindeutig) != 11:
        raise ValueError(f"Transfermarkt: Für '{teamname}' wurden nicht exakt 11 Startspieler gefunden (gefunden: {len(eindeutig)}).")

    return eindeutig


# ---------------------------------------------------------
# TRANSFERMARKT JSON-API
# ---------------------------------------------------------

_TM_API_BASE = "https://transfermarkt-api.fly.dev"
_TM_LAST_API_CALL = 0.0


def _tm_api_wait():
    global _TM_LAST_API_CALL
    import time
    now = time.monotonic()
    wait = 1.65 - (now - _TM_LAST_API_CALL)
    if wait > 0:
        time.sleep(wait)
    _TM_LAST_API_CALL = time.monotonic()


def _tm_api_get(path, timeout=20):
    import time
    max_attempts = 3
    last_error = None

    for attempt in range(1, max_attempts + 1):
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
            last_error = "Transfermarkt-API konnte nicht erreicht werden."
            if attempt < max_attempts:
                time.sleep(1.0)
                continue
            return None, last_error

        if response.status_code == 200:
            try:
                return response.json(), None
            except ValueError:
                return None, "Transfermarkt-API hat kein gültiges JSON geliefert."

        last_error = f"Transfermarkt-API HTTP {response.status_code}."
        if response.status_code not in (502, 503, 504) or attempt >= max_attempts:
            return None, last_error

        time.sleep(1.0)

    return None, last_error or "Transfermarkt-API fehlgeschlagen."


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
    has_real_coordinates = True

    for player in players:
        if not isinstance(player, dict):
            has_real_coordinates = False
            break
        left = _tm_player_value(player, "styleLeft", "style_left", "left", "x")
        top = _tm_player_value(player, "styleTop", "style_top", "top", "y")
        try:
            if left is None or top is None:
                raise ValueError
            float(left)
            float(top)
        except (TypeError, ValueError):
            has_real_coordinates = False
            break

    if has_real_coordinates:
        result = []
        for player in players:
            name = _tm_player_value(player, "name", "playerName", "fullName")
            number = _tm_player_value(player, "shirtNumber", "shirt_number", "number", "jerseyNumber")
            left = float(_tm_player_value(player, "styleLeft", "style_left", "left", "x"))
            top = float(_tm_player_value(player, "styleTop", "style_top", "top", "y"))

            if name:
                result.append({
                    "nummer": str(number) if number is not None else "",
                    "name": str(name).strip(),
                    "x": left,
                    "y": top,
                })
        return result

    # Fallback-Koordinaten aus der Formation
    nums = [int(x) for x in re.findall(r"\d+", formation or "")]
    if sum(nums) != 10:
        nums = [4, 3, 3]

    rows = [1] + nums
    if sum(rows) != len(players):
        rows = [1, len(players) - 1]

    y_values = [88.0, 70.0, 50.0, 31.0, 16.0]
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
        raise ValueError(error or "Transfermarkt-API liefert keine Spieldaten.")

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
        opponent = away_team
    elif _team_match(teamname, away_team):
        is_home = False
        own_side = away_side
        opponent = home_team
    else:
        raise ValueError(f"Transfermarkt-API: Team '{teamname}' passt nicht zu '{home_team}' oder '{away_team}'.")

    home_goals = _tm_player_value(home_side, "score", "goals")
    away_goals = _tm_player_value(away_side, "score", "goals")
    if home_goals is None or away_goals is None:
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
    # REPARATUR DES ABGESCHNITTENEN CODES:
    players = _tm_player_value(own_side, "startingLineup", "starting_lineup", "lineup", "players")
    if not isinstance(players, list):
        players = []

    koordinaten = _tm_make_coordinates(players, formation, is_home)

    return {
        "heim_team": home_team,
        "gast_team": away_team,
        "own_goals": own_goals,
        "opp_goals": opp_goals,
        "ausgang": ausgang,
        "formation": formation,
        "spieler": koordinaten,
        "is_home": is_home,
    }
