import html
from pathlib import Path

from components.css import CSS
from components.pitch import pitch
from components.players import players
from components.absence import absence_table
from components.header import header
from components.match_info import match_info


# ============================================================
# MATCHBLATT – EXAKTES MAC-LAYOUT
#
# Ziel:
#   Kopfzeile
#   Team 1:
#       Spielfeld links | Absenzen rechts
#   Team 2:
#       Spielfeld links | Absenzen rechts
#
# Das Layout ist bewusst fest definiert und wird nicht mehr
# durch die alten Team-/Grid-Regeln aus components.css bestimmt.
# ============================================================


LAYOUT_CSS = r"""
<style>

* {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
}

body {
    background: #ffffff;
    font-family: Arial, Helvetica, sans-serif;
    color: #111;
}

/* Gesamte Matchblatt-Breite wie im Mac-PDF */
body > * {
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
}

/* ------------------------------------------------------------
   Hauptkopf
   ------------------------------------------------------------ */

.match-header {
    width: 800px;
    margin: 0 auto 14px auto;
    background: #173b78;
    color: #fff;
    border-radius: 10px 10px 0 0;
    text-align: center;
    padding: 8px 15px 7px 15px;
}

.match-header-title {
    font-size: 27px;
    line-height: 30px;
    font-weight: 700;
    margin: 0;
}

.match-header-subtitle {
    margin-top: 5px;
    font-size: 13px;
    line-height: 16px;
    color: rgba(255,255,255,.9);
}

/* ------------------------------------------------------------
   Teamkarte
   ------------------------------------------------------------ */

.team {
    width: 800px !important;
    margin: 0 auto 18px auto !important;
    padding: 0 !important;
    border: 1px solid #dfe5ec !important;
    border-radius: 10px !important;
    background: #fff !important;
    overflow: hidden !important;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
}

/* Team-Kopf exakt als dunkle Leiste */
.team_head {
    width: 100% !important;
    height: 48px !important;
    min-height: 48px !important;
    display: flex !important;
    align-items: center !important;
    background: #17233f !important;
    color: #fff !important;
    padding: 0 18px !important;
    border: 0 !important;
    border-radius: 9px 9px 0 0 !important;
    overflow: hidden !important;
}

.team_name {
    flex: 1 !important;
    padding: 0 !important;
    margin: 0 !important;
    background: transparent !important;
    color: #fff !important;
    font-size: 22px !important;
    line-height: 48px !important;
    font-weight: 700 !important;
    text-align: left !important;
}

.team_opponent {
    margin-left: auto !important;
    padding: 0 !important;
    background: transparent !important;
    color: rgba(255,255,255,.88) !important;
    font-size: 17px !important;
    line-height: 48px !important;
    font-weight: 400 !important;
    text-align: right !important;
    white-space: nowrap !important;
}

/* ------------------------------------------------------------
   DAS WICHTIGE LAYOUT:
   445 px Pitch | 33 px Abstand | 274 px Absenzen
   ------------------------------------------------------------ */

.team_body {
    width: 100% !important;
    display: grid !important;
    grid-template-columns: 445px 274px !important;
    column-gap: 33px !important;
    align-items: start !important;
    padding: 7px 20px 8px 20px !important;
    margin: 0 !important;
}

/* Beide bisherigen Wrapper werden neutralisiert */
.team_body > div:first-child,
.team_body > div:last-child {
    min-width: 0 !important;
    width: auto !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ------------------------------------------------------------
   Spielfeld
   ------------------------------------------------------------ */

.team_body .pitch {
    position: relative !important;
    width: 445px !important;
    height: 445px !important;
    min-width: 445px !important;
    max-width: 445px !important;
    min-height: 445px !important;
    max-height: 445px !important;

    margin: 0 !important;
    padding: 0 !important;

    border: 1px solid #d7dfe8 !important;
    border-radius: 8px !important;
    background: #fff !important;
    overflow: hidden !important;
}

/* Spielfeldlinien */
.team_body .pitch::before {
    content: "" !important;
    display: block !important;
    position: absolute !important;
    left: 0 !important;
    right: 0 !important;
    top: 0 !important;
    bottom: 0 !important;
    border: 0 !important;
    pointer-events: none !important;
}

.team_body .pitch .midline {
    position: absolute !important;
    left: 0 !important;
    right: 0 !important;
    top: 50% !important;
    border-top: 0 !important;
}

.team_body .pitch .centerdot {
    position: absolute !important;
    width: 5px !important;
    height: 5px !important;
    background: #222 !important;
    border-radius: 50% !important;
    left: 50% !important;
    top: 50% !important;
    transform: translate(-50%,-50%) !important;
}

.team_body .pitch .centercircle {
    position: absolute !important;
    width: 76px !important;
    height: 76px !important;
    border: 1.5px solid #444 !important;
    border-radius: 50% !important;
    left: 50% !important;
    top: 50% !important;
    transform: translate(-50%,-50%) !important;
}

.team_body .pitch .penalty_top {
    position: absolute !important;
    left: 20% !important;
    width: 60% !important;
    height: 52px !important;
    top: 0 !important;
    border: 1.5px solid #444 !important;
    border-top: none !important;
}

.team_body .pitch .penalty_bottom {
    position: absolute !important;
    left: 20% !important;
    width: 60% !important;
    height: 52px !important;
    bottom: 0 !important;
    border: 1.5px solid #444 !important;
    border-bottom: none !important;
}

.team_body .pitch .goalbox_top {
    position: absolute !important;
    left: 35% !important;
    width: 30% !important;
    height: 19px !important;
    top: 0 !important;
    border: 1.5px solid #444 !important;
    border-top: none !important;
}

.team_body .pitch .goalbox_bottom {
    position: absolute !important;
    left: 35% !important;
    width: 30% !important;
    height: 19px !important;
    bottom: 0 !important;
    border: 1.5px solid #444 !important;
    border-bottom: none !important;
}

.team_body .pitch .penalty_dot_top {
    position: absolute !important;
    width: 5px !important;
    height: 5px !important;
    background: #222 !important;
    border-radius: 50% !important;
    left: 50% !important;
    top: 105px !important;
    transform: translateX(-50%) !important;
}

.team_body .pitch .penalty_dot_bottom {
    position: absolute !important;
    width: 5px !important;
    height: 5px !important;
    background: #222 !important;
    border-radius: 50% !important;
    left: 50% !important;
    bottom: 105px !important;
    transform: translateX(-50%) !important;
}

/* ------------------------------------------------------------
   Spieler
   ------------------------------------------------------------ */

.team_body .pitch .player {
    position: absolute !important;
    transform: translate(-50%,-50%) !important;
    width: 72px !important;
    text-align: center !important;
    z-index: 5 !important;
}

.team_body .pitch .player_circle {
    width: 36px !important;
    height: 36px !important;
    margin: auto !important;
    border-radius: 50% !important;
    background: #111 !important;
    color: #fff !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    border: 0 !important;
    box-shadow: none !important;
}

.team_body .pitch .player_name {
    margin-top: 5px !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    line-height: 12px !important;
    color: #111 !important;
    white-space: nowrap !important;
}

.team_body .pitch .player_position {
    display: none !important;
}

/* ------------------------------------------------------------
   Absenzen – exakt rechts neben dem Spielfeld
   ------------------------------------------------------------ */

.team_body .absence,
.team_body .absence-table {
    width: 274px !important;
    max-width: 274px !important;
    border-collapse: collapse !important;
    margin: 0 !important;
    padding: 0 !important;
    table-layout: fixed !important;
}

.team_body .absence td,
.team_body .absence-table td {
    border: 1px solid #d9dee5 !important;
    padding: 7px 10px !important;
    height: 50px !important;
    font-size: 12px !important;
    line-height: 14px !important;
    vertical-align: top !important;
    color: #111 !important;
}

.team_body .absence td:first-child,
.team_body .absence-table td:first-child {
    width: 124px !important;
    background: #fafbfc !important;
    color: #555 !important;
    font-size: 14px !important;
    font-weight: 700 !important;
}

.team_body .absence td:last-child,
.team_body .absence-table td:last-child {
    width: 150px !important;
    background: #fff !important;
    font-size: 12px !important;
    font-weight: 700 !important;
}

/* Nicht im Aufgebot darf NICHT verschwinden */
.team_body .absence tr:last-child td {
    min-height: 50px !important;
}

/* Alles Alte, was die Darstellung wieder untereinander ziehen könnte */
.team_body .formation,
.team_body .team_information,
.team_body h3,
.team_body br {
    display: none !important;
}

/* ------------------------------------------------------------
   Match-Info wird vor den Teams kompakt gehalten
   ------------------------------------------------------------ */

.info {
    width: 800px !important;
    margin: 0 auto 14px auto !important;
    border-collapse: collapse !important;
}

.info td {
    border: 1px solid #d7d7d7 !important;
    padding: 6px 10px !important;
    font-size: 12px !important;
}

.info td:first-child {
    width: 180px !important;
    background: #f3f3f3 !important;
    font-weight: 700 !important;
}

/* Alte Seitenbegrenzungen dürfen das Matchblatt nicht verschieben */
.page {
    width: 800px !important;
    min-height: 0 !important;
    margin: 0 auto !important;
    padding: 0 !important;
    background: #fff !important;
    box-shadow: none !important;
}

/* Auf Desktop keine zweite Spalte/Umbruch */
.team,
.team_body,
.match-header,
.info {
    break-inside: avoid !important;
    page-break-inside: avoid !important;
}

</style>
"""


