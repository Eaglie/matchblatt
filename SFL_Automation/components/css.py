CSS = """
*{
box-sizing: border-box;
}

body{
margin: 0;
padding: 0;
background: white;
font-family: Arial, Helvetica, sans-serif;
}

.page{
width: 210mm;
min-height: 297mm;
margin: 10mm auto;
background: white;
padding: 10mm 15mm;
box-shadow: 0 0 15px rgba(0,0,0,.15);
}

.header{
background: #0b2f6b;
color: white;
display: flex;
justify-content: center;
align-items: center;
padding: 5px 20px;
border: 1px solid #0b2f6b;
border-radius: 10px 10px 0 0;
overflow: hidden;
}

.logo{
display:none;
}

.title{
text-align: center;
}

.title h1{
margin: 0;
font-size: 24px;
font-weight: 700;
letter-spacing: 0.5px;
color: #fff;
}

.title h2{
margin: 8px 0 0;
font-size: 13px;
font-weight: 400;
color: rgba(255,255,255,.78);
}

.header_label{
color: #ffffff;
font-weight: 600;
}

.header_value{
color: #6EC6FF;
}

.header_label + *{
color: #6EC6FF;
}

.title h3{
margin: 2px 0 0;
font-size: 18px;
font-weight: 600;
color: white;
}

.info{
width: 100%;
border-collapse: collapse;
margin-bottom: 4px;
font-size: 13px;
}

.info td{
border: 1px solid #d7d7d7;
padding: 8px 12px;
}

.info td:first-child{
width: 200px;
background: #f3f3f3;
font-weight: bold;
}

.absence{
width: 100%;
border-collapse: collapse;
margin: 0;
font-size: 15px;
}

.absence td{
border: 1px solid #d9dee5;
padding: 6px 10px;
height: 30px;
font-size: 11px;
font-weight: 700;
line-height: 1.25;
color: #111;
vertical-align: top;

/* EINZIGE ÄNDERUNG: vorhandene Zeilenumbrüche beibehalten */
white-space: pre-line;
}

.absence td:first-child{
width: 105px;
background: #fafbfc;
color: #555;
font-size: 13px;
font-weight: 600;
}

.team{
margin-top: 12px;
border: 1px solid #dfe5ec;
border-radius: 10px;
overflow: hidden;
background: #fff;
box-shadow: 0 2px 8px rgba(0,0,0,.06);
}

.team_head{
display: flex;
align-items: center;
width: 100%;
background: #17233f;
border-radius: 10px 10px 0 0;
overflow: hidden;
margin-bottom: 0;
white-space: nowrap;
font-family: Arial, Helvetica, sans-serif;
}

.team_name{
flex: 1;
background: #17233f;
color: #fff;
padding: 10px 16px;
font-size: 18px;
font-weight: 700;
text-align: left;
}

.team_score{
display: none;
}

.team_opponent{
background: #17233f;
color: rgba(255,255,255,.85);
padding: 10px 16px;
font-size: 16px;
font-weight: 400;
text-align: right;
margin-left: auto;
}

.team_logo{
display: none;
}

.team_body{
display: grid;
grid-template-columns: 380px 1fr;
gap: 28px;
padding: 6px 18px 4px 18px;
align-items: start;
}

.formation{
width: 380px;
display: flex;
justify-content: center;
text-align: center;
}

.formation_label{
color: #666;
font-size: 9px;
font-weight: bold;
margin-bottom: 1px;
}

.formation_value{
font-size: 12px;
font-weight: bold;
margin-bottom: 1px;
}

.pitch{
position: relative;
width: 380px;
height: 380px;
border: 1px solid #d7dfe8;
border-radius: 8px;
background: #fff;
overflow: hidden;
}

.pitch::before{
display: none;
}

.midline{
position: absolute;
left: 0;
right: 0;
top: 50%;
border-top: 2px solid rgba(255,255,255,.85);
}

.centerdot{
position: absolute;
width: 6px;
height: 6px;
background: #fff;
border-radius: 50%;
left: 50%;
top: 50%;
transform: translate(-50%, -50%);
}

.centercircle{
position: absolute;
width: 74px;
height: 74px;
border: 1.5px solid #444;
border-radius: 50%;
left: 50%;
top: 50%;
transform: translate(-50%, -50%);
}

.penalty_top{
position: absolute;
left: 20%;
width: 60%;
height: 44px;
top: 0;
border: 1.5px solid #444;
border-top: none;
}

.penalty_bottom{
position: absolute;
left: 20%;
width: 60%;
height: 44px;
bottom: 0;
border: 1.5px solid #444;
border-bottom: none;
}

.goalbox_top{
position: absolute;
left: 35%;
width: 30%;
height: 16px;
top: 0;
border: 1.5px solid #444;
border-top: none;
}

.goalbox_bottom{
position: absolute;
left: 35%;
width: 30%;
height: 16px;
bottom: 0;
border: 1.5px solid #444;
border-bottom: none;
}

.penalty_dot_top{
position: absolute;
width: 3px;
height: 3px;
background: #222;
border-radius: 50%;
left: 50%;
top: 32px;
transform: translateX(-50%);
}

.penalty_dot_bottom{
position: absolute;
width: 3px;
height: 3px;
background: #222;
border-radius: 50%;
left: 50%;
bottom: 32px;
transform: translateX(-50%);
}

.corner_top_left{
position: absolute;
top: -8px;
left: -8px;
width: 16px;
height: 16px;
border: 1.5px solid #444;
border-radius: 50%;
}

.corner_top_right{
position: absolute;
top: -8px;
right: -8px;
width: 16px;
height: 16px;
border: 1.5px solid #444;
border-radius: 50%;
}

.corner_bottom_left{
position: absolute;
bottom: -8px;
left: -8px;
width: 16px;
height: 16px;
border: 1.5px solid #444;
border-radius: 50%;
}

.corner_bottom_right{
position: absolute;
bottom: -8px;
right: -8px;
width: 16px;
height: 16px;
border: 1.5px solid #444;
border-radius: 50%;
}

.player{
position: absolute;
transform: translate(-50%, -50%);
display: flex;
flex-direction: column;
align-items: center;
justify-content: center;
text-align: center;
z-index: 2;
}

.player_number{
    width: 50px;
    height: 50px;
    margin: 0;
    padding: 0;

    background: #000;
    border: none;
    border-radius: 50%;
    box-shadow: none;

    display: flex;
    align-items: center;
    justify-content: center;

    font-size: 16px;
    font-weight: 700;
    line-height: 1;
    color: #fff;
}

.player_name{
margin-top: 2px;
padding: 0;
background: none;
border: none;
box-shadow: none;
font-size: 11px;
font-weight: 700;
line-height: 1.1;
color: #111;
text-align: center;
white-space: nowrap;
}

.player_position{
display: none;
}

html{
-webkit-print-color-adjust: exact;
print-color-adjust: exact;
}

body{
-webkit-print-color-adjust: exact;
print-color-adjust: exact;
}
"""


FORMATION_COORDS = {
"4-2-3-1": {
    "GK":  {"top": 88, "left": 50},

    "LB":  {"top": 72, "left": 25},
    "CB1": {"top": 72, "left": 41},
    "CB2": {"top": 72, "left": 59},
    "RB":  {"top": 72, "left": 75},

    "DM1": {"top": 56, "left": 38},
    "DM2": {"top": 56, "left": 62},

    "LM":  {"top": 38, "left": 25},
    "AM":  {"top": 38, "left": 50},
    "RM":  {"top": 38, "left": 75},

    "ST":  {"top": 18, "left": 50},
}
}
