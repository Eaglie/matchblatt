def team_information(daten):
    return """
    <div class="team_body">
        <!-- 1. Linke Spalte: Formation + Spielfeld -->
        <div class="team_left_column">
            <div class="formation">
                <div class="formation_label">Formation</div>
                <div class="formation_value">4-2-3-1</div>
            </div>
            <div class="pitch">
                <!-- Hier wird das Spielfeld gerendert -->
            </div>
        </div>

        <!-- 2. Rechte Spalte: Absenzen oben, Ersatzbank direkt darunter -->
        <div class="team_right_column">
            <h3 style="margin: 0 0 6px 0; font-size: 14px;">Absenzen</h3>
            <table class="absence">
                <tr><td>Gesperrt</td><td></td></tr>
                <tr><td>Verletzt</td><td></td></tr>
                <tr><td>Krank</td><td></td></tr>
                <tr><td>Fraglich</td><td></td></tr>
            </table>

            <h3 style="margin: 15px 0 6px 0; font-size: 14px;">Ersatzbank</h3>
            <table class="bench">
                <tr>
                    <td><span class="bench-number">1</span>Thomas Castella</td>
                    <td style="text-align: right; color: #555; font-weight: bold;">TW</td>
                </tr>
                <tr>
                    <td><span class="bench-number">3</span>Tyler Fredricson</td>
                    <td style="text-align: right; color: #555; font-weight: bold;">IV</td>
                </tr>
                <tr>
                    <td><span class="bench-number">5</span>Dircssi Ngonzo</td>
                    <td style="text-align: right; color: #555; font-weight: bold;">IV</td>
                </tr>
                <tr>
                    <td><span class="bench-number">6</span>Theo Bergvall</td>
                    <td style="text-align: right; color: #555; font-weight: bold;">RV</td>
                </tr>
                <tr>
                    <td><span class="bench-number">80</span>Sékou Koné</td>
                    <td style="text-align: right; color: #555; font-weight: bold;">DM</td>
                </tr>
                <tr>
                    <td><span class="bench-number">91</span>Florent Mollet</td>
                    <td style="text-align: right; color: #555; font-weight: bold;">OM</td>
                </tr>
                <tr>
                    <td><span class="bench-number">7</span>Alban Ajdini</td>
                    <td style="text-align: right; color: #555; font-weight: bold;">RA</td>
                </tr>
                <tr>
                    <td><span class="bench-number">49</span>Ilija Despotovic</td>
                    <td style="text-align: right; color: #555; font-weight: bold;">MS</td>
                </tr>
                <tr>
                    <td><span class="bench-number">17</span>Seydou Traoré</td>
                    <td style="text-align: right; color: #555; font-weight: bold;">MS</td>
                </tr>
                <tr class="bench-trainer">
                    <td colspan="2">Trainer: Luka Elsner</td>
                </tr>
            </table>
        </div>
    </div>
    """