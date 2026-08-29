"""
Entrena (o continúa entrenando) un agente PPO para tu equipo de Pokémon
Champions VGC, usando SELF-PLAY.

En vez de pelear siempre contra el mismo heurístico, el entrenamiento se
divide en bloques de `--chunk-size` pasos. Al final de cada bloque se
guarda el modelo actual como checkpoint en un pool (self_play_pool/), y
para el SIGUIENTE bloque se sortea el oponente entre:
  - el heurístico MaxBasePower (con probabilidad --heuristic-prob), para
    que el agente no olvide cómo ganarle a un rival simple pero agresivo.
  - una versión congelada elegida al azar de entre TODO el pool de
    checkpoints propios (no solo la última), lo que evita que el agente
    se sobre-ajuste a pelear contra su versión más reciente y sea más
    robusto contra estilos de juego variados.

Uso:
    python3 train_agent.py --timesteps 200000
    python3 train_agent.py --timesteps 200000 --chunk-size 20000 --heuristic-prob 0.3
"""

import argparse
import os
import random
from pathlib import Path

from poke_env.environment.single_agent_wrapper import SingleAgentWrapper
from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor

from rl_env import ChampionsDoublesEnv, MaskableEnvWrapper
from showdown_utils import VGCMaxBasePowerPlayer, RandomTeamFromPool, RLOpponentPlayer
from teams import USER_TEAMS, OPPONENT_TEAMS

BATTLE_FORMAT = "gen9championsvgc2026regmb"  # Formato VGC Champions 2026 (dobles) Reglamento M-B
MODEL_NAME = "ppo_pokemon_bot"  # Nombre del archivo donde se guarda el modelo "principal"
POOL_DIR = Path("self_play_pool")  # Carpeta donde se guardan los checkpoints congelados
POOL_DIR.mkdir(exist_ok=True)


def pick_opponent(heuristic_prob: float):
    """
    Sortea el oponente para el próximo bloque de entrenamiento.

    Devuelve (opponent_player, descripcion_para_el_log). Si el pool de
    checkpoints todavía está vacío (primer bloque de una ejecución nueva),
    siempre usa el heurístico — no hay ninguna versión propia contra la
    que jugar todavía.
    """
    checkpoints = sorted(POOL_DIR.glob("*.zip"))

    if not checkpoints or random.random() < heuristic_prob:
        opponent = VGCMaxBasePowerPlayer(battle_format=BATTLE_FORMAT)
        return opponent, "heurístico (MaxBasePower)"

    checkpoint_path = random.choice(checkpoints)
    frozen_model = MaskablePPO.load(checkpoint_path)
    opponent = RLOpponentPlayer(model=frozen_model, battle_format=BATTLE_FORMAT)
    return opponent, f"self-play ({checkpoint_path.name})"


def make_env(opponent):
    """
    Crea el entorno de combate para un bloque de entrenamiento, contra el
    `opponent` que se le pase (heurístico o self-play).
    """
    user_team = RandomTeamFromPool(USER_TEAMS)

    base_env = ChampionsDoublesEnv(
        battle_format=BATTLE_FORMAT,
        team=user_team,
        strict=False,
        choose_on_teampreview=False,
    )

    # Equipo real del rival dentro del propio entorno base (dobles).
    base_env.agent2._team = RandomTeamFromPool(OPPONENT_TEAMS)

    env = SingleAgentWrapper(base_env, opponent)
    env = MaskableEnvWrapper(env)
    return Monitor(env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--timesteps", type=int, default=200_000,
        help="Total de pasos a entrenar en esta ejecución.",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=20_000,
        help="Cada cuántos pasos se guarda un checkpoint nuevo en el pool y se "
             "vuelve a sortear el oponente del siguiente bloque.",
    )
    parser.add_argument(
        "--heuristic-prob", type=float, default=0.3,
        help="Probabilidad de que el bloque entrene contra el heurístico en vez "
             "de contra un checkpoint del pool de self-play.",
    )
    parser.add_argument(
        "--pool-max", type=int, default=10,
        help="Nº máximo de checkpoints a conservar en el pool (se elimina el más "
             "antiguo cuando se supera).",
    )
    args = parser.parse_args()

    model = None
    steps_done = 0

    while steps_done < args.timesteps:
        chunk = min(args.chunk_size, args.timesteps - steps_done)

        opponent, opp_desc = pick_opponent(args.heuristic_prob)
        env = make_env(opponent)
        print(f"\n--- Bloque de pasos {steps_done} a {steps_done + chunk} | oponente: {opp_desc} ---")

        if model is None:
            if os.path.exists(f"{MODEL_NAME}.zip"):
                print(f"--- Cargando modelo existente: {MODEL_NAME} ---")
                model = MaskablePPO.load(MODEL_NAME, env=env)
                print(f"--- Pasos ya entrenados hasta ahora: {model.num_timesteps} ---")
            else:
                print("--- No se encontró modelo previo. Iniciando entrenamiento desde cero ---")
                model = MaskablePPO("MultiInputPolicy", env, verbose=1)
        else:
            # Reutiliza los pesos ya aprendidos, solo cambia el entorno
            # (y por tanto el oponente) para este bloque.
            model.set_env(env)

        model.learn(total_timesteps=chunk, reset_num_timesteps=False)
        steps_done += chunk

        # Guarda el modelo actual como checkpoint nuevo del pool, para que
        # futuros bloques puedan pelear contra esta versión concreta.
        checkpoint_path = POOL_DIR / f"ckpt_{model.num_timesteps}.zip"
        model.save(checkpoint_path)
        print(f"--- Checkpoint guardado en el pool: {checkpoint_path.name} ---")

        # Si el pool se pasa del tamaño máximo, se elimina el checkpoint
        # más antiguo (por fecha de modificación) para no acumular
        # indefinidamente ficheros .zip en disco.
        pool_checkpoints = sorted(POOL_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime)
        while len(pool_checkpoints) > args.pool_max:
            oldest = pool_checkpoints.pop(0)
            oldest.unlink()
            print(f"--- Pool lleno ({args.pool_max} máx.), eliminado el más antiguo: {oldest.name} ---")

        # Guarda también como el modelo "principal" tras cada bloque, por si
        # la ejecución se corta a mitad de un entrenamiento largo.
        model.save(MODEL_NAME)

    print(f"\n--- Entrenamiento terminado. Modelo final guardado como {MODEL_NAME}.zip "
          f"(total: {model.num_timesteps} pasos) ---")