def draw_players(spieler):
    return players(spieler)


def draw_pitch(spieler):
    return pitch(draw_players(spieler))


def absence_table_html(absences):
    return absence_table(absences or {})


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

    spieler = []

    for s in daten.get("spieler", []):
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

    letzter_gegner = daten.get("letzter_gegner", "")
    resultat = daten.get("resultat", "")

    last_game = (
        f"Letztes Spiel: {teamname} "
        f"{resultat} {letzter_gegner}"
    ).strip()

    return f"""
<div class="team">

    <div class="team_head">
        <span class="team_name">
            {html.escape(str(teamname))}
        </span>

        <span class="team_opponent">
            {html.escape(last_game)}
        </span>
    </div>

    <div class="team_body">

        <div>
            {draw_pitch(spieler)}
        </div>

        <div>
            {absence_table_html(absenzen)}
        </div>

    </div>

</div>
"""


def _normalise_css(css):
    css = "" if css is None else str(css).strip()

    if css.lower().startswith("<style"):
        start = css.find(">")
        end = css.lower().rfind("</style>")

        if start != -1 and end != -1 and end > start:
            css = css[start + 1:end].strip()

    return f"<style>\n{css}\n</style>"


def erstelle_report(sfl, heim, gast):
    sfl = sfl or {}
    heim = heim or {}
    gast = gast or {}

    html_report = f"""<!DOCTYPE html>
<html lang="de">

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

{_normalise_css(CSS)}

{LAYOUT_CSS}
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

    Path("report.html").write_text(
        html_report,
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
            "fraglich": [],
            "nicht_im_aufgebot": []
        }
    }


if __name__ == "__main__":
    print("Dieses Modul wird von main.py aufgerufen.")
