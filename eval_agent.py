"""
Hace jugar al agente RL ya entrenado partidas reales contra el pool de
equipos rivales, y registra los resultados en la misma base de datos que
usa showdown_stats_bot.py (para poder analizarlos con analyze_stats.py).

Cambios respecto a tu versión con la API antigua:
- action_to_move / _action_to_move ya no existen; el equivalente actual es
  el método estático DoublesEnv.action_to_order(action, battle).
- bot.ladder(n_battles=...) necesita un servidor con matchmaking real (otro
  cliente esperando partida). En un servidor LOCAL normalmente no hay nadie
  más laddeando, así que en vez de eso hacemos battle_against un rival
  concreto (igual que showdown_stats_bot.py), que es fiable en local.

Uso:
    python eval_agent.py --battles 5
"""

import argparse
import asyncio
import sqlite3
import time
from pathlib import Path

import numpy as np
from poke_env.player import MaxBasePowerPlayer
from sb3_contrib import MaskablePPO

from rl_env import ChampionsDoublesEnv
from showdown_utils import (
    LoggingPlayer,
    RandomTeamFromPool,
    compute_team_fingerprint,
    init_db,
)
from teams import USER_TEAM, OPPONENT_TEAMS

DB_PATH = Path(__file__).parent / "database" / "showdown_stats.db"
MODEL_NAME = "ppo_pokemon_bot"
BATTLE_FORMAT = "gen9championsvgc2026regmb"


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


class RLPlayerWrapper(LoggingPlayer):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        # Instancia auxiliar solo para reutilizar embed_battle; no se
        # conecta al servidor (start_listening=False), así que es segura
        # de crear sin gastar una conexión websocket real.
        self._helper_env = ChampionsDoublesEnv(
            battle_format=BATTLE_FORMAT,
            start_listening=False,
        )

    def choose_move(self, battle):
        action_mask = np.array(self._helper_env.get_action_mask(battle))
        state = {
            "observation": self._helper_env.embed_battle(battle),
            "action_mask": action_mask,
        }
        action, _ = self.model.predict(state, action_masks=action_mask, deterministic=True)
        order = ChampionsDoublesEnv.action_to_order(action, battle, strict=False)
        self._log_turn(battle, order)
        return order


def register_rl_team(conn: sqlite3.Connection, rl_team_id: str):
    """Registra el agente RL en la tabla `teams` con un team_id propio,
    para distinguir sus partidas de las del bot aleatorio que usa el mismo
    roster, y para que analyze_stats.py pueda leer su roster correctamente."""
    _, roster = compute_team_fingerprint(USER_TEAM)
    existing = conn.execute(
        "SELECT team_id FROM teams WHERE team_id = ?", (rl_team_id,)
    ).fetchone()
    if existing is None:
        import json

        conn.execute(
            "INSERT INTO teams (team_id, team_export, roster, first_seen) VALUES (?, ?, ?, ?)",
            (rl_team_id, USER_TEAM, json.dumps(roster), time.time()),
        )
        conn.commit()


async def main(n_battles: int):
    conn = init_db(DB_PATH)

    print(f"--- Cargando modelo: {MODEL_NAME} ---")
    model = MaskablePPO.load(MODEL_NAME)

    # team_id único según cuánto ha entrenado el modelo en este momento,
    # así evaluaciones en distintos puntos del entrenamiento quedan
    # separadas automáticamente (nunca se mezclan en analyze_stats.py).
    rl_team_id = f"RL_AGENT_{model.num_timesteps}steps"
    print(f"--- Este modelo lleva {model.num_timesteps} pasos entrenados ---")
    print(f"--- Sus partidas se guardarán bajo team_id = {rl_team_id} ---")

    register_rl_team(conn, rl_team_id)

    opponent_pool = RandomTeamFromPool(OPPONENT_TEAMS)
    opponent = LoggingMaxBasePowerOpponent(
        battle_format=BATTLE_FORMAT,
        team=opponent_pool,
        max_concurrent_battles=1,
        db_conn=conn,
    )

    bot = RLPlayerWrapper(
        model=model,
        battle_format=BATTLE_FORMAT,
        team=USER_TEAM,
        max_concurrent_battles=1,
        db_conn=conn,
        team_id=rl_team_id,
    )

    print("--- El agente RL está combatiendo... ---")
    await bot.battle_against(opponent, n_battles=n_battles)

    bot.log_finished_battles()
    conn.close()
    print("--- Batallas registradas en SQLite ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--battles", type=int, default=5)
    args = parser.parse_args()

    asyncio.run(main(args.battles))
