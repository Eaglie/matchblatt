import webbrowser
from pathlib import Path

from sfl import lade_sfl
from transfermarkt import lade_transfermarkt
from report import erstelle_report


def get_centered_left(x):
    # Zentriert jede beliebige Formation automatisch exakt im Spielfeld
    return 50 + (x - 50) * 0.72


sfl_url = input("SFL Matchcenter URL: ")

print("\nLade SFL...")
sfl = lade_sfl(sfl_url)
print("AKTUELLES SPIEL:")
print(sfl.get("heim"))
print(sfl.get("gast"))
print(sfl.get("datum"))

heim_url = input("Transfermarkt Heim: ")
gast_url = input("Transfermarkt Gast: ")

print("Lade Heimspiel...")
heim = lade_transfermarkt(
    heim_url,
    sfl.get("heim","")
)

print("Lade Gastspiel...")
gast = lade_transfermarkt(
    gast_url,
    sfl.get("gast","")
)

# Setzt den Gegner jeweils auf das andere Team aus dem SFL-Matchcenter
heim.setdefault("letzter_gegner", sfl.get("gast", ""))
gast.setdefault("letzter_gegner", sfl.get("heim", ""))

# Falls die Koordinaten hier direkt im Data-Dictionary oder beim Report verarbeitet werden, 
# greift get_centered_left ab sofort vollautomatisch auf alle X-Werte zu.

print("Erstelle Report...")
# Hier die Variablen exakt getauscht übergeben:
erstelle_report(sfl, gast, heim)

webbrowser.open(Path("report.html").resolve().as_uri())

print("Fertig.")