def hole_offizielle(opta_id, heim="", gast=""):
    """
    Holt Schiedsrichter und VAR aus dem SFL-Header.
    Die API liefert die Daten unter:
    fixturesAndResults -> match -> liveData ->
    matchDetailsExtra -> matchOfficial
    """

    url = (
        "https://origins-widgets-orchestrator.origins-digital.com"
        f"/api/header?fixtureId={opta_id}"
    )

    response = requests.get(
        url,
        headers={
            "Accept": "*/*",
            "Accept-Language": "de",
            "Origin": "https://sfl.ch",
            "Referer": "https://sfl.ch/",
            "User-Agent": "Mozilla/5.0",
            "x-account-key": "Os-hXumIK",
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    matches = (
        data
        .get("fixturesAndResults", {})
        .get("match", [])
    )

    schiedsrichter = ""
    var = ""

    # Passendes Spiel suchen
    passendes_match = None

    for match in matches:

        match_info = match.get("matchInfo", {})

        description = match_info.get(
            "description",
            ""
        )

        if heim and gast:
            if (
                heim.replace("FC ", "") in description
                and gast.replace("FC ", "") in description
            ):
                passendes_match = match
                break

        # Falls nur ein Match zurückkommt
        if len(matches) == 1:
            passendes_match = match

    if passendes_match is None:
        return "", ""

    offizielle = (
        passendes_match
        .get("liveData", {})
        .get("matchDetailsExtra", {})
        .get("matchOfficial", [])
    )

    for person in offizielle:

        typ = person.get("type", "")

        name = " ".join(
            x for x in [
                person.get("firstName", ""),
                person.get("lastName", "")
            ]
            if x
        ).strip()

        if typ == "Main":
            schiedsrichter = name

        elif typ == "Video Assistant Referee":
            var = name

    return schiedsrichter, var
