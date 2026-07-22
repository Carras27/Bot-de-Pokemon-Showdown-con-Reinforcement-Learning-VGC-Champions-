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
import random
import itertools

import gymnasium as gym
from poke_env.environment.single_agent_wrapper import SingleAgentWrapper
from poke_env.player import MaxBasePowerPlayer
from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor

from rl_env import ChampionsDoublesEnv
from teams import USER_TEAM
from teams import OPPONENT_TEAMS

BATTLE_FORMAT = "gen9championsvgc2026regmb" # Formato VGC Champions 2026 (dobles) Reglamento M-B
MODEL_NAME = "ppo_pokemon_bot" # Nombre del archivo donde se guardará el modelo entrenado


class VGCMaxBasePowerPlayer(MaxBasePowerPlayer):
    """
    Oponente que elige movimientos con la heurística de MaxBasePowerPlayer.
    De momento elegirá los pokémon en la preview en orden de escritura.
    """
    def teampreview(self, battle):
        # En VGC se deben seleccionar 4 Pokémon (ej. los 4 primeros: "/team 1234")
        return "/team 1234"
class MaskableEnvWrapper(gym.Wrapper):
    """Wrapper de Gymnasium para almacenar y exponer la máscara de acciones válidas.

    Extrae la clave 'action_mask' del diccionario de observaciones en cada turno
    y la expone a través del método `action_masks()`. Esto evita que el bot
    intente acciones ilegales (como seleccionar un movimiento sin PP, bloqueado
    por Otra Vez / Taunt, o cambiar a un Pokémon debilitado).
    """

    def reset(self, **kwargs):
        """Reinicia el entorno al comenzar un nuevo combate.

        Extrae y almacena la máscara de acciones correspondiente al primer turno.
        """
        obs, info = self.env.reset(**kwargs)
        self._last_mask = obs["action_mask"]
        return obs, info

    def step(self, action):
        """Ejecuta una acción (movimiento o cambio) en el combate.

        Actualiza la máscara con las acciones legales disponibles para el
        siguiente turno.
        """
        obs, reward, terminated, truncated, info = self.env.step(action)
        self._last_mask = obs["action_mask"]
        return obs, reward, terminated, truncated, info

    def action_masks(self):
        """Devuelve la máscara de acciones actual.

        Método requerido por librerías como `sb3-contrib` para filtrar
        las acciones inválidas antes de que la red neuronal elija una.

        Returns:
            np.ndarray: Array booleano donde True indica una acción válida.
        """
        return self._last_mask

def repair_conflicting_switches(action, mask):
    """
    Las acciones 1-6 representan "cambiar al Pokémon nº X del equipo" (ver
    DoublesEnv._action_to_order_individual). Si los dos slots piden cambiar
    al MISMO Pokémon de banca, es una combinación imposible (un jugador
    real no puede elegir eso). En vez de dejar que el simulador la rechace
    y caiga a un movimiento aleatorio, se sustituye aquí el segundo slot por
    otra opción válida de su propia máscara — preferentemente otro switch,
    y si no hay ninguno disponible, cualquier acción válida restante.
    """
    action = list(action)
    a0, a1 = int(action[0]), int(action[1])
    is_switch0 = 1 <= a0 < 7
    is_switch1 = 1 <= a1 < 7
 
    if is_switch0 and is_switch1 and a0 == a1:
        half = len(mask) // 2
        slot1_mask = mask[half:]
 
        alt_switches = [i for i in range(1, 7) if i < len(slot1_mask) and slot1_mask[i] and i != a1]
        if alt_switches:
            action[1] = alt_switches[0]
        else:
            alternatives = [i for i, valid in enumerate(slot1_mask) if valid and i != a1]
            if alternatives:
                action[1] = alternatives[0]
            # Si tampoco hay alternativa, se deja como está: strict=False
            # se encarga de ese caso extremo (no debería darse casi nunca).
 
    return action

def make_env():
    """
    Crea el entorno de combate, el oponente con el heurístico MaxBasePowerPlayer
    con el equipo elegido aleatoriamente de un diccionario de equipos. El equipo usuario
    estará definido en teams.py. Se envuelve en MaskableEnvWrapper para exponer la
    máscara de acciones válidas a la red neuronal.
    """
    selected_team = random.choice(OPPONENT_TEAMS)
    opponent = VGCMaxBasePowerPlayer(battle_format=BATTLE_FORMAT, team=USER_TEAM)

    base_env = ChampionsDoublesEnv(
        battle_format=BATTLE_FORMAT,
        team=USER_TEAM,
        strict=False, # Si se elige una acción ilegal, se reemplaza por una válida, sin crashear.
        choose_on_teampreview=False, # La red neuronal también está obligada a elegir el orden de salida en el preview, no solo los movimientos.
    )

    env = SingleAgentWrapper(base_env, opponent) # Esta función de poke-env se encarga de pedirle al oponente su acción en cada turno automáticamente, para que el agente pueda centrarse solo en su propio equipo.
    env = MaskableEnvWrapper(env)
    return Monitor(env) # Monitor de stable-baselines3 para registrar estadísticas de episodios (recompensas, duración, etc.)


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
