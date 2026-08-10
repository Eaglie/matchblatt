from pathlib import Path

CSS = """
<style>

*{
    box-sizing:border-box;
}

body{
    margin:0;
    padding:0;
    background:#dcdcdc;
    font-family:Arial,Helvetica,sans-serif;
}

.page{
    width:210mm;
    min-height:297mm;
    margin:20px auto;
    background:white;
    padding:15mm;
    box-shadow:0 0 15px rgba(0,0,0,.15);
}

.header{
    background:#111;
    color:white;
    display:grid;
    grid-template-columns:90px 1fr 90px;
    align-items:center;
    padding:18px;
}

.logo{
    display:flex;
    justify-content:center;
    align-items:center;
}

.logo img{
    width:70px;
    height:70px;
    object-fit:contain;
}

.title{
    text-align:center;
}

.title h1{
    margin:0;
    font-size:30px;
}

.title h2{
    margin:8px 0 0;
    font-size:16px;
    font-weight:normal;
}

.info,
.absence,
.bench{
    width:100%;
    border-collapse:collapse;
    margin-bottom:18px;
}

.info td,
.absence td,
.bench td,
.bench th{
    border:1px solid #d7d7d7;
    padding:8px 10px;
    font-size:13px;
}

.info td:first-child,
.absence td:first-child{
    width:180px;
    background:#f3f3f3;
    font-weight:bold;
}

.bench th{
    background:#111;
    color:white;
    text-align:left;
}

.team{
    margin-top:25px;
    border:1px solid #d7d7d7;
}

.team_head{
    background:#111;
    color:white;
    display:grid;
    grid-template-columns:70px 1fr 90px;
    align-items:center;
    height:55px;
}

.team_logo{
    display:flex;
    justify-content:center;
    align-items:center;
}

.team_logo img{
    width:46px;
    height:46px;
    object-fit:contain;
}

.team_name{
    font-size:24px;
    font-weight:bold;
}

.team_result{
    text-align:center;
    font-size:24px;
    font-weight:bold;
}

.team_body{
    display:grid;
    grid-template-columns:90px 540px 1fr;
    gap:15px;
    padding:15px;
}

.formation{
    text-align:center;
}

.formation_label{
    color:#666;
    font-size:12px;
    margin-bottom:8px;
}

.formation_value{
    font-size:34px;
    font-weight:bold;
}

.pitch{
    position:relative;
    width:540px;
    height:760px;
    border:3px solid #222;
    background:white;
    overflow:hidden;
}

.pitch::before{
    content:"";
    position:absolute;
    left:10px;
    right:10px;
    top:10px;
    bottom:10px;
    border:2px solid #222;
}

.midline{
    position:absolute;
    left:10px;
    right:10px;
    top:50%;
    border-top:2px solid #222;
}

.centerdot{
    position:absolute;
    width:8px;
    height:8px;
    background:#222;
    border-radius:50%;
    left:50%;
    top:50%;
    transform:translate(-50%,-50%);
}

.centercircle{
    position:absolute;
    width:120px;
    height:120px;
    border:2px solid #222;
    border-radius:50%;
    left:50%;
    top:50%;
    transform:translate(-50%,-50%);
}

.penalty_top{
    position:absolute;
    left:22%;
    width:56%;
    height:120px;
    top:10px;
    border:2px solid #222;
    border-top:none;
}

.penalty_bottom{
    position:absolute;
    left:22%;
    width:56%;
    height:120px;
    bottom:10px;
    border:2px solid #222;
    border-bottom:none;
}

.goalbox_top{
    position:absolute;
    left:36%;
    width:28%;
    height:45px;
    top:10px;
    border:2px solid #222;
    border-top:none;
}

.goalbox_bottom{
    position:absolute;
    left:36%;
    width:28%;
    height:45px;
    bottom:10px;
    border:2px solid #222;
    border-bottom:none;
}

.penalty_dot_top{
    position:absolute;
    width:6px;
    height:6px;
    background:#222;
    border-radius:50%;
    left:50%;
    top:92px;
    transform:translateX(-50%);
}

.penalty_dot_bottom{
    position:absolute;
    width:6px;
    height:6px;
    background:#222;
    border-radius:50%;
    left:50%;
    bottom:92px;
    transform:translateX(-50%);
}

.player{
    position:absolute;
    transform:translate(-50%,-50%);
    width:82px;
    text-align:center;
}

.player_circle{
    width:36px;
    height:36px;
    margin:auto;
    border-radius:50%;
    background:#111;
    color:white;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:15px;
    font-weight:bold;
    border:2px solid white;
    box-shadow:0 3px 8px rgba(0,0,0,.25);
}

.player_name{
    margin-top:5px;
    font-size:11px;
    font-weight:bold;
    line-height:1.2;
}

.player_position{
    font-size:10px;
    color:#666;
    margin-top:2px;
}

</style>
"""
def draw_players(players):

    html = ""

    for p in players:

        nummer = p.get("nummer", "")
        name = p.get("name", "")
        position = p.get("position", "")

        x = p.get("x", 50)
        y = p.get("y", 50)

        html += f"""
<div class="player"
style="left:{x}%;top:{y}%">

    <div class="player_circle">
        {nummer}
    </div>

    <div class="player_name">
        {name}
    </div>

    <div class="player_position">
        {position}
    </div>

</div>
"""

    return html


