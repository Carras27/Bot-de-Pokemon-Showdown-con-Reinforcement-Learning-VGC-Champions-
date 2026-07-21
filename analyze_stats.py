"""
Analiza la base de datos generada por showdown_stats_bot.py.

Para CADA equipo de usuario registrado (team_id) calcula:

1. % de victorias del equipo.
2. % de veces que cada Pokémon del roster (6) fue elegido en el Team
   Preview (de 6 se eligen 4 en VGC/Champions).
3. % de elección de cada movimiento, por Pokémon (de los turnos donde
   ese Pokémon estaba activo, qué % de las veces se usó cada movimiento).
4. Además, el detalle de matchups y Pokémon rivales que ya teníamos.

Con --global, en vez de agrupar por equipo, agrupa por NOMBRE de especie
cruzando todos los equipos donde haya aparecido (si tu Aerodactyl está en
dos equipos distintos, cuenta como un único Aerodactyl).

Uso:
    python analyze_stats.py --db database/showdown_stats.db
    python analyze_stats.py --db database/showdown_stats.db --team-id a1b2c3d4e5f6
    python analyze_stats.py --db database/showdown_stats.db --global
"""

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path


def load_teams(conn):
    rows = conn.execute("SELECT team_id, roster, first_seen FROM teams").fetchall()
    return {
        row["team_id"]: {
            "roster": json.loads(row["roster"]),
            "first_seen": row["first_seen"],
        }
        for row in rows
    }


def compute_global_pokemon_stats(battles, chosen_moves_by_battle):
    """
    Agrupa por NOMBRE de especie, ignorando de qué team_id venga. Devuelve:
    - win_stats: {especie: [victorias, apariciones]}
    - move_usage: {especie: {movimiento: veces_usado}}
    """
    win_stats = defaultdict(lambda: [0, 0])
    move_usage = defaultdict(lambda: defaultdict(int))

    for b in battles:
        for mon in b["user_pokemon"]:
            win_stats[mon][1] += 1
            if b["won"]:
                win_stats[mon][0] += 1

        for turn_moves in chosen_moves_by_battle.get(b["battle_id"], []):
            for mon, move in turn_moves.items():
                if move is None:
                    continue
                move_usage[mon][move] += 1

    return win_stats, move_usage


def print_global_report(win_stats, move_usage, min_battles):
    print("#" * 70)
    print("VISIÓN GLOBAL POR POKÉMON (cruzando todos los equipos)")
    print("#" * 70)

    print("\n--- % de victorias del equipo cuando este Pokémon participó ---")
    for mon, (wins, total) in sorted(
        win_stats.items(), key=lambda kv: -kv[1][0] / kv[1][1] if kv[1][1] else 0
    ):
        if total < min_battles:
            continue
        print(f"{mon:<22} {pct(wins, total):>7}  ({wins}/{total} partidas)")

    print("\n--- % de elección de cada movimiento, por Pokémon ---")
    for mon, moves in sorted(move_usage.items()):
        total_uses = sum(moves.values())
        print(f"{mon}:")
        for move, count in sorted(moves.items(), key=lambda kv: -kv[1]):
            print(f"    {move:<20} {pct(count, total_uses):>7}  ({count}/{total_uses})")
    print()



def load_battles(conn, team_id: str | None):
    query = "SELECT battle_id, team_id, won, user_pokemon, opponent_pokemon FROM battles"
    params = ()
    if team_id:
        query += " WHERE team_id = ?"
        params = (team_id,)
    rows = conn.execute(query, params).fetchall()

    battles = []
    skipped = 0
    for row in rows:
        if row["won"] is None or row["user_pokemon"] is None or row["opponent_pokemon"] is None:
            skipped += 1
            continue
        battles.append(
            {
                "battle_id": row["battle_id"],
                "team_id": row["team_id"],
                "won": bool(row["won"]),
                "user_pokemon": json.loads(row["user_pokemon"]),
                "opponent_pokemon": json.loads(row["opponent_pokemon"]),
            }
        )
    return battles, skipped


def load_chosen_moves(conn, battle_ids: set):
    """Devuelve {battle_id: [ {pokemon: movimiento_o_switch}, ... ] } con
    una entrada por turno registrado de esa partida."""
    if not battle_ids:
        return {}
    placeholders = ",".join("?" for _ in battle_ids)
    rows = conn.execute(
        f"SELECT battle_id, chosen_moves FROM turns WHERE battle_id IN ({placeholders})",
        tuple(battle_ids),
    ).fetchall()

    result = defaultdict(list)
    for row in rows:
        if row["chosen_moves"] is None:
            continue
        result[row["battle_id"]].append(json.loads(row["chosen_moves"]))
    return result


def pct(count: int, total: int) -> str:
    if total == 0:
        return "N/A"
    return f"{100 * count / total:.1f}%"


def compute_win_rate(battles):
    total = len(battles)
    wins = sum(1 for b in battles if b["won"])
    return wins, total


def compute_pokemon_pick_rate(battles, roster):
    """% de partidas en las que cada Pokémon del roster fue elegido."""
    counts = {mon: 0 for mon in roster}
    total = len(battles)
    for b in battles:
        for mon in b["user_pokemon"]:
            if mon in counts:
                counts[mon] += 1
    return counts, total


def compute_move_usage(battles, chosen_moves_by_battle):
    """
    {pokemon: {movimiento_o_switch: veces_usado}} contando cada turno en
    el que ese Pokémon estaba activo y eligió esa acción.
    """
    usage = defaultdict(lambda: defaultdict(int))
    for b in battles:
        for turn_moves in chosen_moves_by_battle.get(b["battle_id"], []):
            for mon, move in turn_moves.items():
                if move is None:
                    continue
                usage[mon][move] += 1
    return usage


