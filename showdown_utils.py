"""
Librería de utilidades para el bot de Pokémon Showdown.
Contiene la gestión de base de datos SQLite, registro de estadísticas de turnos,
generación de permutaciones para VGC y clases de jugadores base.
ESTE ARCHIVO NO DEBE EJECUTARSE DIRECTAMENTE.
"""

import hashlib
import itertools
import json
import random
import sqlite3
import threading
import time
from pathlib import Path

from poke_env.data import to_id_str
from poke_env.player import Player, MaxBasePowerPlayer
from poke_env.teambuilder import Teambuilder
from teams import USER_TEAM, OPPONENT_TEAMS

DB_DIR = Path(__file__).parent / "database" # Ruta del directorio donde se guardará la base de datos SQLite con las estadísticas de Showdown.
DB_DIR.mkdir(exist_ok=True) # Crea el directorio si no existe, para poder guardar la base de datos.
DB_PATH = DB_DIR / "showdown_stats.db" # Ruta de la base de datos SQLite donde se registrarán los resultados de las batallas.
DB_LOCK = threading.Lock() # Lock para asegurar que solo un hilo acceda a la base de datos SQLite a la vez, evitando errores de concurrencia.

# Genera las 360 permutaciones posibles para elegir 4 Pokémon de 6 ("1234", "1235", etc.)
VGC_TEAM_PREVIEW_COMBOS = [
    "".join(map(str, combo))
    for combo in itertools.permutations(range(1, 7), 4)
]

class VGCMaxBasePowerPlayer(MaxBasePowerPlayer):
    """
    Oponente con la heurística de MaxBasePowerPlayer para VGC.
    """
    def teampreview(self, battle):
        # Elige 4 de los 6 al azar (y marca _selected_in_teampreview
        # correctamente), en vez de traer siempre los 4 primeros.
        return self.random_teampreview(battle)

class RandomTeamFromPool(Teambuilder):
    """Elige un equipo al azar de una lista en cada partida."""

    def __init__(self, teams: list[str]):
        self.packed_teams = [
            # Los equipos se parsean y normalizan para que dos equipos con el mismo contenido
            # pero distinto orden o formato den el mismo team_id.
            self.join_team(self.parse_showdown_team(team)) for team in teams
        ]
    # Se elige un equipo al azar de la lista de equipos disponibles para cada partida.
    def yield_team(self) -> str:
        return random.choice(self.packed_teams)


# Subclase mínima solo para poder instanciar Teambuilder (es una clase
# abstracta) y usar sus métodos de parseo/normalización de equipos
# (parse_showdown_team / join_team). yield_team nunca se llega a llamar.
class _TeamParser(Teambuilder):
    def yield_team(self) -> str:
        return ""

# Instancia global de _TeamParser para poder usar sus métodos de parseo/normalización de equipos.
_team_parser = _TeamParser()


def compute_team_fingerprint(team_export: str) -> tuple[str, list[str]]:
    """
    A partir del texto 'Export' de un equipo, calcula:
    - team_id: hash corto del equipo ya normalizado.
    - roster: lista de las especies del equipo (para saber qué 6 Pokémon
      tiene disponibles ese team_id).
    """
    # Parsea y normaliza el equipo,
    # así dos equipos con el mismo contenido pero distinto orden o formato dan el mismo team_id.
    parsed = _team_parser.parse_showdown_team(team_export)
    packed = _team_parser.join_team(parsed)

    # Calcula un hash SHA256 del equipo normalizado y lo recorta a 12 caracteres.
    team_id = hashlib.sha256(packed.encode("utf-8")).hexdigest()[:12]

    # Extrae la lista de especies del equipo (roster).
    roster = sorted(
        to_id_str(getattr(mon, "species", None) or getattr(mon, "nickname", None))
        for mon in parsed
    )
    return team_id, roster


def init_db(db_path: Path) -> sqlite3.Connection:
    """
    Inicializa la base de datos SQLite para registrar estadísticas de Showdown.
    Crea las tablas necesarias si no existen y aplica migraciones si es necesario.
    Devuelve la conexión a la base de datos.
    """
    # Inicia la conexión a la base de datos SQLite, permitiendo acceso desde múltiples hilos.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # Configura el modo WAL (Write-Ahead Logging) para permitir concurrencia de lectura/escritura.
    conn.execute("PRAGMA journal_mode=WAL")

    # Crea las tablas necesarias si no existen.
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
    # Devuelve la conexión a la base de datos para que pueda ser usada por otros módulos.
    return conn


