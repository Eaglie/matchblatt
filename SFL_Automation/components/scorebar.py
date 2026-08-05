def scorebar(teamname, logo, resultat, letzter_gegner):

    return f"""
<div class="team_head">
    <span class="team_name">{teamname.upper()}</span>
    <span class="team_opponent">
        Letztes Spiel: {teamname} {resultat} {letzter_gegner}
    </span>
</div>
"""