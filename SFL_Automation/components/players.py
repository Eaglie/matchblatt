def players(spieler):

    html = ""

    for p in spieler:

        nummer = p.get("nummer", "")
        name = p.get("name", "")
        position = p.get("position", "")

        x = p.get("left", p.get("x", 50))
        y = p.get("top", p.get("y", 50))

        html += f"""
<div class="player" style="left:{x}%;top:{y}%">

    <div class="player_circle" style="background:#000000; color:#ffffff; border-radius:50%; width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-size:15px; font-weight:700;">{nummer}</div>

<div class="player_name">{name}</div>

    <div class="player_position">{position}</div>

</div>
"""

    return html
