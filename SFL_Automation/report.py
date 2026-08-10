from pathlib import Path
import html
import re

CSS = r'''<style>
*{box-sizing:border-box;}
body{margin:0;padding:0;background:white;font-family:Arial,Helvetica,sans-serif;}
.page{width:210mm;min-height:297mm;margin:10mm auto;background:white;padding:10mm 15mm;box-shadow:0 0 15px rgba(0,0,0,.15);}
.header{background:#0b2f6b;color:white;display:flex;justify-content:center;align-items:center;padding:5px 20px;border:1px solid #0b2f6b;border-radius:10px 10px 0 0;overflow:hidden;}
.title{text-align:center;}
.title h1{margin:0;font-size:24px;font-weight:700;letter-spacing:.5px;color:#fff;}
.title h2{margin:8px 0 0;font-size:13px;font-weight:400;color:rgba(255,255,255,.78);}
.header_label{color:#fff;font-weight:600;}
.header_value{color:#fff;}
.info{width:100%;border-collapse:collapse;margin-bottom:4px;font-size:13px;}
.info td{border:1px solid #d7d7d7;padding:8px 12px;}
.info td:first-child{width:200px;background:#f3f3f3;font-weight:bold;}
.absence{width:100%;border-collapse:collapse;margin:0;font-size:15px;}
.absence td{border:1px solid #d9dee5;padding:6px 10px;height:30px;font-size:11px;font-weight:700;line-height:1.25;color:#111;vertical-align:top;}
.absence td:first-child{width:105px;background:#fafbfc;color:#555;font-size:13px;font-weight:600;}
.absence td:nth-child(2){white-space:normal;overflow-wrap:anywhere;word-break:normal;}
.absence_name{display:block;white-space:normal;line-height:1.25;}
.team{margin-top:12px;border:1px solid #dfe5ec;border-radius:10px;overflow:hidden;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.06);}
.team_head{display:flex;align-items:center;width:100%;background:#17233f;border-radius:10px 10px 0 0;overflow:hidden;margin-bottom:0;white-space:nowrap;font-family:Arial,Helvetica,sans-serif;}
.team_name{flex:1;background:#17233f;color:#fff;padding:10px 16px;font-size:18px;font-weight:700;text-align:left;}
.team_opponent{background:#17233f;color:rgba(255,255,255,.85);padding:10px 16px;font-size:16px;font-weight:400;text-align:right;margin-left:auto;}
.team_body{display:grid;grid-template-columns:380px 1fr;gap:28px;padding:6px 18px 4px 18px;align-items:start;}
.pitch{position:relative;width:380px;height:380px;border:1px solid #d7dfe8;border-radius:8px;background:#fff;overflow:hidden;}
.midline{position:absolute;left:0;right:0;top:50%;border-top:2px solid rgba(255,255,255,.85);}
.centerdot{position:absolute;width:6px;height:6px;background:#fff;border-radius:50%;left:50%;top:50%;transform:translate(-50%,-50%);}
.centercircle{position:absolute;width:74px;height:74px;border:1.5px solid #444;border-radius:50%;left:50%;top:50%;transform:translate(-50%,-50%);}
.penalty_top{position:absolute;left:20%;width:60%;height:44px;top:0;border:1.5px solid #444;border-top:none;}
.penalty_bottom{position:absolute;left:20%;width:60%;height:44px;bottom:0;border:1.5px solid #444;border-bottom:none;}
.goalbox_top{position:absolute;left:35%;width:30%;height:16px;top:0;border:1.5px solid #444;border-top:none;}
.goalbox_bottom{position:absolute;left:35%;width:30%;height:16px;bottom:0;border:1.5px solid #444;border-bottom:none;}
.penalty_dot_top{position:absolute;width:3px;height:3px;background:#222;border-radius:50%;left:50%;top:32px;transform:translateX(-50%);}
.penalty_dot_bottom{position:absolute;width:3px;height:3px;background:#222;border-radius:50%;left:50%;bottom:32px;transform:translateX(-50%);}
.corner_top_left{position:absolute;top:-8px;left:-8px;width:16px;height:16px;border:1.5px solid #444;border-radius:50%;}
.corner_top_right{position:absolute;top:-8px;right:-8px;width:16px;height:16px;border:1.5px solid #444;border-radius:50%;}
.corner_bottom_left{position:absolute;bottom:-8px;left:-8px;width:16px;height:16px;border:1.5px solid #444;border-radius:50%;}
.corner_bottom_right{position:absolute;bottom:-8px;right:-8px;width:16px;height:16px;border:1.5px solid #444;border-radius:50%;}
.player{position:absolute;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;z-index:2;}
.player_number{font-size:12px;font-weight:700;line-height:1;color:#111;}
.player_name{margin-top:2px;padding:0;font-size:11px;font-weight:700;line-height:1.1;color:#111;text-align:center;white-space:nowrap;}
.player_position{display:none;}
html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
</style>'''


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