def draw_pitch(players):

    return f"""

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

    {draw_players(players)}

</div>

"""


def absence_table(absences):

    return f"""

<table class="absence">

<tr>
<td>Gesperrt</td>
<td>{"<br>".join(absences.get("gesperrt", []))}</td>
</tr>

<tr>
<td>Verletzt</td>
<td>{"<br>".join(absences.get("verletzt", []))}</td>
</tr>

<tr>
<td>Krank</td>
<td>{"<br>".join(absences.get("krank", []))}</td>
</tr>

<tr>
<td>Fraglich</td>
<td>{"<br>".join(absences.get("fraglich", []))}</td>
</tr>

</table>

"""


def team_information(daten):

    trainer = daten.get("trainer", "")
    captain = daten.get("captain", "")
    tabellenplatz = daten.get("tabellenplatz", "")
    form = daten.get("form", "")
    tore = daten.get("tore", "")
    gegentore = daten.get("gegentore", "")
    xg = daten.get("xg", "")
    ballbesitz = daten.get("ballbesitz", "")

    return f"""

<table class="info">

<tr>
<td>Trainer</td>
<td>{trainer}</td>
</tr>

<tr>
<td>Captain</td>
<td>{captain}</td>
</tr>

<tr>
<td>Tabellenplatz</td>
<td>{tabellenplatz}</td>
</tr>

<tr>
<td>Form</td>
<td>{form}</td>
</tr>

<tr>
<td>Tore</td>
<td>{tore}</td>
</tr>

<tr>
<td>Gegentore</td>
<td>{gegentore}</td>
</tr>

<tr>
<td>xG</td>
<td>{xg}</td>
</tr>

<tr>
<td>Ballbesitz</td>
<td>{ballbesitz}</td>
</tr>

</table>

"""


def bench_table(bank):

    html = """

<h3>Ersatzbank</h3>

<table class="bench">

<tr>
<th>Nr.</th>
<th>Name</th>
<th>Pos.</th>
</tr>

"""

    for spieler in bank:

        html += f"""
<tr>
<td>{spieler.get("nummer","")}</td>
<td>{spieler.get("name","")}</td>
<td>{spieler.get("position","")}</td>
</tr>
"""

    html += """

</table>

"""

    return html
def team_block(teamname, daten):

    formation = daten.get("formation", "")
    resultat = daten.get("resultat", "")
    logo = daten.get("logo", "")

    absenzen = daten.get(
        "absenzen",
        {
            "gesperrt": [],
            "verletzt": [],
            "krank": [],
            "fraglich": [],
            "nicht_im_aufgebot": []
        }
    )

    spieler = daten.get("spieler", [])
    ersatzbank = daten.get("ersatzbank", [])

    return f"""

<div class="team">

    <div class="team_head">

        <div class="team_logo">
            <img src="{logo}">
        </div>

        <div class="team_name">
            {teamname}
        </div>

        <div class="team_result">
            {resultat}
        </div>

    </div>

    <div class="team_body">

        <div class="formation">

            <div class="formation_label">
                Formation
            </div>

            <div class="formation_value">
                {formation}
            </div>

        </div>

        {draw_pitch(spieler)}

        <div>

            {team_information(daten)}

            <br>

            <h3>Absenzen</h3>

            {absence_table(absenzen)}

        </div>

    </div>

    {bench_table(ersatzbank)}

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

<div class="header">

<div class="logo">
<img src="{heim.get('logo','')}">
</div>

<div class="title">

<h1>
{sfl.get("heim","")} – {sfl.get("gast","")}
</h1>

<h2>

{sfl.get("liga","")}

<br>

{sfl.get("datum","")} • {sfl.get("zeit","")}

</h2>

</div>

<div class="logo">
<img src="{gast.get('logo','')}">
</div>

</div>

<table class="info">

<tr>
<td>Stadion</td>
<td>{sfl.get("stadion","")}</td>
</tr>

<tr>
<td>Schiedsrichter</td>
<td>{sfl.get("schiedsrichter","")}</td>
</tr>

<tr>
<td>VAR</td>
<td>{sfl.get("var","")}</td>
</tr>

<tr>
<td>Runde</td>
<td>{sfl.get("runde","")}</td>
</tr>

<tr>
<td>Zuschauer</td>
<td>{sfl.get("zuschauer","")}</td>
</tr>

</table>

{team_block(sfl.get("heim",""), heim)}

<br><br>

{team_block(sfl.get("gast",""), gast)}
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
    
