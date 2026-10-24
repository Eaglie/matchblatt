from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import urllib.parse
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

_TM_API_BASE = "https://tmapi.transfermarkt.technology"
_TM_LAST_API_CALL = 0.0


def _tm_api_wait():
    """Kleine Pause zwischen direkten Transfermarkt-JSON-Anfragen."""
    global _TM_LAST_API_CALL
    import time
    now = time.monotonic()
    wait = 0.25 - (now - _TM_LAST_API_CALL)
    if wait > 0:
        time.sleep(wait)
    _TM_LAST_API_CALL = time.monotonic()


def _tm_api_get(path, timeout=25):
    """Direkter Zugriff auf Transfermarkts interne JSON-API.

    Die offizielle Transfermarkt-Webseite ist auf Render durch Human Verification
    blockiert. Die aktuelle Community-API v4/v5 nutzt stattdessen genau diese
    interne JSON-API. Die Antwort hat das Format {success: true, data: ...}.
    """
    import time
    last_error = None
    for attempt in range(4):
        _tm_api_wait()
        try:
            response = requests.get(
                _TM_API_BASE + path,
                timeout=timeout,
                headers={
                    "User-Agent": "transfermarkt-api",
                    "Accept": "application/json",
                },
            )
        except requests.RequestException as exc:
            last_error = f"Netzwerkfehler: {exc}"
            if attempt < 3:
                time.sleep(2.0)
                continue
            return None, last_error

        if response.status_code == 200:
            try:
                body = response.json()
            except ValueError:
                return None, "Transfermarkt-JSON-API liefert kein gültiges JSON."
            if isinstance(body, dict) and body.get("success") and "data" in body:
                return body["data"], None
            return None, "Transfermarkt-JSON-API liefert eine unerwartete Antwort."

        last_error = f"HTTP {response.status_code}"
        if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
            retry_after = response.headers.get("Retry-After")
            try:
                delay = max(2.0, float(retry_after)) if retry_after else 4.0
            except (TypeError, ValueError):
                delay = 4.0
            time.sleep(delay)
            continue
        return None, f"Transfermarkt-JSON-API {last_error}."

    return None, f"Transfermarkt-JSON-API {last_error or 'unbekannter Fehler'}."

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


def _tm_position_text(player):
    """Liest die komplette Positionsinformation aus der API."""
    if not isinstance(player, dict):
        return ""

    parts = []

    def collect(value):
        if isinstance(value, str) and value.strip():
            parts.append(value.strip().lower())
        elif isinstance(value, dict):
            for value2 in value.values():
                collect(value2)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    for key in ("position", "positionName", "matchPosition"):
        collect(player.get(key))

    # Doppelte Begriffe entfernen, Reihenfolge aber erhalten.
    seen = set()
    return " ".join(
        x for x in parts
        if not (x in seen or seen.add(x))
    )


def _tm_position_group(player):
    """Ermittelt die natürliche Hauptposition; Winger bleiben flexibel."""
    pos = _tm_position_text(player)
    if not pos:
        return ""

    if any(x in pos for x in (
        "goalkeeper", "goalie", "keeper", "torwart"
    )):
        return "goalkeeper"

    if any(x in pos for x in (
        "centre-back", "center-back", "central defender",
        "left-back", "right-back", "full-back",
        "defender", "innenverteidiger",
        "aussenverteidiger", "außenverteidiger"
    )):
        return "defender"

    # Winger sind für die Aufstellung flexibel:
    # 4-4-2 -> Mittelfeld, 3-4-3 -> Angriff.
    if any(x in pos for x in (
        "left winger", "right winger", "left wing", "right wing",
        "winger", "aussenstürmer", "außenstürmer"
    )):
        return "wing"

    if any(x in pos for x in (
        "striker", "centre-forward", "center-forward",
        "forward", "stürmer"
    )):
        return "striker"

    if any(x in pos for x in (
        "midfielder", "midfield", "defensive midfield",
        "central midfield", "attacking midfield",
        "left midfield", "right midfield",
        "mittelfeld", "zentrales mittelfeld",
        "defensives mittelfeld"
    )):
        return "midfielder"

    return ""