def draw_players(spieler):
    html_parts = []
    for p in spieler or []:
        if not isinstance(p, dict):
            continue
        nummer = p.get("nummer", p.get("number", ""))
        name = p.get("name", p.get("spieler", ""))
        left = p.get("left", p.get("x", 50))
        top = p.get("top", p.get("y", 50))
        html_parts.append(f'''
<div class="player" style="left:{html.escape(str(left))}%;top:{html.escape(str(top))}%">
    <div class="player_number">{html.escape(str(nummer))}</div>
    <div class="player_name">{html.escape(str(name))}</div>
    <div class="player_position"></div>
</div>''')
    return "".join(html_parts)


def draw_pitch(spieler):
    return f'''
<div class="pitch">
    <div class="midline"></div>
    <div class="centerdot"></div>
    <div class="centercircle"></div>
    <div class="penalty_top"></div>
    <div class="goalbox_top"></div>
    <div class="penalty_bottom"></div>
    <div class="goalbox_bottom"></div>
    <div class="penalty_dot_top"></div>
    <div class="penalty_dot_bottom"></div>
    {draw_players(spieler)}
</div>'''


def absence_table_html(absences):
    absences = absences or {}

    def values(*keys):
        found = []
        for key in keys:
            value = absences.get(key, [])
            if isinstance(value, str):
                if value.strip():
                    found.append(value.strip())
            elif isinstance(value, (list, tuple)):
                found.extend(str(x) for x in value if str(x).strip())

        # Nur Darstellung der Absenzen:
        # Wenn mehrere Namen als ein zusammengeklebter String ankommen,
        # werden sie vor der HTML-Ausgabe wieder getrennt.
        names = []
        for value in found:
            parts = re.split(
                r"(?<=[a-zäöüà-ÿ])(?=[A-ZÄÖÜÀ-Ý])",
                value
            )
            names.extend(
                part.strip()
                for part in parts
                if part.strip()
            )

        # Jeden Namen als eigenes Block-Element ausgeben.
        # Damit bleibt die Zeilentrennung auch in Streamlit garantiert erhalten.
        return "".join(
            f'<div class="absence_name">{html.escape(x)}</div>'
            for x in names
        )

    return f'''
<table class="absence">
<tr><td>Gesperrt</td><td>{values("gesperrt")}</td></tr>
<tr><td>Verletzt</td><td>{values("verletzt")}</td></tr>
<tr><td>Krank</td><td>{values("krank")}</td></tr>
<tr><td>Fraglich</td><td>{values("fraglich")}</td></tr>
<tr><td>Nicht im Aufgebot</td><td>{values("nicht_im_aufgebot", "nicht_im_kader", "nicht_im_aufgebot_namen")}</td></tr>
</table>'''


def team_block(teamname, daten, absenzen):
    daten = daten or {}
    raw_spieler = daten.get("spieler", [])
    spieler = []

    for s in raw_spieler:
        if not isinstance(s, dict):
            continue
        s_copy = s.copy()
        orig_left = s_copy.get("_orig_left", s_copy.get("left", s_copy.get("x")))
        orig_top = s_copy.get("_orig_top", s_copy.get("top", s_copy.get("y")))
        s_copy["_orig_left"] = orig_left
        s_copy["_orig_top"] = orig_top
        s_copy["left"] = adjust_left(orig_left)
        s_copy["top"] = adjust_top(orig_top)
        spieler.append(s_copy)

    letzter_gegner = daten.get("letzter_gegner", "")
    resultat = daten.get("resultat", "")

    last_game = f"Letztes Spiel: {teamname} {resultat} {letzter_gegner}".strip()

    return f'''
<div class="team">
    <div class="team_head">
        <span class="team_name">{html.escape(str(teamname))}</span>
        <span class="team_opponent">{html.escape(last_game)}</span>
    </div>
    <div class="team_body">
        <div style="display:flex; flex-direction:column;">
            {draw_pitch(spieler)}
        </div>
        <div style="display:flex; flex-direction:column;">
            {absence_table_html(absenzen)}
        </div>
    </div>
</div>'''


def erstelle_report(sfl, heim, gast):
    sfl = sfl or {}
    heim = heim or {}
    gast = gast or {}

    heim_name = sfl.get("heim", "")
    gast_name = sfl.get("gast", "")

    header = f'''
<div class="header">
    <div class="title">
        <h1>{html.escape(str(heim_name))} – {html.escape(str(gast_name))}</h1>
        <h2>
            {html.escape(str(sfl.get("stadion", "")))}
            • <span class="header_label">Schiedsrichter:</span>
            <span class="header_value">{html.escape(str(sfl.get("schiedsrichter", "")))}</span>
            • <span class="header_label">VAR:</span>
            <span class="header_value">{html.escape(str(sfl.get("var", "")))}</span>
        </h2>
    </div>
</div>'''

    html_document = f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{html.escape(str(heim_name))} - {html.escape(str(gast_name))}</title>
{CSS}
</head>
<body>
<div class="page">
{header}

{team_block(
    heim_name,
    heim,
    sfl.get("heim_abwesend", heim.get("absenzen", {}))
)}

<div style="height:2px;"></div>

{team_block(
    gast_name,
    gast,
    sfl.get("gast_abwesend", gast.get("absenzen", {}))
)}
</div>
</body>
</html>'''

    Path("report.html").write_text(html_document, encoding="utf-8")
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
        "zuschauer": "",
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
            "nicht_im_aufgebot": [],
        },
    }


if __name__ == "__main__":
    print("Dieses Modul wird von main.py aufgerufen.")
