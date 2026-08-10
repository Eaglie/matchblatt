from pathlib import Path
from components.css import CSS
from components.scorebar import scorebar
from components.pitch import pitch
from components.players import players
from components.absence import absence_table
from components.header import header
from components.match_info import match_info


def draw_players(spieler):
    return players(spieler)


def draw_pitch(players):
    return pitch(draw_players(players))


def absence_table_html(absences):
    return absence_table(absences)


def parse_val(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = "".join(c for c in val if c.isdigit() or c in ".-")
        if cleaned:
            return float(cleaned)
    return None


def adjust_left(val):
    n = parse_val(val)
    if n is None:
        return val

    # Horizontal leicht nach rechts verschieben
    return 50 + (n - 50) * 01.2 + 12


def adjust_top(val):
    n = parse_val(val)
    if n is None:
        return val

    # Vertikal etwas nach unten verschieben
    return 50 + (n - 50) * 0.95 + 8


def team_block(teamname, daten, absenzen):
    resultat = daten.get("resultat", "")
    logo = daten.get("logo", "")

    raw_spieler = daten.get("spieler", [])
    spieler = []

    for s in raw_spieler:
        if isinstance(s, dict):
            s_copy = s.copy()
            orig_left = s_copy.get("_orig_left", s_copy.get("left", s_copy.get("x")))
            orig_top = s_copy.get("_orig_top", s_copy.get("top", s_copy.get("y")))

            s_copy["_orig_left"] = orig_left
            s_copy["_orig_top"] = orig_top

            s_copy["left"] = adjust_left(orig_left)
            s_copy["top"] = adjust_top(orig_top)
            spieler.append(s_copy)

    return f"""
<div class="team">
{scorebar(
    teamname,
    logo,
    resultat,
    daten.get("letzter_gegner", "")
)}

<div class="team_body">

    <div style="display:flex; flex-direction:column;">
        {draw_pitch(spieler)}
    </div>

    <div style="display:flex; flex-direction:column;">


    {absence_table_html(absenzen)}

</div>

</div>
"""


def erstelle_report(sfl, heim, gast):
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{sfl.get("heim","")} - {sfl.get("gast","")}</title>
{CSS}
</head>
<body>

<div class="page">

{header(
    heim.get("logo",""),
    gast.get("logo",""),
    sfl.get("heim",""),
    sfl.get("gast",""),
    sfl.get("liga",""),
    sfl.get("stadion",""),
    sfl.get("datum",""),
    sfl.get("zeit",""),
    sfl.get("schiedsrichter",""),
    sfl.get("var","")
)}

{match_info(sfl)}

{team_block(
    sfl.get("heim",""),
    heim,
    sfl.get("heim_abwesend", {})
)}

<div style="height:2px;"></div>

{team_block(
    sfl.get("gast",""),
    gast,
    sfl.get("gast_abwesend", {})
)}

</div>

</body>
</html>
"""

    Path("report.html").write_text(
        html,
        encoding="utf-8"
    )

    print("✓ report.html erstellt")


def report_vorlage():
    return {
        "heim": "",
        "gast": "",
        "liga": "",
        "datum": "",
        "zeit": "",
        "stadion": "",
        "schiedsrichter": "",
        "var": "",
        "runde": "",
        "zuschauer": ""
    }


def team_vorlage():
    return {
        "logo": "",
        "formation": "",
        "resultat": "",
        "letzter_gegner": "",
        "trainer": "",
        "captain": "",
        "tabellenplatz": "",
        "form": "",
        "tore": "",
        "gegentore": "",
        "xg": "",
        "ballbesitz": "",
        "spieler": [],
        "ersatzbank": [],
        "absenzen": {
            "gesperrt": [],
            "verletzt": [],
            "krank": [],
            "fraglich": []
        }
    }


if __name__ == "__main__":
    print("Dieses Modul wird von main.py aufgerufen.")
