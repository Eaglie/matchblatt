def header(
    heim_logo,
    gast_logo,
    heim,
    gast,
    liga,
    stadion,
    datum,
    zeit,
    schiedsrichter,
    var
):

    return f"""
<div class="title">

    <h1>
        {heim.upper()} – {gast.upper()}
    </h1>

    <div style="color:#ffffff; text-transform:uppercase;">
        SCHIEDSRICHTER: {schiedsrichter.upper()}
    </div>

    <div style="color:#ffffff; text-transform:uppercase;">
        VAR: {var.upper()}
    </div>

</div>
"""
