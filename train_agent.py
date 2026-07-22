"""
Entrena (o continúa entrenando) un agente PPO para tu equipo de Pokémon
Champions VGC.

A diferencia de la API antigua (Gen9EnvSinglePlayer), con la API actual no
hace falta lanzar el oponente manualmente con asyncio ni accept_challenges:
SingleAgentWrapper se encarga de pedirle una acción al oponente en cada
turno automáticamente.

Uso:
    python train_agent.py --timesteps 10000
"""

import argparse
import os

import gymnasium as gym
from poke_env.environment.single_agent_wrapper import SingleAgentWrapper
from poke_env.player import MaxBasePowerPlayer
from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor

from rl_env import ChampionsDoublesEnv
from teams import USER_TEAM

BATTLE_FORMAT = "gen9championsvgc2026regmb"
MODEL_NAME = "ppo_pokemon_bot"


class MaskableEnvWrapper(gym.Wrapper):
    """
    PPO normal ignora el 'action_mask' que trae la observación, así que
    puede elegir acciones inválidas (ej. un movimiento durante el Team
    Preview) y el simulador las rechaza con un error. MaskablePPO sí lo
    respeta, pero necesita que el env exponga un método action_masks();
    este wrapper lo construye a partir del 'action_mask' que ya viene
    dentro de cada observación de poke-env.
    """

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self._last_mask = obs["action_mask"]
        return obs, info

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        self._last_mask = obs["action_mask"]
        return obs, reward, terminated, truncated, info

    def action_masks(self):
        return self._last_mask


def make_env():
    # V1: el oponente usa el mismo USER_TEAM (limitación actual de poke-env:
    # el entorno solo acepta un único `team` compartido por ambos lados).
    # Rival heurístico (máximo daño) en vez de random puro: más difícil de
    # "resolver" por el agente, así que el aprendizaje es más informativo.
    opponent = MaxBasePowerPlayer(battle_format=BATTLE_FORMAT, team=USER_TEAM)

    base_env = ChampionsDoublesEnv(
        battle_format=BATTLE_FORMAT,
        team=USER_TEAM,
        strict=False,
        choose_on_teampreview=False,
    )
    env = SingleAgentWrapper(base_env, opponent)
    env = MaskableEnvWrapper(env)
    return Monitor(env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=10_000)
    args = parser.parse_args()

    env = make_env()

    if os.path.exists(f"{MODEL_NAME}.zip"):
        print(f"--- Cargando modelo existente: {MODEL_NAME} ---")
        model = MaskablePPO.load(MODEL_NAME, env=env)
        print(f"--- Pasos ya entrenados hasta ahora: {model.num_timesteps} ---")
        model.learn(total_timesteps=args.timesteps, reset_num_timesteps=False)
    else:
        print("--- No se encontró modelo previo. Iniciando entrenamiento desde cero ---")
        model = MaskablePPO("MultiInputPolicy", env, verbose=1)
        model.learn(total_timesteps=args.timesteps)

    model.save(MODEL_NAME)
    print(f"--- Modelo guardado como {MODEL_NAME}.zip (total: {model.num_timesteps} pasos) ---")
