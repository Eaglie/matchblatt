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
    """
    Erzeugt die Absenzen-Tabelle über die bestehende Komponente.

    Die bestehende Komponente kennt vier Kategorien.
    'Nicht im Aufgebot' wird hier ergänzt, damit diese Kategorie
    im Matchblatt nicht mehr verloren geht.
    """
    absences = absences or {}

    html = absence_table(absences)

    nicht_im_aufgebot = absences.get(
        "nicht_im_aufgebot",
        absences.get("nicht im aufgebot", [])
    )

    if nicht_im_aufgebot:
        namen = "<br>".join(
            str(name)
            for name in nicht_im_aufgebot
        )
    else:
        namen = ""

    row = f"""
    <tr>
        <td>Nicht im Aufgebot</td>
        <td>{namen}</td>
    </tr>
    """

    if "</table>" in html:
        html = html.replace(
            "</table>",
            row + "</table>",
            1
        )
    else:
        html += f"""
        <table class="absence">
            {row}
        </table>
        """

    return html


def parse_val(val):
    if val is None:
        return None

    if isinstance(val, (int, float)):
        return float(val)

    if isinstance(val, str):
        cleaned = "".join(
            c
            for c in val
            if c.isdigit() or c in ".-"
        )

        if cleaned:
            return float(cleaned)

    return None


def adjust_left(val):
    n = parse_val(val)

    if n is None:
        return val

    # Bestehende horizontale Anpassung beibehalten.
    return 50 + (n - 50) * 1.2 + 12


def adjust_top(val):
    n = parse_val(val)

    if n is None:
        return val

    # Bestehende vertikale Anpassung beibehalten.
    return 50 + (n - 50) * 0.95 + 8


def team_block(teamname, daten, absenzen, is_guest=False):
    """
    Baut genau einen Teamblock.

    Die Spielerkoordinaten werden nur hier angepasst.
    Die Originalwerte bleiben erhalten.
    """

    daten = daten or {}
    absenzen = absenzen or {}

    resultat = daten.get(
        "resultat",
        ""
    )

    logo = daten.get(
        "logo",
        ""
    )

    formation = daten.get(
        "formation",
        ""
    )

    raw_spieler = daten.get(
        "spieler",
        []
    )

    spieler = []

    for s in raw_spieler:

        if not isinstance(s, dict):
            continue

        s_copy = s.copy()

        orig_left = s_copy.get(
            "_orig_left",
            s_copy.get(
                "left",
                s_copy.get("x")
            )
        )

        orig_top = s_copy.get(
            "_orig_top",
            s_copy.get(
                "top",
                s_copy.get("y")
            )
        )

        s_copy["_orig_left"] = orig_left
        s_copy["_orig_top"] = orig_top

        s_copy["left"] = adjust_left(
            orig_left
        )

        s_copy["top"] = adjust_top(
            orig_top
        )

        spieler.append(
            s_copy
        )

    pitch_html = draw_pitch(
        spieler
    )

    absence_html = absence_table_html(
        absenzen
    )

    return f"""
    <div class="team">

        {scorebar(
            logo,
            teamname,
            resultat
        )}

        <div class="team_body">

            <div class="formation">
                <div class="formation_label">
                    Formation
                </div>

                <div class="formation_value">
                    {formation}
                </div>
            </div>

            {pitch_html}

            <div class="absence-container">
                {absence_html}
            </div>

        </div>

    </div>
    """


def erstelle_report(sfl, heim, gast):

    html = f"""
<!DOCTYPE html>

<html lang="de">

<head>

<meta charset="utf-8">

<title>
{sfl.get("heim", "")} -
{sfl.get("gast", "")}
</title>

{CSS}

</head>

<body>

<div class="page">

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
        sfl.get(
            "heim_abwesend",
            {}
        ),
        is_guest=False
    )}

    {team_block(
        sfl.get("gast", ""),
        gast,
        sfl.get(
            "gast_abwesend",
            {}
        ),
        is_guest=True
    )}

</div>

</body>

</html>
"""

    Path(
        "report.html"
    ).write_text(
        html,
        encoding="utf-8"
    )

    print(
        "✓ report.html erstellt"
    )

    return html


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
    print(
        "Dieses Modul wird von main.py aufgerufen."
    )
