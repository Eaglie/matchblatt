import webbrowser
from pathlib import Path

from sfl import lade_sfl
from transfermarkt import lade_transfermarkt
from report import erstelle_report


sfl_url = input("SFL Matchcenter URL: ").strip()

print("\nLade SFL...")

sfl = lade_sfl(
    sfl_url
)

print("AKTUELLES SPIEL:")
print(sfl.get("heim"))
print(sfl.get("gast"))
print(sfl.get("datum"))

heim_url = input(
    "Transfermarkt Heim: "
).strip()

gast_url = input(
    "Transfermarkt Gast: "
).strip()


print("Lade Heimspiel...")

heim = lade_transfermarkt(
    heim_url,
    sfl.get("heim", "")
)


print("Lade Gastspiel...")

gast = lade_transfermarkt(
    gast_url,
    sfl.get("gast", "")
)


print("Erstelle Report...")

erstelle_report(
    sfl,
    heim,
    gast
)


webbrowser.open(
    Path("report.html").resolve().as_uri()
)

print("Fertig.")
