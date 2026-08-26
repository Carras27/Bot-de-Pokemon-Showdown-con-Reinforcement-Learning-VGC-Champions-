"""
Deja al agente entrenado esperando un reto TUYO en tu servidor local de
Showdown, para que puedas jugar una partida real contra él.

Requiere que tengas el servidor local corriendo (el mismo que usas para
entrenar) y el cliente de Showdown apuntando a él. El bot se conecta con
el nombre de usuario indicado en BOT_USERNAME: desde el cliente, busca
ese nombre y mándale un reto en el formato correcto
(gen9championsvgc2026regmb).

Uso:
    python play_vs_human.py
    python play_vs_human.py --n-challenges 3 --team-index 1
"""

import argparse
import asyncio
from pathlib import Path

from poke_env.ps_client import AccountConfiguration
from sb3_contrib import MaskablePPO

from eval_agent import RLPlayerWrapper, MODEL_NAME, BATTLE_FORMAT
from showdown_utils import compute_team_fingerprint, ensure_team_registered, init_db
from teams import USER_TEAMS

DB_PATH = Path(__file__).parent / "database" / "showdown_stats.db"

# Nombre con el que el bot se conecta al servidor local. Es el nombre al
# que tienes que retar desde el cliente de Showdown.
BOT_USERNAME = "RLPokeBot"


async def main(n_challenges: int, team_index: int):
    conn = init_db(DB_PATH)

    print(f"--- Cargando modelo: {MODEL_NAME} ---")
    model = MaskablePPO.load(MODEL_NAME)
    print(f"--- Este modelo lleva {model.num_timesteps} pasos entrenados ---")

    # Registra (o reutiliza) el team_id de este equipo concreto, igual que
    # hace eval_agent.py, para que estas partidas también salgan bien en
    # analyze_stats.py.
    team_export = USER_TEAMS[team_index]
    team_id, roster, team_string = compute_team_fingerprint(team_export)
    ensure_team_registered(conn, team_id, team_string, roster)

    bot = RLPlayerWrapper(
        model=model,
        battle_format=BATTLE_FORMAT,
        team=team_string,
        max_concurrent_battles=1,
        db_conn=conn,
        account_configuration=AccountConfiguration(BOT_USERNAME, None),
    )
    bot.team_id = team_id

    print(
        f"\n--- Esperando {n_challenges} reto(s) en tu servidor local. "
        f"Desde el cliente de Showdown, busca a '{BOT_USERNAME}' y mándale un reto "
        f"en formato {BATTLE_FORMAT} ---\n"
    )

    # Se queda esperando hasta recibir y jugar `n_challenges` retos de
    # CUALQUIER usuario (pasa tu propio username en vez de None si
    # quieres que solo acepte retos tuyos).
    await bot.accept_challenges(None, n_challenges)

    bot.log_finished_battles()
    conn.close()
    print("\n--- Partida(s) terminada(s) y registrada(s) en SQLite ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--n-challenges", type=int, default=1,
        help="Cuántos retos va a aceptar el bot antes de que el script termine.",
    )
    parser.add_argument(
        "--team-index", type=int, default=0,
        help="Índice del equipo de USER_TEAMS que usará el bot.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.n_challenges, args.team_index))
