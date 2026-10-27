from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import unicodedata
from datetime import datetime
import requests
from urllib.parse import quote
import time


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

    # 3. Vereinslinks der Spielseite
    if not heim_team or not gast_team:
        team_links = []

        for a in soup.select('a[href*="/startseite/verein/"]'):
            text = a.get_text(" ", strip=True)

            if not text:
                continue

            if text not in team_links:
                team_links.append(text)

        if team_links:
            own_index = None

            for i, text in enumerate(team_links):
                if _team_match(teamname, text):
                    own_index = i
                    break

            if own_index is not None:
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

    # 4. Breiter Fallback über sichtbare Überschriften
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

    # 5. Letzter Rohtext-Fallback
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


def _extract_score(soup):
    """
    Holt das Endresultat.
    """
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
        raise ValueError(
            "Transfermarkt: Endresultat "
            "konnte nicht eindeutig gefunden werden."
        )

    return tuple(map(int, raw_resultat.split(":")))


def _extract_formation(soup):
    text = soup.get_text("\n")
    match = re.search(
        r"Startaufstellung:\s*([0-9\- ]+)",
        text
    )

    if match:
        return match.group(1).strip()

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
        style = div.get("style", "")
        top = re.search(r"top:\s*([\d.]+)%", style)
        left = re.search(r"left:\s*([\d.]+)%", style)
        nummer = div.select_one(".tm-shirt-number")
        name = div.select_one(".formation-number-name")

        if (
            not top
            or not left
            or not nummer
            or not name
        ):
            continue

        spieler.append(
            {
                "nummer": nummer.get_text(strip=True),
                "name": name.get_text(" ", strip=True),
                "x": float(left.group(1)),
                "y": float(top.group(1)),
            }
        )

    eindeutig = []
    gesehen = set()

    for s in spieler:
        key = (s["name"], s["x"], s["y"])
        if key in gesehen:
            continue
        gesehen.add(key)
        eindeutig.append(s)

    spieler = eindeutig

    if len(spieler) != 11:
        raise ValueError(
            "Transfermarkt: Für "
            f"'{teamname}' wurden nicht exakt "
            f"11 Startspieler gefunden "
            f"(gefunden: {len(spieler)})."
        )

    return spieler


def _matching_team_link(soup, teamname):
    for a in soup.select('a[href]'):
        href = a.get("href", "").strip()
        text = a.get_text(" ", strip=True)
        title = a.get("title", "").strip()
        if "/startseite/verein/" not in href:
            continue
        if _team_match(teamname, text) or _team_match(teamname, title):
            return href
    return ""


def _team_schedule_url_from_link(href, season=""):
    m = re.search(r"/([^/]+)/startseite/verein/(\d+)", href or "")
    if not m:
        return ""
    slug, verein_id = m.group(1), m.group(2)
    if season:
        return (
            f"https://www.transfermarkt.ch/{slug}/spielplan/verein/"
            f"{verein_id}/saison_id/{season}/plus/1"
        )
    return f"https://www.transfermarkt.ch/{slug}/spielplan/verein/{verein_id}/plus/1"


def _extract_last_match_from_schedule(
    soup,
    teamname,
    current_url
):
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
    url_id_match = re.search(r"/verein/(\d+)", current_url or "")
    url_verein_id = url_id_match.group(1) if url_id_match else ""

    for a in soup.select("a[href]"):
        href = a.get("href", "")
        text = a.get_text(" ", strip=True)

        if "/startseite/verein/" not in href:
            continue

        if _team_match(teamname, text):
            team_link = href
            break

    if team_link:
        id_match = re.search(
            r"/startseite/verein/(\d+)",
            team_link
        )
        verein_id = id_match.group(1) if id_match else url_verein_id

        slug_match = re.search(
            r"/([^/]+)/startseite/verein/",
            team_link
        )
        slug = slug_match.group(1) if slug_match else ""
    else:
        verein_id = url_verein_id
        slug_match = re.search(
            r"https?://[^/]+/([^/]+)/(?:spielplan|spielplandatum|startseite)/",
            current_url or ""
        )
        slug = slug_match.group(1) if slug_match else ""

    if not verein_id:
        return None

    season_match = re.search(
        r"saison_id/(\d{4})",
        current_url or ""
    )
    saison = (
        season_match.group(1)
        if season_match
        else str(datetime.now().year)
    )

    schedule_url = (
        "https://www.transfermarkt.ch/"
        f"{slug}/spielplan/verein/{verein_id}/"
        f"saison_id/{saison}/plus/1"
    ) if slug else (
        "https://www.transfermarkt.ch/"
        f"spielplan/verein/{verein_id}/saison_id/{saison}/plus/1"
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
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

    for row in schedule_soup.select("tr"):
        row_text = row.get_text(" ", strip=True)
        if not row_text:
            continue

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

                if b >= 60:
                    continue

                if a <= 20 and b <= 20:
                    score_text = f"{a}:{b}"

            if score_text:
                break

        if not score_text:
            continue

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

        report_url = ""
        for a_link in row.select('a[href*="/spielbericht/"]'):
            href = a_link.get("href", "").strip()
            if href:
                if href.startswith("http"):
                    report_url = href
                else:
                    host_match = re.match(r"(https?://[^/]+)", current_url or "")
                    host = host_match.group(1) if host_match else "https://www.transfermarkt.ch"
                    report_url = host + (href if href.startswith("/") else "/" + href)
                break

        kandidaten.append({
            "datum": match_date,
            "resultat": eigenes,
            "gegner": opponent,
            "ausgang": ausgang,
            "report_url": report_url,
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
    global _TM_LAST_API_CALL
    now = time.monotonic()
    wait = 1.65 - (now - _TM_LAST_API_CALL)
    if wait > 0:
        time.sleep(wait)
    _TM_LAST_API_CALL = time.monotonic()


def _tm_api_get(path, timeout=20):
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

        left = _tm_player_value(
            player, "styleLeft", "style_left", "left", "x"
        )
        top = _tm_player_value(
            player, "styleTop", "style_top", "top", "y"
        )

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
            name = _tm_player_value(
                player, "name", "playerName", "fullName"
            )
            number = _tm_player_value(
                player, "shirtNumber", "shirt_number", "number", "jerseyNumber"
            )
            left = float(_tm_player_value(
                player, "styleLeft", "style_left", "left", "x"
            ))
            top = float(_tm_player_value(
                player, "styleTop", "style_top", "top", "y"
            ))

            if name:
                result.append({
                    "nummer": str(number) if number is not None else "",
                    "name": str(name).strip(),
                    "x": left,
                    "y": top,
                })

        return result

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
            name = _tm_player_value(player, "name", "