def _tm_position_sort_key(player, group):
    """Sortiert innerhalb einer Reihe möglichst korrekt von links nach rechts."""
    pos = _tm_position_text(player)

    if group == "defender":
        if any(x in pos for x in ("left-back", "left back", "link")):
            return 10
        if any(x in pos for x in (
            "centre-back", "center-back", "central defender",
            "centre", "center", "innenverteidiger"
        )):
            return 20
        if any(x in pos for x in ("right-back", "right back", "rechts")):
            return 30
        return 20

    if group == "midfielder":
        if any(x in pos for x in ("left", "link")):
            return 10
        if any(x in pos for x in ("right", "rechts")):
            return 40
        if any(x in pos for x in ("defensive", "defensiv")):
            return 20
        if any(x in pos for x in ("central", "centre", "center", "zentr")):
            return 25
        if any(x in pos for x in ("attacking", "offensive")):
            return 30
        return 25

    if group == "striker":
        if any(x in pos for x in ("left", "link")):
            return 10
        if any(x in pos for x in ("right", "rechts")):
            return 30
        return 20

    return 20


def _tm_make_coordinates(players, formation, is_home):
    """Build match-sheet coordinates from player positions.

    Transfermarkt does not guarantee that the lineup array is in the visual
    left-to-right order shown on the pitch.  Therefore players are first
    assigned to the four formation rows and only then sorted horizontally.
    """
    nums = [int(x) for x in re.findall(r"\d+", formation or "")]
    if len(nums) != 3 or sum(nums) != 10:
        nums = [4, 3, 3]

    lineup = [p for p in players if isinstance(p, dict)][:11]
    if len(lineup) != 11:
        return []

    # Keep the position information broad enough for Transfermarkt's
    # English/German position labels, but make the goalkeeper/defender
    # checks win before winger/forward checks.
    def natural_group(player):
        pos = _tm_position_text(player).lower()

        if any(x in pos for x in (
            "goalkeeper", "goalie", "keeper", "torwart", "tw"
        )):
            return "goalkeeper"

        if any(x in pos for x in (
            "centre-back", "center-back", "central defender",
            "left-back", "right-back", "full-back", "fullback",
            "defender", "innenverteidiger", "aussenverteidiger",
            "außenverteidiger", "linksverteidiger", "rechtsverteidiger"
        )):
            return "defender"

        if any(x in pos for x in (
            "striker", "centre-forward", "center-forward",
            "centre forward", "center forward", "forward", "stürmer"
        )):
            return "striker"

        if any(x in pos for x in (
            "midfielder", "midfield", "defensive midfield",
            "central midfield", "attacking midfield", "left midfield",
            "right midfield", "mittelfeld", "zentrales mittelfeld",
            "defensives mittelfeld", "offensives mittelfeld"
        )):
            return "midfielder"

        if any(x in pos for x in (
            "left winger", "right winger", "left wing", "right wing",
            "winger", "aussenstürmer", "außenstürmer", "flügel"
        )):
            return "midfielder"

        return "unknown"

    buckets = {
        "goalkeeper": [],
        "defender": [],
        "midfielder": [],
        "striker": [],
        "unknown": [],
    }
    for player in lineup:
        buckets[natural_group(player)].append(player)

    needed = {
        "goalkeeper": 1,
        "defender": nums[0],
        "midfielder": nums[1],
        "striker": nums[2],
    }

    rows = {name: [] for name in needed}

    # First take players whose natural position matches the row.
    for name in ("goalkeeper", "defender", "midfielder", "striker"):
        rows[name] = buckets[name][:needed[name]]

    # Never move a recognised goalkeeper out of goal.  Fill only non-goalkeeper
    # gaps from players whose position could not be resolved or from an excess
    # bucket.  This is the important guard against Omlin becoming a field player.
    used = {id(player) for row in rows.values() for player in row}
    remaining = [player for player in lineup if id(player) not in used]

    for name in ("defender", "midfielder", "striker"):
        missing = needed[name] - len(rows[name])
        if missing <= 0:
            continue
        take = remaining[:missing]
        rows[name].extend(take)
        remaining = remaining[missing:]

    if len(rows["goalkeeper"]) != 1:
        return []
    if any(len(rows[name]) != needed[name] for name in ("defender", "midfielder", "striker")):
        return []

    def horizontal_key(player, row):
        pos = _tm_position_text(player).lower()

        if row == "defender":
            if any(x in pos for x in (
                "left-back", "left back", "leftback", "linksverteidiger",
                "linker außenverteidiger", "linker aussenverteidiger"
            )):
                return (10, 0)
            if any(x in pos for x in (
                "right-back", "right back", "rightback", "rechtsverteidiger",
                "rechter außenverteidiger", "rechter aussenverteidiger"
            )):
                return (40, 0)
            # Centre-backs occupy the two middle positions. Stable ordering
            # preserves the order supplied by Transfermarkt between them.
            return (25, 0)

        if row == "midfielder":
            if any(x in pos for x in (
                "left winger", "left wing", "left midfield", "left midfielder",
                "left-sided", "linker flügel", "linkes mittelfeld"
            )):
                return (10, 0)
            if any(x in pos for x in (
                "right winger", "right wing", "right midfield", "right midfielder",
                "right-sided", "rechter flügel", "rechtes mittelfeld"
            )):
                return (40, 0)
            # Central/defensive/attacking midfielders are deliberately kept
            # together in the centre; Python's stable sort preserves their
            # original Transfermarkt order.
            return (25, 0)

        if row == "striker":
            if any(x in pos for x in (
                "left forward", "left-sided", "left winger", "left wing",
                "linker flügel"
            )):
                return (10, 0)
            if any(x in pos for x in (
                "right forward", "right-sided", "right winger", "right wing",
                "rechter flügel"
            )):
                return (30, 0)
            return (20, 0)

        return (20, 0)

    # IMPORTANT: sort the actual row variable. Do not reference an undefined
    # `row` while assigning into the rows dictionary.
    ordered_rows = [rows["goalkeeper"]]
    for row_name in ("defender", "midfielder", "striker"):
        row = rows[row_name]
        ordered_rows.append(sorted(row, key=lambda player: horizontal_key(player, row_name)))

    # Match-sheet graphic: attack at top, goalkeeper at bottom.
    y_values = [88.0, 70.0, 50.0, 31.0]
    result = []
    for row_index, row in enumerate(ordered_rows):
        count = len(row)
        y = y_values[row_index]
        for j, player in enumerate(row):
            x = 50.0 if count == 1 else 12.0 + (76.0 * j / (count - 1))
            name = _tm_player_value(player, "name", "playerName", "fullName")
            number = _tm_player_value(
                player, "shirtNumber", "shirt_number", "number", "jerseyNumber"
            )
            if not name:
                continue
            result.append({
                "nummer": str(number) if number is not None else "",
                "name": str(name).strip(),
                "x": x,
                "y": y if is_home else 100.0 - y,
            })

    return result

