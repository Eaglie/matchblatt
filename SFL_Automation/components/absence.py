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