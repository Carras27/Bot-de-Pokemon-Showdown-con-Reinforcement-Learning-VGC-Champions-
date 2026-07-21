"""
Entorno de RL (Gymnasium) para Pokémon Champions VGC (dobles), usando la
API actual de poke-env: PokeEnv / DoublesEnv. Sustituye a Gen9EnvSinglePlayer,
que ya no existe en poke-env >= 0.9 aprox (y que además era solo para
singles, no dobles).
"""

import numpy as np
from gymnasium.spaces import Box
from poke_env.environment.doubles_env import DoublesEnv # API para combates dobles

# Constantes
NUM_OWN_POKEMON = 6
NUM_OPP_POKEMON = 6

# Por cada Pokémon extraemos 3 características: HP (%), debilitado (0/1), activo (0/1)
# 3*6 + 3*6 + 1 (métrica del turno actual) = 37 valores. 
OBS_SIZE = 3 * NUM_OWN_POKEMON + 3 * NUM_OPP_POKEMON + 1


class ChampionsDoublesEnv(DoublesEnv):
    """
    Entorno de Gymnasium personalizado para combates dobles en poke-env.

    Hereda de `DoublesEnv` y se encarga de:
      1. Definir el espacio de observación continuo para cada agente.
      2. Calcular la recompensa en cada turno (`calc_reward`).
      3. Vectorizar el estado del combate (`embed_battle`).
    """

    def __init__(self, *args, **kwargs):
        """
        Inicializa el entorno y configura el `observation_space` para cada agente.
        """
        super().__init__(*args, **kwargs)
        # Límites para el espacio de observación: todos los valores están normalizados entre 0 y 1.
        obs_low = np.zeros(OBS_SIZE, dtype=np.float32)
        obs_high = np.ones(OBS_SIZE, dtype=np.float32)

        # NOTA DE API: Asignamos un `Box` crudo a cada agente dentro de `self.observation_spaces`.
        # Poke-env intercepta internamente esta asignación y la envuelve automáticamente en un Dict con:
        # Dict({"observation": ..., "action_mask": ...}). Evitamos pasarle un Dict explícito aquí.
        raw_obs_space = Box(low=obs_low, high=obs_high, dtype=np.float32)
        self.observation_spaces = {agent: raw_obs_space for agent in self.possible_agents}

    def calc_reward(self, battle) -> float:
        """
        Calcula la recompensa para el agente en el estado actual del combate.
        Ponderación aplicada:
          - +2.0 por cada Pokémon enemigo debilitado.
          - +1.0 según la diferencia de porcentaje de vida (HP) a favor.
          - +0.3 por provocar/mantener estados alterados (parálisis, quemadura, etc.).
          - +30.0 bonus masivo si se consigue la victoria.
        """
        return self.reward_computing_helper(
            battle,
            fainted_value=2.0,
            hp_value=1.0,
            status_value=0.3,
            victory_value=30.0,
        )

    def embed_battle(self, battle):
        """
        Transforma el objeto `battle` de poke-env en un vector de numpy (float32) de tamaño 37.
        
        Estructura del vector resultante:
          - Índices [0:18]   -> Estado del equipo propio (6 Pokémon x 3 features).
          - Índices [18:36]  -> Estado del equipo rival (6 Pokémon x 3 features).
          - Índice  [36]     -> Progreso del turno actual (de 0.0 a 1.0).
        """

        # ---------------------------------------------------------------------
        # 1. Identificar qué Pokémon están activos actualmente en el campo
        # ---------------------------------------------------------------------
        # En dobles, `active_pokemon` puede devolver una lista o un único objeto según el estado del turno
        active_own = battle.active_pokemon
        active_own = active_own if isinstance(active_own, list) else [active_own]
        own_active_species = {mon.species for mon in active_own if mon is not None}

        active_opp = battle.opponent_active_pokemon
        active_opp = active_opp if isinstance(active_opp, list) else [active_opp]
        opp_active_species = {mon.species for mon in active_opp if mon is not None}

        # ---------------------------------------------------------------------
        # 2. Vectorizar el equipo propio (6 Pokémon x 3 características)
        # ---------------------------------------------------------------------
        own_vec = []
        # Se ordena por especie para mantener cierta consistencia en el orden de los vectores
        own_team = sorted(battle.team.values(), key=lambda m: m.species)

        for mon in own_team[:NUM_OWN_POKEMON]:
            own_vec += [
                mon.current_hp_fraction,    # % de vida restante (0.0 a 1.0)
                1.0 if mon.fainted else 0.0,    # ¿Está debilitado? (1.0 = Sí, 0.0 = No)
                1.0 if mon.species in own_active_species else 0.0,  # ¿Está activo en pista? (1.0 = Sí, 0.0 = No)
            ]
        # Padding de seguridad: si el equipo tiene menos de 6 Pokémon cargados en memoria,
        # rellena con ceros hasta alcanzar 18 valores
        while len(own_vec) < NUM_OWN_POKEMON * 3:
            own_vec += [0.0, 0.0, 0.0]

        # ---------------------------------------------------------------------
        # 3. Vectorizar el equipo rival (6 Pokémon x 3 características)
        # ---------------------------------------------------------------------
        opp_vec = []
        opp_team = list(battle.opponent_team.values())
        for mon in opp_team[:NUM_OPP_POKEMON]:
            opp_vec += [
                mon.current_hp_fraction,    # % de vida restante (0.0 a 1.0)
                1.0 if mon.fainted else 0.0,    # ¿Está debilitado? (1.0 = Sí, 0.0 = No)
                1.0 if mon.species in opp_active_species else 0.0,  # ¿Está activo en pista? (1.0 = Sí, 0.0 = No)
            ]
        # Padding de seguridad: si el equipo tiene menos de 6 Pokémon cargados en memoria,
        # rellena con ceros hasta alcanzar 18 valores
        while len(opp_vec) < NUM_OPP_POKEMON * 3:
            opp_vec += [0.0, 0.0, 0.0]

        # ---------------------------------------------------------------------
        # 4. Característica global: Duración del combate
        # ---------------------------------------------------------------------
        # Normaliza el número de turno entre 0.0 y 1.0 asumiendo un máximo de 20 turnos (regla VGC)
        turn_fraction = min(battle.turn / 20.0, 1.0)

        # ---------------------------------------------------------------------
        # 5. Concatenación final en un array de float32 de tamaño 37
        # ---------------------------------------------------------------------
        return np.array(own_vec + opp_vec + [turn_fraction], dtype=np.float32)
