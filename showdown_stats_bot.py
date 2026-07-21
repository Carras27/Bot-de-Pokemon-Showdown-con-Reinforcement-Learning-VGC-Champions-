"""
Bot de Pokémon Showdown que juega partidas y registra estadísticas en SQLite.

Cada equipo de usuario (USER_TEAM) se identifica automáticamente con un
"team_id" calculado a partir de su contenido normalizado (Pokémon, objeto,
EVs, naturaleza, movimientos). Si cambias cualquier cosa del equipo, el
team_id cambia solo y se registra como un equipo nuevo en la tabla `teams`;
si vuelves a jugar exactamente el mismo equipo, reconoce el team_id que ya
existía y sigue acumulando partidas ahí.

Requiere un servidor Showdown local corriendo (ver README.md) y poke-env
instalado (`pip install -r requirements.txt`).

Uso:
    python showdown_stats_bot.py --battles 10 --format gen9championsvgc2026regmb
"""

import argparse
import asyncio
import hashlib
import json
import random
import sqlite3
import threading
import time
from pathlib import Path

from poke_env.data import to_id_str
from poke_env.player import Player
from poke_env.teambuilder import Teambuilder

DB_DIR = Path(__file__).parent / "database"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "showdown_stats.db"
DB_LOCK = threading.Lock()

# -----------------------------------------------------------------------
# EQUIPO DEL JUGADOR 1 (el tuyo). Cámbialo cuantas veces quieras: cada
# equipo distinto se registra automáticamente con su propio team_id.
# Pégalo en formato "Export" de Showdown (Teambuilder -> Export).
# -----------------------------------------------------------------------
USER_TEAM = """
Aerodactyl @ Aerodactylite  
Ability: Unnerve  
Level: 50  
EVs: 2 HP / 32 Atk / 32 Spe  
Jolly Nature  
- Protect  
- Dual Wingbeat  
- Rock Slide  
- Tailwind  

Kingambit @ Black Glasses  
Ability: Supreme Overlord  
Level: 50  
EVs: 32 HP / 32 Atk / 2 Spe  
Adamant Nature  
- Kowtow Cleave  
- Iron Head  
- Sucker Punch  
- Swords Dance  

Gyarados @ Focus Sash  
Ability: Intimidate  
Level: 50  
EVs: 2 HP / 32 Atk / 32 Spe  
Jolly Nature  
- Waterfall  
- Earthquake  
- Ice Fang  
- Dragon Dance  

Hippowdon @ Sitrus Berry  
Ability: Sand Stream  
Level: 50  
EVs: 32 HP / 32 Def / 2 SpD  
Impish Nature  
- Earthquake  
- Slack Off  
- Yawn  
- Stealth Rock  

Archaludon @ Leftovers  
Ability: Stamina  
Level: 50  
EVs: 32 HP / 2 Def / 32 SpD  
Calm Nature  
- Thunderbolt  
- Draco Meteor  
- Stealth Rock  
- Roar  

Primarina @ Mystic Water  
Ability: Torrent  
Level: 50  
EVs: 32 HP / 32 SpA / 2 Spe  
Modest Nature  
- Sparkling Aria  
- Aqua Jet  
- Flip Turn  
- Moonblast  
"""