def ensure_team_registered(
    conn: sqlite3.Connection, team_id: str, team_export: str, roster: list[str]
    ) -> bool:
    """Da de alta el equipo en la tabla `teams` si no existía. Devuelve
    True si era un equipo NUEVO, False si ya se había jugado antes."""
    # Se asegura de que solo un hilo acceda a la base de datos a la vez.
    with DB_LOCK:
        # Comprueba si el team_id ya existe en la tabla `teams`.
        existing = conn.execute(
            "SELECT team_id FROM teams WHERE team_id = ?", (team_id,)
        ).fetchone()
        # Si ya existía, devuelve False. Si no existía, lo inserta y devuelve True.
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
    Intento de averiguar qué movimiento (o switch) eligió cada
    Pokémon activo, a partir del objeto BattleOrder que devuelve poke-env.
    Si la estructura interna no coincide con lo esperado (puede variar
    entre versiones), se guarda None para ese Pokémon en vez de fallar.
    """
    # Comprueba si el combate es de dobles, y si es así,
    # extrae las órdenes de cada Pokémon activo (first and second_order).
    first = getattr(order, "first_order", None)
    second = getattr(order, "second_order", None)

    if first is not None or second is not None:
        sub_orders = [first, second]
    # Si no, comprueba si el objeto order tiene un atributo 'orders' (para triples).
    elif hasattr(order, "orders"):
        sub_orders = list(order.orders)
    # Si no se cumple ninguna, se guarda la orden única en una lista (singles).
    else:
        sub_orders = [order]

    # Diccionario final para guardar qué movimiento eligió cada Pokémon activo.
    chosen = {}

    # Itera sobre los Pokémon activos y las órdenes correspondientes,
    #  y extrae el movimiento o switch elegido.
    for i, mon in enumerate(active_list):
        # Si no hay Pokémon activo en esa posición, se guarda None.
        if mon is None:
            continue

        # Obtenemos la sub-orden (orden de un solo pokemon) correspondiente.
        sub = sub_orders[i] if i < len(sub_orders) else None

        # Extrae el objeto de acción (Move o Pokemon) de la sub-orden.
        action_obj = getattr(sub, "order", None) if sub is not None else None

        # Dependiendo del tipo de acción, se guarda el id del movimiento,
        #  el nombre del Pokémon para switch,
        #  o None si no se pudo determinar.
        if action_obj is None:
            chosen[mon.species] = None
        elif hasattr(action_obj, "id"):  # Move
            chosen[mon.species] = action_obj.id
        elif hasattr(action_obj, "species"):  # Pokemon (switch)
            chosen[mon.species] = f"switch:{action_obj.species}"
        # Si no se reconoce el tipo de acción, se guarda la representación en string.
        else:
            chosen[mon.species] = str(action_obj)
    return chosen


class LoggingPlayer(Player):
    """
    Subclase de Player que registra en la base de datos SQLite cada turno
    y cada batalla finalizada, con toda la información relevante del combate.
    """

    # Inicializa el jugador con la conexión a la base de datos y un team_id.
    def __init__(self, *args, db_conn: sqlite3.Connection, team_id: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_conn = db_conn # Conexión a la base de datos SQLite para registrar estadísticas.
        self.team_id = team_id # Identificador del equipo del jugador.
        self._revealed_active: dict[str, dict[str, set]]= {}

    # Elige 4 de los 6 Pokémon al azar para la preview de VGC (y marca
    # _selected_in_teampreview correctamente en cada uno).
    def teampreview(self, battle):
        return self.random_teampreview(battle)

    # Registra la acción elegida en la base de datos y
    # devuelve la orden para que Showdown la ejecute.
    def choose_move(self, battle):
        order = self.choose_random_move(battle) # Elige un movimiento aleratorio
        self._log_turn(battle, order)
        return order

    # Registra qué Pokémon activos se han revelado en la batalla, para poder guardar
    #  la lista de Pokémon que participaron en la batalla al final.
    def _track_revealed(self, battle):
        # Se asegura de que haya un diccionario para este battle_tag,
        # con sets para "own" y "opponent".
        seen = self._revealed_active.setdefault(
            battle.battle_tag, {"own": set(), "opponent": set()}
        )
        # Actualiza los sets con las especies de los Pokémon activos en este turno.
        active_raw = battle.active_pokemon
        # Convierte a lista si es un solo Pokémon (singles) o ya es una lista (doubles).
        active_list = active_raw if isinstance(active_raw, list) else [active_raw]
        # Actualiza el set de Pokémon propios revelados con las especies de los Pokémon activos.
        seen["own"].update(mon.species for mon in active_list if mon is not None)

        # Hace lo mismo para los Pokémon activos del oponente.
        opp_raw = battle.opponent_active_pokemon
        opp_list = opp_raw if isinstance(opp_raw, list) else [opp_raw]
        seen["opponent"].update(mon.species for mon in opp_list if mon is not None)

    # Registra en la base de datos SQLite toda la información relevante del turno actual.
    def _log_turn(self, battle, order):
        # Actualiza la lista de Pokémon revelados en este turno.
        self._track_revealed(battle)

        active_raw = battle.active_pokemon
        active_list = active_raw if isinstance(active_raw, list) else [active_raw]
        # Convierte la lista de Pokémon activos a una lista de especies (o None si no hay Pokémon).
        active = [mon.species if mon else None for mon in active_list]

        opp_raw = battle.opponent_active_pokemon
        opp_list = opp_raw if isinstance(opp_raw, list) else [opp_raw]
        # Convierte la lista de Pokémon activos del oponente a una lista de especies (o None si no hay Pokémon).
        opp_active = [mon.species if mon else None for mon in opp_list]

        # Calcula la fracción de HP actual de cada Pokémon del equipo y del oponente.
        team_hp = {mon.species: mon.current_hp_fraction for mon in battle.team.values()}
        opp_hp = {
            mon.species: mon.current_hp_fraction for mon in battle.opponent_team.values()
        }

        # Registra el estado alterado (status) de cada Pokémon del equipo 
        # y del oponente (paralizado, dormido, etc.)    
        team_status = {
            mon.species: (mon.status.name if mon.status else None)
            for mon in battle.team.values()
        }
        opp_status = {
            mon.species: (mon.status.name if mon.status else None)
            for mon in battle.opponent_team.values()
        }

        # Registra los boosts de cada Pokémon activo (cambios en estadísticas) del equipo 
        # y del oponente.
        team_boosts = {
            mon.species: dict(mon.boosts) for mon in active_list if mon is not None
        }
        opp_boosts = {
            mon.species: dict(mon.boosts) for mon in opp_list if mon is not None
        }

        # Registra el clima (weather), el terreno (terrain) 
        # y las condiciones de lado (side conditions) del equipo y del oponente.
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

        # Extrae qué movimiento eligió cada Pokémon activo 
        # (o switch) a partir del objeto BattleOrder.
        chosen_moves = _extract_chosen_moves(active_list, order)

        # Inserta toda la información del turno en la tabla `turns` de la base de datos.
        with DB_LOCK: # Se asegura de que solo un hilo acceda a la base de datos a la vez.
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

    # Registra en la base de datos SQLite los resultados de la batalla al finalizar.
    def log_finished_battles(self):
        with DB_LOCK: # Se asegura de que solo un hilo acceda a la base de datos a la vez.
            for battle_tag, battle in self.battles.items():
                # Extrae los Pokémon que se han revelado durante la batalla 
                # (propios y del oponente).
                seen = self._revealed_active.get(battle_tag, {"own": set(), "opponent": set()})
                user_pokemon = sorted(seen["own"])
                opponent_pokemon = sorted(seen["opponent"])
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


class LoggingMaxBasePowerOpponent(LoggingPlayer):
    """Igual que LoggingPlayer, pero elige movimientos con la heurística de
    MaxBasePowerPlayer (máximo daño) en vez de al azar."""

    def choose_move(self, battle):
        if self.format_is_doubles:
            order = MaxBasePowerPlayer.choose_doubles_move(battle)
        else:
            order = MaxBasePowerPlayer.choose_singles_move(battle)
        self._log_turn(battle, order)
        return order