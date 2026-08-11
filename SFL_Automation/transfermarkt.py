from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import unicodedata
from datetime import datetime
from urllib.parse import urljoin


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
    """

    heim_team = ""
    gast_team = ""

    # 1. Direkte Transfermarkt-Struktur
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
        heim_team = heim_box.get_text(
            " ",
            strip=True
        )

    if gast_box:
        gast_team = gast_box.get_text(
            " ",
            strip=True
        )

    # 2. Hauptüberschrift / Seitentitel
    titel_quellen = []

    h1 = soup.select_one("h1")

    if h1:
        titel_quellen.append(
            h1.get_text(
                " ",
                strip=True
            )
        )

    if soup.title:
        titel_quellen.append(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

    meta_title = soup.select_one(
        'meta[property="og:title"]'
    )

    if (
        meta_title
        and meta_title.get("content")
    ):
        titel_quellen.append(
            meta_title["content"].strip()
        )

    for titel_text in titel_quellen:

        if not titel_text:
            continue

        match_paar = titel_text.split(
            ",",
            1
        )[0].strip()

        if " - " not in match_paar:
            continue

        t1, t2 = [
            x.strip()
            for x in match_paar.split(
                " - ",
                1
            )
        ]

        if (
            t1
            and t2
            and _team_match(
                teamname,
                t1
            )
        ):
            heim_team = t1
            gast_team = t2
            break

        if (
            t1
            and t2
            and _team_match(
                teamname,
                t2
            )
        ):
            heim_team = t1
            gast_team = t2
            break

    # 3. Breiter Fallback über sichtbare Überschriften
    kandidaten = []

    if not heim_team or not gast_team:

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

            if not text:
                continue

            kandidaten.append(text)

            if " - " not in text:
                continue

            paar = text.split(
                ",",
                1
            )[0].strip()

            if " - " not in paar:
                continue

            t1, t2 = [
                x.strip()
                for x in paar.split(
                    " - ",
                    1
                )
            ]

            if (
                t1
                and t2
                and _team_match(
                    teamname,
                    t1
                )
            ):
                heim_team = t1
                gast_team = t2
                break

            if (
                t1
                and t2
                and _team_match(
                    teamname,
                    t2
                )
            ):
                heim_team = t1
                gast_team = t2
                break

    # 4. Letzter Rohtext-Fallback
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

    if not heim_team or not gast_team:
        raise ValueError(
            "Transfermarkt: Heim- und Gastteam "
            "konnten nicht eindeutig gefunden werden."
        )

    if _team_match(
        heim_team,
        gast_team
    ):
        raise ValueError(
            "Transfermarkt: Heimteam und Gastteam "
            "sind identisch."
        )

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

    Wichtig: Das Resultat wird aus den Ergebnis-Zellen gelesen,
    niemals aus dem gesamten Zeilentext, weil dort auch die Uhrzeit
    im Format 16:30 stehen kann.
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

        # Das aktuell eingegebene Spiel niemals als letztes Spiel verwenden.
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

        # Die beiden Vereinslinks liefern Heim- und Gastteam zuverlässig.
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

        # Resultat ausschließlich aus den Tabellenzellen lesen.
        # So wird z.B. 16:30 nicht mit einem Spielresultat verwechselt.
        score_candidates = []
        cells = row.select("td")

        for cell in cells:
            cell_text = cell.get_text(" ", strip=True)

            if cell_text in ("-:-", "–:–", "—:—", ""):
                continue

            matches = re.findall(
                r"(?<!\d)(\d{1,2}:\d{1,2})(?!\d)",
                cell_text
            )
            score_candidates.extend(matches)

        if not score_candidates:
            continue

        score_text = score_candidates[-1]

        try:
            a, b = map(
                int,
                score_text.split(":")
            )
        except ValueError:
            continue

        # H = eigenes Team zuhause, A = eigenes Team auswärts.
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

            except Exception:
                pass

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
        if navigation_error is not None:
            raise ValueError(
                "Transfermarkt-Seite konnte nicht geladen werden: "
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

    # ---------------------------------------------------------
    # LETZTES SPIEL
    # ---------------------------------------------------------
    # Die Startaufstellung kommt weiterhin aus der eingegebenen
    # Transfermarkt-Spielseite. Für "Letztes Spiel" darf diese
    # Seite aber nicht verwendet werden, weil sie das aktuelle
    # Spiel bzw. die aktuelle Begegnung beschreibt.
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