# Pool de equipos del jugador 2 (el "rival"). En cada partida se elige uno
# al azar de esta lista.
OPPONENT_TEAMS: list[str] = ["""
Kangaskhan-Mega @ Kangaskhanite
Ability: Scrappy
EVs: 2 HP / 32 Atk / 32 Spe
Jolly Nature
- Fake Out
- Double-Edge
- Sucker Punch
- Low Kick

Starmie @ Leftovers
Ability: Natural Cure
EVs: 32 SpA / 2 Def / 32 Spe
Timid Nature
- Surf
- Ice Beam
- Recover
- Rapid Spin

Arcanine @ Quick Claw
Ability: Intimidate
EVs: 32 HP / 2 Atk / 32 Spe
Jolly Nature
- Flare Blitz
- Extreme Speed
- Will-O-Wisp
- Morning Sun

Clefable @ Sitrus Berry
Ability: Unaware
EVs: 32 HP / 32 Def / 2 SpD
Bold Nature
- Moonblast
- Helping Hand
- Thunder Wave
- Stealth Rock

Alakazam @ Focus Sash
Ability: Magic Guard
EVs: 32 SpA / 2 SpD / 32 Spe
Timid Nature
- Psychic
- Shadow Ball
- Encore
- Focus Blast

Tauros-Paldea-Blaze @ Choice Scarf
Ability: Cud Chew
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Raging Bull
- Close Combat
- Flare Blitz
- Earthquake
""",
"""
Charizard @ Charizardite Y
Ability: Blaze
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Fire Blast
- Solar Beam
- Air Slash
- Roost

Venusaur @ Life Orb
Ability: Chlorophyll
EVs: 32 SpA / 2 SpD / 32 Spe
Timid Nature
- Giga Drain
- Sludge Bomb
- Earth Power
- Sleep Powder

Arcanine-Hisui @ Black Belt
Ability: Rock Head
EVs: 32 Atk / 2 Def / 32 Spe
Adamant Nature
- Head Smash
- Flare Blitz
- Extreme Speed
- Close Combat

Starmie @ Leftovers
Ability: Natural Cure
EVs: 32 SpA / 2 Def / 32 Spe
Timid Nature
- Surf
- Recover
- Rapid Spin
- Ice Beam

Clefable @ Sitrus Berry
Ability: Unaware
EVs: 32 HP / 32 Def / 2 SpD
Bold Nature
- Moonblast
- Stealth Rock
- Helping Hand
- Thunder Wave

Raichu-Alola @ Focus Sash
Ability: Surge Surfer
EVs: 32 SpA / 2 SpD / 32 Spe
Timid Nature
- Thunderbolt
- Grass Knot
- Encore
- Nasty Plot
""",
"""
Gengar @ Gengarite
Ability: Cursed Body
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Shadow Ball
- Sludge Bomb
- Focus Blast
- Destiny Bond

Machamp @ Quick Claw
Ability: No Guard
EVs: 32 HP / 32 Atk / 2 Def
Adamant Nature
- Dynamic Punch
- Knock Off
- Bullet Punch
- Ice Punch

Pidgeot-Mega @ Pidgeotite
Ability: No Guard
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Hurricane
- Heat Wave
- U-turn
- Roost

Starmie @ Leftovers
Ability: Natural Cure
EVs: 32 SpA / 2 Def / 32 Spe
Timid Nature
- Surf
- Recover
- Rapid Spin
- Thunderbolt

Ninetales-Alola @ Light Clay
Ability: Snow Warning
EVs: 32 HP / 2 SpD / 32 Spe
Timid Nature
- Aurora Veil
- Freeze-Dry
- Encore
- Moonblast

Tauros @ Choice Scarf
Ability: Intimidate
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Body Slam
- Earthquake
- Rock Slide
- Close Combat
""",
"""
Tyranitar @ Tyranitarite
Ability: Sand Stream
EVs: 32 HP / 32 Atk / 2 SpD
Adamant Nature
- Rock Slide
- Knock Off
- Low Kick
- Dragon Dance

Excadrill @ Life Orb
Ability: Sand Rush
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Earthquake
- Iron Head
- Rock Slide
- Protect

Rotom-Wash @ Sitrus Berry
Ability: Levitate
EVs: 32 HP / 22 Def / 12 SpD
Bold Nature
- Hydro Pump
- Volt Switch
- Will-O-Wisp
- Protect

Corviknight @ Leftovers
Ability: Mirror Armor
EVs: 32 HP / 22 Def / 12 SpD
Impish Nature
- Brave Bird
- Body Press
- Roost
- U-turn

Sinistcha @ Occa Berry
Ability: Hospitality
EVs: 32 HP / 20 Def / 14 SpD
Bold Nature
- Matcha Gotcha
- Rage Powder
- Strength Sap
- Trick Room

Primarina @ Mystic Water
Ability: Torrent
EVs: 32 HP / 32 SpA / 2 SpD
Modest Nature
- Moonblast
- Hydro Pump
- Ice Beam
- Psychic Noise
"""]  # <-- rellena con 1 o más equipos rivales


class RandomTeamFromPool(Teambuilder):
    """Elige un equipo al azar de una lista en cada partida."""

    def __init__(self, teams: list[str]):
        self.packed_teams = [
            self.join_team(self.parse_showdown_team(team)) for team in teams
        ]

    def yield_team(self) -> str:
        return random.choice(self.packed_teams)


# Subclase mínima solo para poder instanciar Teambuilder (es una clase
# abstracta) y usar sus métodos de parseo/normalización de equipos
# (parse_showdown_team / join_team). yield_team nunca se llega a llamar.
class _TeamParser(Teambuilder):
    def yield_team(self) -> str:
        return ""


_team_parser = _TeamParser()


