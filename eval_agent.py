"""
Hace jugar al agente RL, ya entrenado, partidas reales contra el pool de
equipos rivales. Y registra los resultados en la base de datos SQLite.

Uso:
    python eval_agent.py --battles 5
"""

import argparse
import asyncio
import sqlite3
import time
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

from rl_env import ChampionsDoublesEnv
from showdown_utils import (
    LoggingPlayer,
    LoggingMaxBasePowerOpponent,
    RandomTeamFromPool,
    compute_team_fingerprint,
    ensure_team_registered,
    init_db,
)
from teams import USER_TEAM, OPPONENT_TEAMS

DB_PATH = Path(__file__).parent / "database" / "showdown_stats.db" # Ruta de la base de datos SQLite donde se registrarán los resultados de las batallas.
MODEL_NAME = "ppo_pokemon_bot" # Nombre del fichero donde se guardó el modelo entrenado.
BATTLE_FORMAT = "gen9championsvgc2026regmb" # Nombre del formato de combate VGC Champions 2026 (dobles) Reglamento M-B, que se usará para las batallas.


class RLPlayerWrapper(LoggingPlayer):
    """
    Bot que envuelve un modelo entrenado por RL (PPO).
    """
    def __init__(self, model, *args, **kwargs):
        # Recibe la red neuronal entrenada (model) y los argumentos (usuario, formato, equipo, etc.)
        super().__init__(*args, **kwargs)

        # Guarda el modelo como atributo
        self.model = model

        # Crea una instancia de Gymnasium para traducir el combate de Showdown
        # a un formato que la red pueda entender (embed_battle).
        self._helper_env = ChampionsDoublesEnv(
            battle_format=BATTLE_FORMAT,
            start_listening=False, # Evita conectarse al servidor.
        )

    def choose_move(self, battle):
        """
        Se ejecuta cada vez que el bot necesita elegir un movimiento.
        """

        # Obtiene el array de la máscara de acciones válidas e inválidas.
        action_mask = np.array(self._helper_env.get_action_mask(battle))

        # Empaqueta el estado del combate a un formato que lo entienda la red neuronal
        state = {
            # Vector de observación, con los boosts, HPs, tipos, clima, estados, etc.
            "observation": self._helper_env.embed_battle(battle),
            # La máscara recién obtenida.
            "action_mask": action_mask,
        }

        # A partir del estado y la máscara, el modelo predice la mejor acción.
        # deterministic=True hace elegir siempre la opción con mayor probabilidad.
        action, _ = self.model.predict(state, action_masks=action_mask, deterministic=True)

        # Convierte la acción elegida al comando de Showdown corresponidiente.
        # strict=false hace que si la acción elegida es ilegal, se reemplace por una aleatoria válida y no crashear.
        order = ChampionsDoublesEnv.action_to_order(action, battle, strict=False)

        # Llama a la función de LoggingPlayer para registrar la acción elegida en la base de datos.
        self._log_turn(battle, order)

        # Devuelve la acción elegida para que Showdown lo ejecute.
        return order


async def main(n_battles: int):
    # Define la conexión con la base de datos SQLite donde
    #  se registrarán los resultados de las batallas.
    conn = init_db(DB_PATH)

    # Carga el modelo RL en una variable. Si no existe, se lanza un error.
    print(f"--- Cargando modelo: {MODEL_NAME} ---")
    model = MaskablePPO.load(MODEL_NAME)
    print(f"--- Este modelo lleva {model.num_timesteps} pasos entrenados ---")

    # Se asegura de que el equipo del agente esté registrado en la base de datos,
    #  y si no lo está, lo registra.
    team_id, roster = compute_team_fingerprint(USER_TEAM)
    is_new = ensure_team_registered(conn, team_id, USER_TEAM, roster)
    if is_new:
        print(f"--- Nuevo equipo registrado en la BD ---")
    else:
        print(f"--- Equipo ya conocido, sumando batallas ---")

    # Elige un equipo rival aleatorio del pool de OPPONENT_TEAMS
    #  y lo registra en la base de datos si es nuevo.
    opponent_pool = RandomTeamFromPool(OPPONENT_TEAMS)

    # Configura el oponente, su heurística, equipo, formato
    # y la conexión a la base de datos para registrar los resultados.
    opponent = LoggingMaxBasePowerOpponent(
        battle_format=BATTLE_FORMAT,
        team=opponent_pool,
        max_concurrent_battles=1,
        db_conn=conn,
    )

    # Configura el bot RL, con su modelo entrenado, equipo, formato
    # y la conexión a la base de datos para registrar los resultados.
    bot = RLPlayerWrapper(
        model=model,
        battle_format=BATTLE_FORMAT,
        team=USER_TEAM,
        max_concurrent_battles=1,
        db_conn=conn,
        team_id=team_id,
    )

    # Inicia las batallas, el bot RL contra el oponente heurístico.
    print("--- El agente RL está combatiendo... ---")
    await bot.battle_against(opponent, n_battles=n_battles)

    # Cuando las batallas terminan, registra los resultados en la base de datos
    # y cierra la conexión.
    bot.log_finished_battles()
    conn.close()
    print("--- Batallas registradas en SQLite ---")


if __name__ == "__main__":
    # Se parsean los argumentos de línea de comandos,
    # en este caso solo el número de batallas a jugar.
    parser = argparse.ArgumentParser()
    parser.add_argument("--battles", type=int, default=5)
    args = parser.parse_args()

    # Se ejecuta la función main() de manera asíncrona, pasando el número de batallas.
    asyncio.run(main(args.battles))