def compute_opponent_and_matchup_stats(battles):
    opponent_stats = defaultdict(lambda: [0, 0])
    matchup_stats = defaultdict(lambda: [0, 0])

    for battle in battles:
        won = battle["won"]

        for mon in battle["opponent_pokemon"]:
            opponent_stats[mon][1] += 1
            if not won:
                opponent_stats[mon][0] += 1

        for user_mon in battle["user_pokemon"]:
            for opp_mon in battle["opponent_pokemon"]:
                key = (user_mon, opp_mon)
                matchup_stats[key][1] += 1
                if won:
                    matchup_stats[key][0] += 1

    return opponent_stats, matchup_stats


def print_team_report(team_id, team_info, battles, chosen_moves_by_battle, min_battles):
    roster = team_info["roster"]

    print("#" * 70)
    print(f"EQUIPO team_id = {team_id}")
    print(f"Roster: {', '.join(roster)}")
    print("#" * 70)

    wins, total = compute_win_rate(battles)
    print(f"\n% de victorias del equipo: {pct(wins, total)}  ({wins}/{total} partidas)")

    if total < min_battles:
        print(
            f"(Menos de {min_battles} partidas registradas todavía — "
            f"los porcentajes de abajo pueden no ser fiables)"
        )

    print("\n--- % de veces elegido en Team Preview (de 6 se eligen 4) ---")
    pick_counts, pick_total = compute_pokemon_pick_rate(battles, roster)
    for mon in sorted(roster, key=lambda m: -pick_counts[m]):
        print(f"{mon:<22} {pct(pick_counts[mon], pick_total):>7}  ({pick_counts[mon]}/{pick_total})")

    print("\n--- % de elección de cada movimiento, por Pokémon ---")
    move_usage = compute_move_usage(battles, chosen_moves_by_battle)
    for mon in roster:
        moves = move_usage.get(mon)
        if not moves:
            print(f"{mon}: sin datos de movimientos todavía")
            continue
        total_uses = sum(moves.values())
        print(f"{mon}:")
        for move, count in sorted(moves.items(), key=lambda kv: -kv[1]):
            print(f"    {move:<20} {pct(count, total_uses):>7}  ({count}/{total_uses})")

    opponent_stats, matchup_stats = compute_opponent_and_matchup_stats(battles)

    print("\n--- % de victorias del rival, por Pokémon suyo ---")
    for mon, (wins_opp, total_opp) in sorted(
        opponent_stats.items(), key=lambda kv: -kv[1][0] / kv[1][1] if kv[1][1] else 0
    ):
        if total_opp < min_battles:
            continue
        print(f"{mon:<22} {pct(wins_opp, total_opp):>7}  ({wins_opp}/{total_opp})")

    print("\n--- % de victorias por matchup (tu Pokémon vs el suyo) ---")
    for (user_mon, opp_mon), (wins_m, total_m) in sorted(
        matchup_stats.items(), key=lambda kv: -kv[1][0] / kv[1][1] if kv[1][1] else 0
    ):
        if total_m < min_battles:
            continue
        print(f"{user_mon:<20} vs {opp_mon:<20} {pct(wins_m, total_m):>7}  ({wins_m}/{total_m})")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        type=str,
        required=True,
        help="Ruta a la base de datos (ej. database/showdown_stats.db)",
    )
    parser.add_argument(
        "--team-id",
        type=str,
        default=None,
        help="Analiza solo este team_id. Si no se indica, analiza todos los equipos registrados.",
    )
    parser.add_argument(
        "--global",
        dest="global_view",
        action="store_true",
        help="Agrupa por nombre de especie cruzando todos los equipos, en vez de por team_id.",
    )
    parser.add_argument(
        "--min-battles",
        type=int,
        default=1,
        help="Ignora filas con menos de N partidas para evitar % poco fiables",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"No se encontró la base de datos: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    teams = load_teams(conn)
    if not teams:
        raise SystemExit("Todavía no hay ningún equipo registrado en esta base de datos.")

    if args.global_view:
        battles, skipped = load_battles(conn, team_id=None)
        if skipped:
            print(
                f"Aviso: se ignoraron {skipped} partidas sin datos completos "
                f"(por ejemplo, corridas con una versión antigua del bot).\n"
            )
        if not battles:
            raise SystemExit("Todavía no hay partidas completas para analizar.")

        battle_ids = {b["battle_id"] for b in battles}
        chosen_moves_by_battle = load_chosen_moves(conn, battle_ids)
        win_stats, move_usage = compute_global_pokemon_stats(battles, chosen_moves_by_battle)
        print_global_report(win_stats, move_usage, args.min_battles)
        conn.close()
        raise SystemExit(0)

    team_ids = [args.team_id] if args.team_id else list(teams.keys())

    for team_id in team_ids:
        if team_id not in teams:
            print(f"Aviso: team_id '{team_id}' no encontrado, se omite.\n")
            continue

        battles, skipped = load_battles(conn, team_id)
        if skipped:
            print(
                f"Aviso: se ignoraron {skipped} partidas de este equipo sin datos "
                f"completos (por ejemplo, corridas con una versión antigua del bot).\n"
            )
        if not battles:
            print(f"team_id {team_id}: todavía no hay partidas completas para analizar.\n")
            continue

        battle_ids = {b["battle_id"] for b in battles}
        chosen_moves_by_battle = load_chosen_moves(conn, battle_ids)

        print_team_report(team_id, teams[team_id], battles, chosen_moves_by_battle, args.min_battles)

    conn.close()