def _tm_api_last_match(player_id, current_id, team_id):
    """Liest das letzte bereits gespielte Match aus der direkten JSON-API."""
    if not player_id:
        return None

    data, _ = _tm_api_get(f"/player/{player_id}/performance-game")
    if not isinstance(data, dict):
        return None

    performance = data.get("performance")
    if not isinstance(performance, list):
        return None

    matches = sorted(
        [m for m in performance if isinstance(m, dict)],
        key=lambda m: ((m.get("gameInformation") or {}).get("date") or {}).get("dateTimeUTC") or "",
        reverse=True,
    )

    for match in matches:
        info = match.get("gameInformation") or {}
        game_id = str(info.get("gameId", ""))
        if game_id == str(current_id):
            continue
        teams = match.get("clubsInformation") or {}
        club = teams.get("club") or {}
        opponent = teams.get("opponent") or {}
        club_id = club.get("clubId")
        if team_id and club_id is not None and str(club_id) != str(team_id):
            continue
        club_name = str(club.get("name") or "").strip()
        opponent_name = str(opponent.get("name") or "").strip()
        club_goals = club.get("goalsTotal")
        opponent_goals = opponent.get("goalsTotal")
        if club_goals is None or opponent_goals is None:
            continue
        if not club_name or not opponent_name:
            return (str(club_id or ""), str(opponent.get("clubId") or ""), int(club_goals), int(opponent_goals))
        return (club_name, opponent_name, int(club_goals), int(opponent_goals))

    return None

