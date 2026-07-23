"""
Entrena (o continúa entrenando) un agente PPO para tu equipo de Pokémon
Champions VGC.

Uso:
    python train_agent.py --timesteps 10000
"""

import argparse
import os

from poke_env.environment.single_agent_wrapper import SingleAgentWrapper
from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor

from rl_env import ChampionsDoublesEnv, MaskableEnvWrapper
from showdown_utils import VGCMaxBasePowerPlayer, RandomTeamFromPool
from teams import USER_TEAM, OPPONENT_TEAMS

BATTLE_FORMAT = "gen9championsvgc2026regmb" # Formato VGC Champions 2026 (dobles) Reglamento M-B
MODEL_NAME = "ppo_pokemon_bot" # Nombre del archivo donde se guardará el modelo entrenado


def make_env():
    """
    Crea el entorno de combate, el oponente usa el heurístico MaxBasePowerPlayer
    y elige el equipo aleatoriamente desde teams.py. El equipo usuario
    estará definido en teams.py. Se envuelve en MaskableEnvWrapper para exponer la
    máscara de acciones válidas a la red neuronal.
    """

    # Definimos al rival, con un equipo aleatorio y el formato de batalla.
    selected_team = RandomTeamFromPool(OPPONENT_TEAMS)
    opponent = VGCMaxBasePowerPlayer(battle_format=BATTLE_FORMAT, team=selected_team)

    # Definimos al bot a entrenar, con el equipo definido en teams.py
    # y el mismo formato de batalla.
    # strict=False Si se elige una acción ilegal, se reemplaza por una válida, sin crashear.
    # choose_on_teampreview=True La red neuronal también está obligada
    # a elegir el orden de salida en el preview, no solo los movimientos.
    base_env = ChampionsDoublesEnv(
        battle_format=BATTLE_FORMAT,                                                   
        team=USER_TEAM,
        strict=False, # 
        choose_on_teampreview=True, # 
    )

    # Función de poke-env que se encarga de pedirle al oponente sus acciones automáticamente,
    # para que el agente pueda centrarse solo en su propio equipo.
    env = SingleAgentWrapper(base_env, opponent) 

    # Envolvemos el entorno en MaskableEnvWrapper para exponer
    # la máscara de acciones válidas a la red neuronal.
    env = MaskableEnvWrapper(env)

    # Monitor de stable-baselines3 para registrar estadísticas de episodios
    # (recompensas, duración, etc.
    return Monitor(env) 

if __name__ == "__main__":
    # Se definen los argumentos de línea de comandos para el script.
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=10_000)
    args = parser.parse_args()
    # Se crea el entorno de combate.
    env = make_env()

    # Si existe un modelo previamente entrenado, se carga y se continúa el entrenamiento.
    if os.path.exists(f"{MODEL_NAME}.zip"):
        print(f"--- Cargando modelo existente: {MODEL_NAME} ---")
        model = MaskablePPO.load(MODEL_NAME, env=env)
        print(f"--- Pasos ya entrenados hasta ahora: {model.num_timesteps} ---")
        model.learn(total_timesteps=args.timesteps, reset_num_timesteps=False)
    # Si no existe un modelo previo, se crea uno nuevo y se entrena desde cero.
    else:
        print("--- No se encontró modelo previo. Iniciando entrenamiento desde cero ---")
        model = MaskablePPO("MultiInputPolicy", env, verbose=1)
        model.learn(total_timesteps=args.timesteps)

    # Finalmente, se guarda el modelo entrenado en un archivo .zip para poder cargarlo más tarde.
    model.save(MODEL_NAME)
    print(f"--- Modelo guardado como {MODEL_NAME}.zip (total: {model.num_timesteps} pasos) ---")
