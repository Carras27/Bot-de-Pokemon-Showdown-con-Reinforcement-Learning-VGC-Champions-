"""
Entorno de RL (Gymnasium) para Pokémon Champions VGC (dobles), usando la
API de poke-env: PokeEnv / DoublesEnv.
"""

import numpy as np
import itertools
import gymnasium as gym

from gymnasium.spaces import Box
from poke_env.environment.doubles_env import DoublesEnv # API para combates dobles
from poke_env.battle.pokemon_type import PokemonType
from poke_env.ps_client.account_configuration import AccountConfiguration

# Genera las 360 combinaciones posibles de team preview en VGC ("1234", "1235", "2143", etc.)
VGC_TEAM_PREVIEW_COMBOS = [
    "".join(map(str, combo))
    for combo in itertools.permutations(range(1, 7), 4)
]

# Diccionario para mapear los 18 (20?) tipos de Pokémon a un número único (0 a 17 (19?))
# Creo que son 20 tipos, está el Stellar y el ???
TYPE_MAP = {t: i for i, t in enumerate(PokemonType) if t is not None}

# Constantes
NUM_OWN_POKEMON = 6
NUM_OPP_POKEMON = 6

# Tamaño del vector de observaciones (ampliable)
OBS_SIZE = 201


class ChampionsDoublesEnv(DoublesEnv):
    """
    Entorno VGC Dobles con información avanzada:
    - Tipos y Estadísticas (Boosts)
    - Clima, Campos y Condiciones de Bando (Tailwind, Screens, Trick Room)
    - Datos de Movimientos y Efectividad de tipos
    - Estado de Megaevolución (no Teracristalización)
    """

    def __init__(self, *args, **kwargs):
        """
        Inicializa el entorno y configura el `observation_space` para cada agente.
        """
        super().__init__(*args, **kwargs)
        # Los boosts de estadísticas pueden ir de -1.0 a 1.0, por eso el límite inferior es -1.0
        obs_low = np.full(OBS_SIZE, -1.0, dtype=np.float32)
        obs_high = np.full(OBS_SIZE, 1.0, dtype=np.float32)

        raw_obs_space = Box(low=obs_low, high=obs_high, dtype=np.float32)
        self.observation_spaces = {agent: raw_obs_space for agent in self.possible_agents}

        self.last_opp_hp = {}  # Para rastrear la vida rival del turno anterior

    def reset(self, *args, **kwargs):
        """
        El mismo objeto de entorno juega muchas partidas seguidas durante el
        entrenamiento (no se crea uno nuevo por partida). Sin este reset,
        last_opp_hp seguía teniendo el HP final de la partida ANTERIOR, así
        que en el primer turno de cada partida nueva se comparaba ese HP
        residual contra el 100% inicial real, generando una recompensa
        falsa (un pico de "daño causado" que nunca ocurrió).
        """
        self.last_opp_hp = {}
        return super().reset(*args, **kwargs)

    # -------------------------------------------------------------------
    # MÉTODOS PARA TEAM PREVIEW
    # -------------------------------------------------------------------
    def teampreview_action_to_string(self, action: int, battle=None) -> str:
        """
        Poke-env llama a este método automáticamente durante el turno 0
        para convertir la acción numérica elegida por la IA en un comando `/team XXXX`.
        """
        combo_idx = action % len(VGC_TEAM_PREVIEW_COMBOS)
        order_str = VGC_TEAM_PREVIEW_COMBOS[combo_idx] # Calcula aleatoriamente el orden de salida de los 4 Pokémon elegidos en Team Preview
        return f"/team {order_str}"

    def action_masks(self, *args, **kwargs) -> np.ndarray:
        """
        Genera la máscara de acciones diferenciando si estamos en Team Preview (Turno 0)
        o en combate normal (Turnos 1+).
        """
        # Obtenemos la batalla actual desde el propio entorno de poke-env
        battle = getattr(self, "current_battle", None)

        # CASO 1: Turno 0 (Team Preview)
        if battle and getattr(battle, "teampreview", False):
            mask = np.zeros(self.action_space.n, dtype=bool)
            # Habilitamos únicamente las opciones asignadas a Team Preview
            max_combos = min(len(VGC_TEAM_PREVIEW_COMBOS), self.action_space.n)
            mask[:max_combos] = True
            return mask

        # CASO 2: Combate normal
        # Si DoublesEnv ya provee action_masks, la llamamos; si no, permitimos las acciones del espacio
        if hasattr(super(), "action_masks"):
            return super().action_masks(*args, **kwargs)

        return np.ones(self.action_space.n, dtype=bool)



    # -------------------------------------------------------------------
    # MÉTODOS DE OBSERVACIÓN Y RECOMPENSA
    # -------------------------------------------------------------------
    def _encode_type(self, pokemon_type) -> float:
        """Convierte un PokemonType a un float entre 0.0 y 1.0."""
        if pokemon_type in TYPE_MAP:
            return TYPE_MAP[pokemon_type] / 18.0
        return 0.0
    
    def _encode_pokemon_full(self, mon, is_active: bool) -> list:
        """
        Extrae 11 características de un Pokémon.
        Acitvo/No, Debilitado/No, Tipo(s), estadísticas (boosts) y estados alterados.
        """
        if mon is None:
            return [0.0] * 11

        # Tipos
        t1 = self._encode_type(mon.type_1)
        t2 = self._encode_type(mon.type_2)

        # Modificadores de Estadísticas (Boosts: Atk, Def, SpA, SpD, Spe) de -6 a +6 -> [-1.0, 1.0]
        boosts = mon.boosts if is_active else {'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0}
        b_atk = boosts.get('atk', 0) / 6.0
        b_def = boosts.get('def', 0) / 6.0
        b_spa = boosts.get('spa', 0) / 6.0
        b_spd = boosts.get('spd', 0) / 6.0
        b_spe = boosts.get('spe', 0) / 6.0

        # Estado alterado (0.0 = ninguno, 1.0 = quemado, paralizado, etc.)
        status = 1.0 if mon.status is not None else 0.0

        return [
            mon.current_hp_fraction,
            1.0 if mon.fainted else 0.0,
            1.0 if is_active else 0.0,
            t1,
            t2,
            status,
            b_atk,
            b_def,
            b_spa,
            b_spd,
            b_spe,
        ]

    def _encode_move(self, move, own_mon, opp_actives) -> list:
        """Extrae 7 características de un movimiento, incluyendo efectividad vs rivales."""
        if move is None:
            return [0.0] * 7

        power = (move.base_power or 0) / 250.0
        accuracy = (move.accuracy or 100) / 100.0 if isinstance(move.accuracy, (int, float)) else 1.0
        
        # Categoría: Físico = 1.0, Especial = -1.0, Estado = 0.0
        cat = 0.0
        if move.category:
            if move.category.name == "PHYSICAL":
                cat = 1.0
            elif move.category.name == "SPECIAL":
                cat = -1.0

        move_type = self._encode_type(move.type)

        # Efectividad contra los 2 Pokémon rivales activos en pista
        eff1, eff2 = 0.0, 0.0
        if len(opp_actives) > 0 and opp_actives[0] is not None:
            eff1 = opp_actives[0].damage_multiplier(move) / 4.0
        if len(opp_actives) > 1 and opp_actives[1] is not None:
            eff2 = opp_actives[1].damage_multiplier(move) / 4.0

        pp_fraction = (move.current_pp / move.max_pp) if move.max_pp > 0 else 0.0

        return [power, accuracy, cat, move_type, eff1, eff2, pp_fraction]
    
    
    def calc_reward(self, battle) -> float:
        reward = 0.0

        # 1. Recompensa por Victoria / Derrota
        if battle.won:
            return 5.0
        elif battle.lost:
            return -5.0

        # 2. Calcular daño infligido y KOs en este turno
        for mon_key, mon in battle.opponent_team.items():
            prev_hp = self.last_opp_hp.get(mon_key, mon.current_hp_fraction)
            curr_hp = mon.current_hp_fraction
            
            hp_diff = prev_hp - curr_hp
            
            if hp_diff > 0:
                # Recompensa proporcional al daño causado
                reward += hp_diff * 2.0  
                
                # Bonus si el golpe provocó el debilitamiento (KO directo)
                if mon.fainted and prev_hp > 0:
                    reward += 3.0  # Bonus por KO
            
            # Actualizar historial de HP
            self.last_opp_hp[mon_key] = curr_hp

        # 3. Pequeña penalización por paso de turno (para incentivar terminar rápido)
        reward -= 0.05

        return reward

    def embed_battle(self, battle) -> np.ndarray:
        # 1. Identificar Pokémon activos en pista
        active_own = battle.active_pokemon if isinstance(battle.active_pokemon, list) else [battle.active_pokemon]
        active_own = [m for m in active_own if m is not None]

        active_opp = battle.opponent_active_pokemon if isinstance(battle.opponent_active_pokemon, list) else [battle.opponent_active_pokemon]
        active_opp = [m for m in active_opp if m is not None]

        own_active_species = {m.species for m in active_own}
        opp_active_species = {m.species for m in active_opp}

        # 2. Vectorizar Equipo Propio (6 x 11 = 66 features)
        own_vec = []
        own_team = sorted(battle.team.values(), key=lambda m: m.species)
        for mon in own_team[:6]:
            is_act = mon.species in own_active_species
            own_vec += self._encode_pokemon_full(mon, is_act)
        while len(own_vec) < 6 * 11:
            own_vec += [0.0] * 11

        # 3. Vectorizar Equipo Rival (6 x 11 = 66 features)
        opp_vec = []
        opp_team = list(battle.opponent_team.values())
        for mon in opp_team[:6]:
            is_act = mon.species in opp_active_species
            opp_vec += self._encode_pokemon_full(mon, is_act)
        while len(opp_vec) < 6 * 11:
            opp_vec += [0.0] * 11

        # 4. Vectorizar Movimientos de tus Pokémon Activos (2 Pokémon x 4 movs x 7 datos = 56 features)
        moves_vec = []
        for slot in range(2):
            if slot < len(active_own) and active_own[slot] is not None:
                mon = active_own[slot]
                moves = list(mon.moves.values())[:4]
                for move in moves:
                    moves_vec += self._encode_move(move, mon, active_opp)
                while len(moves_vec) < (slot + 1) * 28:
                    moves_vec += [0.0] * 7
            else:
                moves_vec += [0.0] * 28

        # 5. Clima, Campos y Espacio Raro (3 features)
        weather_val = 1.0 if battle.weather else 0.0
        fields_val = 1.0 if battle.fields else 0.0
        trick_room = 1.0 if "TRICK_ROOM" in [f.name for f in battle.fields] else 0.0
        global_vec = [weather_val, fields_val, trick_room]

        # 6. Condiciones de Bando / Side Conditions (8 features)
        # (Tailwind / Viento Afín, Reflect, Light Screen, Aurora Veil)
        def get_side_conds(side_dict):
            names = [s.name for s in side_dict.keys()]
            return [
                1.0 if "TAILWIND" in names else 0.0,
                1.0 if "REFLECT" in names else 0.0,
                1.0 if "LIGHT_SCREEN" in names else 0.0,
                1.0 if "AURORA_VEIL" in names else 0.0,
            ]

        own_side = get_side_conds(battle.side_conditions)
        opp_side = get_side_conds(battle.opponent_side_conditions)
        side_vec = own_side + opp_side

        # 7. Megaevolución y Métrica de Turno (2 features)
        can_mega = 1.0 if battle.can_mega_evolve else 0.0
        turn_frac = min(battle.turn / 20.0, 1.0)
        misc_vec = [can_mega, turn_frac]

        # Unir todas las partes
        full_obs = own_vec + opp_vec + moves_vec + global_vec + side_vec + misc_vec
        return np.array(full_obs, dtype=np.float32)

class MaskableEnvWrapper(gym.Wrapper):
    """
    Wrapper de Gymnasium para almacenar y exponer la máscara de acciones válidas.

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

        Antes de enviarla al simulador, repara el caso en que los dos
        slots pidan cambiar al mismo Pokémon de banca (una combinación
        imposible que ningún jugador real podría plantearse siquiera).

        Actualiza la máscara con las acciones legales disponibles para el
        siguiente turno.
        """
        action = repair_conflicting_switches(action, self._last_mask)
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
    Evita que los dos slots pidan cambiar al MISMO Pokémon de banca, 
    sustituyendo el segundo slot por otra opción válida.
    Además, repara que los dos slots pidan 'pass' al mismo tiempo. Esto solo tendría sentido
    si ninguno de los dos pokémon pudiese actuar, cosa que no pasa en una partida real.
    """
    original_dtype = np.asarray(action).dtype
    action = list(action)
    a0, a1 = int(action[0]), int(action[1])
    is_switch0 = 1 <= a0 < 7
    is_switch1 = 1 <= a1 < 7

    
    half = len(mask) // 2
    slot1_mask = mask[half:]

    conflict_same_switch = is_switch0 and is_switch1 and a0 == a1
    conflict_double_pass = a0 == 0 and a1 == 0
 
    if conflict_same_switch:
        alt_switches = [i for i in range(1, 7) if i < len(slot1_mask) and slot1_mask[i] and i != a1]
        if alt_switches:
            action[1] = alt_switches[0]
        else:
            alternatives = [i for i, valid in enumerate(slot1_mask) if valid and i != a1]
            if alternatives:
                action[1] = alternatives[0]
            # Si tampoco hay alternativa, se deja como está: strict=False
            # se encarga de ese caso extremo (no debería darse casi nunca).
    elif conflict_double_pass:
        alternatives = [i for i, valid in enumerate(slot1_mask) if valid and i != 0]
        if alternatives:
            action[1] = alternatives[0]
        # Si tampoco hay alternativa (caso extremo), se deja como está.
 
    # IMPORTANTE: poke-env llama a action[i].item() esperando un escalar de
    # numpy, no un int de Python normal — por eso se devuelve como array,
    # no como lista, conservando el dtype original.
    return np.array(action, dtype=original_dtype)
    
