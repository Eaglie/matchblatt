from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re


def lade_transfermarkt(url, teamname=""):

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

            page.wait_for_timeout(3000)
            html = page.content()

        finally:
            # Nicht browser.close() verwenden:
            # Streamlit + Playwright kann sonst mit
            # "Event loop is closed!" abbrechen.
            pass

    soup = BeautifulSoup(html, "html.parser")

    heim_box = soup.select_one(".sb-team.sb-heim a.sb-club__link")
    gast_box = soup.select_one(".sb-team.sb-gast a.sb-club__link")

    heim_team = heim_box.get_text(strip=True) if heim_box else ""
    gast_team = gast_box.get_text(strip=True) if gast_box else ""

    is_heim = False

    if teamname and heim_team and teamname.lower() in heim_team.lower():
        is_heim = True

    if heim_box and gast_box:
        gegner = gast_team if is_heim else heim_team
    else:
        gegner = ""

        titel = soup.select_one("h1")

        if titel:
            titel_text = titel.get_text(" ", strip=True)
            match_paar = titel_text.split(",")[0]

            if " - " in match_paar:
                t1, t2 = [
                    x.strip()
                    for x in match_paar.split(" - ", 1)
                ]

                if teamname.lower() in t1.lower():
                    gegner = t2
                else:
                    gegner = t1

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

    eigenes_resultat = ""
    ausgang = ""

    if raw_resultat:
        h_tore, g_tore = map(
            int,
            raw_resultat.split(":")
        )

        if is_heim:
            eigenes_resultat = f"{h_tore}:{g_tore}"
            eigene = h_tore
            fremde = g_tore

        else:
            eigenes_resultat = f"{g_tore}:{h_tore}"
            eigene = g_tore
            fremde = h_tore

        if eigene > fremde:
            ausgang = "Sieg"

        elif eigene < fremde:
            ausgang = "Niederlage"

        else:
            ausgang = "Unentschieden"

    formation = ""

    text = soup.get_text("\n")

    m = re.search(
        r"Startaufstellung:\s*([0-9\- ]+)",
        text
    )

    if m:
        formation = m.group(1).strip()

    spieler = []

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

        containers = (
            alle[:11]
            if is_heim
            else alle[11:]
        )

    for div in containers:

        style = div.get("style", "")

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
                "nummer": nummer.get_text(strip=True),
                "name": name.get_text(" ", strip=True),
                "x": float(left.group(1)),
                "y": float(top.group(1)),
            }
        )

    eindeutig = []
    gesehen = set()

    for s in spieler:

        key = (
            s["name"],
            s["x"],
            s["y"],
        )

        if key in gesehen:
            continue

        gesehen.add(key)
        eindeutig.append(s)

    spieler = eindeutig[:11]

    return {
        "logo": "",
        "formation": formation,
        "resultat": eigenes_resultat,
        "letzter_gegner": gegner,
        "gegner": gegner,
        "ausgang": ausgang,
        "spieler": spieler,
    }