def _lade_transfermarkt_api(url, teamname):
    """Lädt den Spielbericht direkt aus Transfermarkts interner JSON-API."""
    match = re.search(r"spielbericht/(?:index/)?spielbericht/(\d+)", url or "")
    if not match:
        match = re.search(r"spielbericht/(\d+)", url or "")
    if not match:
        return None

    match_id = match.group(1)
    game, error = _tm_api_get(f"/game/{match_id}")
    if not isinstance(game, dict):
        raise ValueError(error or "Transfermarkt-JSON-API liefert keine Spieldaten.")

    base = game.get("baseDetails") or {}
    score = game.get("score") or {}
    home_side = game.get("homeClub") or {}
    away_side = game.get("awayClub") or {}
    if not isinstance(home_side, dict) or not isinstance(away_side, dict):
        raise ValueError("Transfermarkt-JSON-API: Heim-/Gastteam fehlt.")

    home_id = home_side.get("clubId")
    away_id = away_side.get("clubId")
    home_name = str(home_side.get("name") or "").strip()
    away_name = str(away_side.get("name") or "").strip()

    # Falls der Name nicht im Spielobjekt steht, Clubs separat auflösen.
    if not home_name and home_id:
        club, _ = _tm_api_get(f"/club/{home_id}")
        home_name = str((club or {}).get("name") or "").strip() if isinstance(club, dict) else ""
    if not away_name and away_id:
        club, _ = _tm_api_get(f"/club/{away_id}")
        away_name = str((club or {}).get("name") or "").strip() if isinstance(club, dict) else ""

    if not home_name or not away_name:
        raise ValueError("Transfermarkt-JSON-API: Heim- oder Gastteam fehlt.")

    if _team_match(teamname, home_name):
        is_home, own_side, own_team, own_id, opponent = True, home_side, home_name, home_id, away_name
    elif _team_match(teamname, away_name):
        is_home, own_side, own_team, own_id, opponent = False, away_side, away_name, away_id, home_name
    else:
        raise ValueError(f"Transfermarkt-JSON-API: Team '{teamname}' passt nicht zu '{home_name}' oder '{away_name}'.")

    home_goals = score.get("home")
    away_goals = score.get("away")
    if home_goals is None or away_goals is None:
        raise ValueError("Transfermarkt-JSON-API: Resultat fehlt.")
    own_goals, opp_goals = ((int(home_goals), int(away_goals)) if is_home else (int(away_goals), int(home_goals)))

    if own_goals > opp_goals:
        ausgang = "Sieg"
    elif own_goals < opp_goals:
        ausgang = "Niederlage"
    else:
        ausgang = "Unentschieden"

    lineup = own_side.get("lineup") or {}
    players = lineup.get("players") or []
    if not isinstance(players, list) or len(players) < 11:
        raise ValueError(f"Transfermarkt-JSON-API: Aufstellung für {own_team} enthält keine 11 Spieler.")
    players = [p for p in players if isinstance(p, dict)][:11]

    # Spielernamen aus der Batch-Route holen. Das ist genau die Auflösung, die
    # auch die aktuelle transfermarkt-api v5 intern verwendet.
    player_ids = [str(p.get("id")) for p in players if p.get("id") is not None]
    player_map = {}
    if player_ids:
        params = [("ids[]", pid) for pid in player_ids]
        pdata, perr = _tm_api_get("/players?" + urllib.parse.urlencode(params))
        if isinstance(pdata, list):
            player_map = {str(p.get("id")): p for p in pdata if isinstance(p, dict)}
        elif perr:
            raise ValueError(perr)

    normalized_players = []
    for p in players:
        pid = str(p.get("id")) if p.get("id") is not None else ""
        ref = player_map.get(pid) or {}
        q = dict(p)
        q["name"] = ref.get("name") or p.get("name") or ""
        q["shirtNumber"] = p.get("shirtNumber") or ref.get("shirtNumber") or ref.get("shirt_number")
        q["position"] = p.get("position") or ref.get("position") or ref.get("positionName") or {}
        normalized_players.append(q)

    if any(not p.get("name") for p in normalized_players):
        missing = sum(1 for p in normalized_players if not p.get("name"))
        raise ValueError(f"Transfermarkt-JSON-API: {missing} Spieler der Startelf konnten nicht aufgelöst werden.")

    formation = own_side.get("tactic", {}).get("tactic") if isinstance(own_side.get("tactic"), dict) else ""
    spieler = _tm_make_coordinates(normalized_players, str(formation or ""), is_home)
    if len(spieler) != 11:
        raise ValueError(f"Transfermarkt-JSON-API: Es konnten nur {len(spieler)} Spieler der Startelf verarbeitet werden.")

    result = {
        "logo": "",
        "team": own_team,
        "formation": str(formation or ""),
        "resultat": f"{own_goals}:{opp_goals}",
        "letzter_gegner": opponent,
        "gegner": opponent,
        "ausgang": ausgang,
        "spieler": spieler,
    }

    first_player_id = str(players[0].get("id")) if players[0].get("id") is not None else None
    last = _tm_api_last_match(first_player_id, match_id, own_id)
    if last:
        last_team, last_opponent, last_own, last_opp = last
        # Wenn nur IDs zurückkommen, bleibt der bereits bekannte Gegner stehen.
        if last_team and not str(last_team).isdigit():
            result["resultat"] = f"{last_own}:{last_opp}"
            result["gegner"] = last_opponent
            result["letzter_gegner"] = last_opponent
            result["ausgang"] = "Sieg" if last_own > last_opp else "Niederlage" if last_own < last_opp else "Unentschieden"

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

    # Nicht mehr auf die normale Transfermarkt-Seite zurückfallen: Render
    # erhält dort nachweislich nur die Human-Verification-Seite.
    raise ValueError(
        "Transfermarkt-Daten konnten über die JSON-API nicht geladen werden. "
        "Die HTML-Seite wird auf Render von Transfermarkt blockiert."
    )

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
