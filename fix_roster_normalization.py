"""
Migración única: corrige el roster ya guardado en la tabla `teams` para que
use el mismo formato normalizado que poke-env usa en mon.species durante
las partidas reales (ej. "Aerodactyl" -> "aerodactyl",
"Tauros-Paldea-Blaze" -> "taurospaldeablaze"). Sin esto, analyze_stats.py
no puede cruzar el roster con los Pokémon que aparecen en las partidas.

No toca las tablas `battles` ni `turns` — esos datos ya estaban guardados
correctamente, el problema era solo el roster de `teams`.

Uso:
    python fix_roster_normalization.py --db database/showdown_stats.db
"""

import argparse
import json
import sqlite3
from pathlib import Path

from poke_env.data import to_id_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, required=True)
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"No se encontró la base de datos: {db_path}")

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT team_id, roster FROM teams").fetchall()

    updated = 0
    for team_id, roster_json in rows:
        old_roster = json.loads(roster_json)
        new_roster = sorted(to_id_str(mon) for mon in old_roster)
        if new_roster != old_roster:
            conn.execute(
                "UPDATE teams SET roster = ? WHERE team_id = ?",
                (json.dumps(new_roster), team_id),
            )
            updated += 1
            print(f"{team_id}: {old_roster} -> {new_roster}")

    conn.commit()
    conn.close()
    print(f"\n{updated} equipo(s) corregido(s) de {len(rows)} en total.")
