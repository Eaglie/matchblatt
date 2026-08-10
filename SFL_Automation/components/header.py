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
<div class="header">

    <div class="title">

        <h1>
            {heim.upper()} – {gast.upper()}
        </h1>

  <h2>
    {stadion} • <span class="header_label">Schiedsrichter:</span> <span class="header_value">{schiedsrichter}</span> • <span class="header_label">VAR:</span> <span class="header_value">{var}</span>
</h2>

    </div>

</div>
"""