def compute_team_fingerprint(team_export: str) -> tuple[str, list[str]]:
    """
    A partir del texto 'Export' de un equipo, calcula:
    - team_id: hash corto del equipo ya normalizado (packed format). Dos
      equipos son iguales si tienen el mismo team_id: mismos Pokémon,
      objetos, EVs, naturalezas y movimientos. Cualquier diferencia real
      cambia el hash; diferencias de formato (espacios, orden de líneas al
      pegar el Export) NO cambian el hash porque se normaliza antes.
    - roster: lista de las especies del equipo (para saber qué 6 Pokémon
      tiene disponibles ese team_id).
    """
    parsed = _team_parser.parse_showdown_team(team_export)
    packed = _team_parser.join_team(parsed)
    team_id = hashlib.sha256(packed.encode("utf-8")).hexdigest()[:12]
    roster = sorted(
        to_id_str(getattr(mon, "species", None) or getattr(mon, "nickname", None))
        for mon in parsed
    )
    return team_id, roster


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS teams (
            team_id TEXT PRIMARY KEY,
            team_export TEXT,
            roster TEXT,
            first_seen REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS battles (
            battle_id TEXT PRIMARY KEY,
            team_id TEXT,
            format TEXT,
            player_name TEXT,
            opponent_name TEXT,
            won INTEGER,
            total_turns INTEGER,
            user_pokemon TEXT,
            opponent_pokemon TEXT,
            finished_at REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            battle_id TEXT,
            turn_number INTEGER,
            active_pokemon TEXT,
            opponent_active TEXT,
            team_hp TEXT,
            opponent_hp TEXT,
            action_taken TEXT,
            chosen_moves TEXT,
            team_status TEXT,
            opponent_status TEXT,
            team_boosts TEXT,
            opponent_boosts TEXT,
            weather TEXT,
            terrain TEXT,
            own_side_conditions TEXT,
            opponent_side_conditions TEXT,
            timestamp REAL
        )
        """
    )

    # Migración: si vienes de una versión anterior del esquema, añade las
    # columnas que falten sin borrar nada de lo que ya tenías.
    migrations = {
        "battles": {"team_id": "TEXT"},
        "turns": {"chosen_moves": "TEXT"},
    }
    for table, columns in migrations.items():
        for column, col_type in columns.items():
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except sqlite3.OperationalError:
                pass  # La columna ya existe.

    conn.commit()
    return conn


def ensure_team_registered(
    conn: sqlite3.Connection, team_id: str, team_export: str, roster: list[str]
) -> bool:
    """Da de alta el equipo en la tabla `teams` si no existía. Devuelve
    True si era un equipo NUEVO, False si ya se había jugado antes."""
    with DB_LOCK:
        existing = conn.execute(
            "SELECT team_id FROM teams WHERE team_id = ?", (team_id,)
        ).fetchone()
        if existing is not None:
            return False
        conn.execute(
            "INSERT INTO teams (team_id, team_export, roster, first_seen) VALUES (?, ?, ?, ?)",
            (team_id, team_export, json.dumps(roster), time.time()),
        )
        conn.commit()
        return True


def _extract_chosen_moves(active_list, order) -> dict:
    """
    Intento best-effort de averiguar qué movimiento (o switch) eligió cada
    Pokémon activo, a partir del objeto BattleOrder que devuelve poke-env.
    Si la estructura interna no coincide con lo esperado (puede variar
    entre versiones), se guarda None para ese Pokémon en vez de fallar —
    el texto crudo de la acción sigue disponible en 'action_taken'.
    """
    first = getattr(order, "first_order", None)
    second = getattr(order, "second_order", None)
    if first is not None or second is not None:
        sub_orders = [first, second]
    elif hasattr(order, "orders"):
        sub_orders = list(order.orders)
    else:
        sub_orders = [order]

    chosen = {}
    for i, mon in enumerate(active_list):
        if mon is None:
            continue
        sub = sub_orders[i] if i < len(sub_orders) else None
        action_obj = getattr(sub, "order", None) if sub is not None else None
        if action_obj is None:
            chosen[mon.species] = None
        elif hasattr(action_obj, "id"):  # Move
            chosen[mon.species] = action_obj.id
        elif hasattr(action_obj, "species"):  # Pokemon (switch)
            chosen[mon.species] = f"switch:{action_obj.species}"
        else:
            chosen[mon.species] = str(action_obj)
    return chosen


class LoggingPlayer(Player):
    """
    Juega movimientos aleatorios válidos (sirve para singles o dobles) y,
    antes de cada decisión, vuelca el estado del battle a la base de datos.
    """

    def __init__(self, *args, db_conn: sqlite3.Connection, team_id: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_conn = db_conn
        self.team_id = team_id

    def choose_move(self, battle):
        order = self.choose_random_move(battle)
        self._log_turn(battle, order)
        return order

    def _log_turn(self, battle, order):
        active_raw = battle.active_pokemon
        active_list = active_raw if isinstance(active_raw, list) else [active_raw]
        active = [mon.species if mon else None for mon in active_list]

        opp_raw = battle.opponent_active_pokemon
        opp_list = opp_raw if isinstance(opp_raw, list) else [opp_raw]
        opp_active = [mon.species if mon else None for mon in opp_list]

        team_hp = {mon.species: mon.current_hp_fraction for mon in battle.team.values()}
        opp_hp = {
            mon.species: mon.current_hp_fraction for mon in battle.opponent_team.values()
        }

        team_status = {
            mon.species: (mon.status.name if mon.status else None)
            for mon in battle.team.values()
        }
        opp_status = {
            mon.species: (mon.status.name if mon.status else None)
            for mon in battle.opponent_team.values()
        }

        team_boosts = {
            mon.species: dict(mon.boosts) for mon in active_list if mon is not None
        }
        opp_boosts = {
            mon.species: dict(mon.boosts) for mon in opp_list if mon is not None
        }

        weather = (
            {w.name: turn for w, turn in battle.weather.items()} if battle.weather else {}
        )
        terrain = (
            {f.name: turn for f, turn in battle.fields.items()} if battle.fields else {}
        )
        own_side = (
            {sc.name: val for sc, val in battle.side_conditions.items()}
            if battle.side_conditions
            else {}
        )
        opp_side = (
            {sc.name: val for sc, val in battle.opponent_side_conditions.items()}
            if battle.opponent_side_conditions
            else {}
        )

        chosen_moves = _extract_chosen_moves(active_list, order)

        with DB_LOCK:
            self.db_conn.execute(
                """
                INSERT INTO turns
                    (battle_id, turn_number, active_pokemon, opponent_active, team_hp,
                     opponent_hp, action_taken, chosen_moves, team_status, opponent_status,
                     team_boosts, opponent_boosts, weather, terrain,
                     own_side_conditions, opponent_side_conditions, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    battle.battle_tag,
                    battle.turn,
                    json.dumps(active),
                    json.dumps(opp_active),
                    json.dumps(team_hp),
                    json.dumps(opp_hp),
                    str(order),
                    json.dumps(chosen_moves),
                    json.dumps(team_status),
                    json.dumps(opp_status),
                    json.dumps(team_boosts),
                    json.dumps(opp_boosts),
                    json.dumps(weather),
                    json.dumps(terrain),
                    json.dumps(own_side),
                    json.dumps(opp_side),
                    time.time(),
                ),
            )
            self.db_conn.commit()

    def log_finished_battles(self):
        with DB_LOCK:
            for battle_tag, battle in self.battles.items():
                user_pokemon = sorted(mon.species for mon in battle.team.values())
                opponent_pokemon = sorted(
                    mon.species for mon in battle.opponent_team.values()
                )
                self.db_conn.execute(
                    """
                    INSERT OR REPLACE INTO battles
                        (battle_id, team_id, format, player_name, opponent_name, won,
                         total_turns, user_pokemon, opponent_pokemon, finished_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        battle_tag,
                        self.team_id,
                        battle.format,
                        self.username,
                        getattr(battle, "opponent_username", None),
                        int(battle.won) if battle.won is not None else None,
                        battle.turn,
                        json.dumps(user_pokemon),
                        json.dumps(opponent_pokemon),
                        time.time(),
                    ),
                )
            self.db_conn.commit()


async def main(n_battles: int, battle_format: str):
    conn = init_db(DB_PATH)

    if not OPPONENT_TEAMS:
        raise ValueError(
            "Debes definir al menos 1 equipo en OPPONENT_TEAMS para el rival."
        )

    team_id, roster = compute_team_fingerprint(USER_TEAM)
    is_new = ensure_team_registered(conn, team_id, USER_TEAM, roster)
    if is_new:
        print(f"Equipo NUEVO registrado. team_id = {team_id}")
    else:
        print(f"Equipo ya conocido, sumando partidas. team_id = {team_id}")
    print(f"Roster: {', '.join(roster)}\n")

    opponent_pool = RandomTeamFromPool(OPPONENT_TEAMS)

    player_1 = LoggingPlayer(
        battle_format=battle_format,
        team=USER_TEAM,
        max_concurrent_battles=1,
        db_conn=conn,
        team_id=team_id,
    )
    player_2 = LoggingPlayer(
        battle_format=battle_format,
        team=opponent_pool,
        max_concurrent_battles=1,
        db_conn=conn,
    )

    await player_1.battle_against(player_2, n_battles=n_battles)

    player_1.log_finished_battles()

    print(f"Partidas jugadas: {player_1.n_finished_battles}")
    print(f"Victorias de {player_1.username}: {player_1.n_won_battles}")
    print(f"Datos guardados en: {DB_PATH}")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--battles", type=int, default=5, help="Número de partidas a jugar")
    parser.add_argument(
        "--format",
        type=str,
        default="gen9championsvgc2026regmb",
        help="Formato de batalla (verifica el nombre exacto en el desplegable de tu servidor local)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.battles, args.format))
