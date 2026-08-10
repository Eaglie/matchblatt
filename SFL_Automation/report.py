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


def draw_pitch(spieler):
    return pitch(draw_players(spieler))


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
            try:
                return float(cleaned)
            except ValueError:
                return None
    return None


def adjust_left(val):
    n = parse_val(val)
    if n is None:
        return val
    return 50 + (n - 50) * 1.2 + 12


def adjust_top(val):
    n = parse_val(val)
    if n is None:
        return val
    return 50 + (n - 50) * 0.95 + 8


def team_block(teamname, daten, absenzen):
    daten = daten or {}
    absenzen = absenzen or {}

    raw_spieler = daten.get("spieler", [])
    spieler = []

    for s in raw_spieler:
        if not isinstance(s, dict):
            continue

        s_copy = s.copy()

        orig_left = s_copy.get(
            "_orig_left",
            s_copy.get("left", s_copy.get("x"))
        )
        orig_top = s_copy.get(
            "_orig_top",
            s_copy.get("top", s_copy.get("y"))
        )

        s_copy["_orig_left"] = orig_left
        s_copy["_orig_top"] = orig_top
        s_copy["left"] = adjust_left(orig_left)
        s_copy["top"] = adjust_top(orig_top)

        spieler.append(s_copy)

    return f"""
<div class="team_block">
    <div class="team_content">
        <div class="team_pitch">
            {draw_pitch(spieler)}
        </div>
        <div class="team_absence">
            {absence_table_html(absenzen)}
        </div>
    </div>
</div>
"""


def _normalise_css(css):
    """
    CSS darf aus components.css entweder als reiner CSS-Text
    oder bereits als <style>...</style> kommen.
    Am Ende wird immer genau EIN style-Block erzeugt.
    """
    css = "" if css is None else str(css).strip()

    lower = css.lower()

    if lower.startswith("<style"):
        start = css.find(">")
        end = lower.rfind("</style>")

        if start != -1 and end != -1 and end > start:
            css = css[start + 1:end].strip()

    return "<style>\n" + css + "\n</style>"


def erstelle_report(sfl, heim, gast):
    sfl = sfl or {}
    heim = heim or {}
    gast = gast or {}

    css_block = _normalise_css(CSS)

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{css_block}
</head>
<body>

{header(
    heim.get("logo", ""),
    gast.get("logo", ""),
    sfl.get("heim", ""),
    sfl.get("gast", ""),
    sfl.get("liga", ""),
    sfl.get("stadion", ""),
    sfl.get("datum", ""),
    sfl.get("zeit", ""),
    sfl.get("schiedsrichter", ""),
    sfl.get("var", "")
)}

{match_info(sfl)}

{team_block(
    sfl.get("heim", ""),
    heim,
    sfl.get("heim_abwesend", heim.get("absenzen", {}))
)}

{team_block(
    sfl.get("gast", ""),
    gast,
    sfl.get("gast_abwesend", gast.get("absenzen", {}))
)}

</body>
</html>
"""

    Path("report.html").write_text(html, encoding="utf-8")
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
            "fraglich": [],
            "nicht_im_aufgebot": []
        }
    }


if __name__ == "__main__":
    print("Dieses Modul wird von main.py aufgerufen.")
