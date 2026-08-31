"""
Entorno de RL (Gymnasium) para Pokémon VGC, usando la
API poke-env.
"""

import numpy as np
import gymnasium as gym

from gymnasium.spaces import Box
from poke_env.environment.doubles_env import DoublesEnv # API para combates dobles
from poke_env.battle.pokemon_type import PokemonType
from poke_env.battle import Status, Field, Weather, SideCondition

# Diccionario para mapear los 18 (20?) tipos de Pokémon a un número único (0 a 17 (19?))
# Creo que son 20 tipos, está el 'Stellar' y el '???'
TYPE_MAP = {t: i for i, t in enumerate(PokemonType) if t is not None}

# Lista de estados alterados, no incluyo el estado debilitado.
# El estado confusión no se considera como tal.
STATUS_LIST = [Status.BRN, Status.FRZ, Status.PAR, Status.PSN,
Status.SLP, Status.TOX]

# Lista de climas.
WEATHER_LIST = [Weather.SUNNYDAY, Weather.RAINDANCE, Weather.SANDSTORM, Weather.SNOW]

# Lista de campos.
FIELD_LIST = [Field.ELECTRIC_TERRAIN, Field.GRASSY_TERRAIN, Field.MISTY_TERRAIN, Field.PSYCHIC_TERRAIN, Field.GRAVITY, Field.MAGNETIC_FIELD, Field.TRICK_ROOM]

# Lista de condiciones de bando (Side Conditions) [12]
SIDE_COND_LIST = [SideCondition.REFLECT, SideCondition.LIGHT_SCREEN, SideCondition.WIDE_GUARD,
                    SideCondition.AURORA_VEIL, SideCondition.SAFEGUARD, SideCondition.QUICK_GUARD,
                    SideCondition.MIST, SideCondition.TAILWIND, SideCondition.STEALTH_ROCK, SideCondition.STICKY_WEB,
                    SideCondition.SPIKES, SideCondition.TOXIC_SPIKES]
                  
# Constantes 
NUM_POKEMON = 6
POKEMON_OBS = 16 # Observaciones por pokémon
OBS_SIZE = 290 # Tamaño del vector de observaciones


class ChampionsDoublesEnv(DoublesEnv):
    """
    Entorno VGC Dobles con información:
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
        observations_low = np.full(OBS_SIZE, -1.0, dtype=np.float32)
        observations_high = np.full(OBS_SIZE, 1.0, dtype=np.float32)

        raw_observation_space = Box(low=observations_low, high=observations_high, dtype=np.float32)
        self.observation_spaces = {agent: raw_observation_space for agent in self.possible_agents}

        self.last_opp_hp = {}  # Para rastrear la vida rival del turno anterior

    def reset(self, *args, **kwargs):
        """
        El mismo objeto de entorno juega muchas partidas seguidas durante el
        entrenamiento (no se crea uno nuevo por partida). Asi que
        al final de cada partida nueva se reinician todos los
        valores para que no interfieran con la siguiente.
        """
        self.last_opp_hp = {}
        return super().reset(*args, **kwargs)

    # NOTA sobre Team Preview con choose_on_teampreview=True:
    # No hace falta ningún método especial aquí. poke-env reutiliza el
    # MISMO /action space de siempre: durante el Team Preview llama
    # a _choose_move(battle) DOS VECES seguidas, cada una esperando que el
    # modelo elija 2 Pokémon (uno por slot) usando los mismos índices 1-6
    # que ya se usan para switches normales.
    # get_action_mask() de DoublesEnv ya tiene su propia rama para
    # battle.teampreview.


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
        Extrae 16 características de un Pokémon.
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

        # Estado alterado: Vector con todos los estados posibles.
        # (quemadura, paralisis, etc.) 1 si le afecta, 0 si no.
        # Si todo son ceros, no hay estado. 
        status_vec = [1.0 if mon.status == s else 0.0 for s in STATUS_LIST]

        return [
            mon.current_hp_fraction,
            1.0 if mon.fainted else 0.0,
            1.0 if is_active else 0.0,
            t1,
            t2,
            *status_vec,
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

        # PPs restantes
        pp_fraction = (move.current_pp / move.max_pp) if move.max_pp > 0 else 0.0

        return [power, accuracy, cat, move_type, eff1, eff2, pp_fraction]
    
    
    def calc_reward(self, battle) -> float:
        reward = 0.0

        # 1. Recompensa por Victoria / Derrota
        if battle.won:
            return 10.0
        elif battle.lost:
            return -10.0

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
                    reward += 4.0  # Bonus por KO
            
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

        # 2. Vectorizar Equipo Propio (6 x 16 = 96 observaciones)
        own_vec = []
        own_team = sorted(battle.team.values(), key=lambda m: m.species)
        for mon in own_team[:NUM_POKEMON]:
            is_act = mon.species in own_active_species
            own_vec += self._encode_pokemon_full(mon, is_act)
        while len(own_vec) < NUM_POKEMON * POKEMON_OBS:
            own_vec += [0.0] * POKEMON_OBS

        # 3. Vectorizar Equipo Rival
        opp_vec = []
        opp_team = list(battle.opponent_team.values())
        for mon in opp_team[:NUM_POKEMON]:
            is_act = mon.species in opp_active_species
            opp_vec += self._encode_pokemon_full(mon, is_act)
        while len(opp_vec) < NUM_POKEMON * POKEMON_OBS:
            opp_vec += [0.0] * POKEMON_OBS

        # 4. Vectorizar Movimientos de tus Pokémon Activos (2 Pokémon x 4 movs x 7 datos = 56 observaciones)
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

        # 5. Clima, vector con 4 valores (Sol, Lluvia, Tormenta de Arena y Nieve)
        active_weather = set(battle.weather.keys()) if battle.weather else set()
        weather_vec = [1.0 if w in active_weather else 0.0 for w in WEATHER_LIST]

        # Campos, vector con 7 valores (Eléctrico, Hierba, Niebla, Psíquico, Gravedad, Magnético, Espacio Raro)
        active_fields = set(battle.fields.keys()) if battle.fields else set()
        fields_vec = [1.0 if f in active_fields else 0.0 for f in FIELD_LIST]
        global_vec =  weather_vec + fields_vec

        # 6. Condiciones de Bando / Side Conditions (12*2 = 24 observaciones)
        def get_side_conds(side_dict):
            names = [s.name for s in side_dict.keys()]
            return [
                1.0 if "TAILWIND" in names else 0.0,
                1.0 if "REFLECT" in names else 0.0,
                1.0 if "LIGHT_SCREEN" in names else 0.0,
                1.0 if "AURORA_VEIL" in names else 0.0,
            ]
        own_side_conds = set(battle.side_conditions.keys()) if battle.side_conditions else set()
        opp_side_conds = set(battle.opponent_side_conditions.keys()) if battle.opponent_side_conditions else set()
        own_side_vec = [1.0 if s in own_side_conds else 0.0 for s in SIDE_COND_LIST]
        opp_side_vec = [1.0 if s in opp_side_conds else 0.0 for s in SIDE_COND_LIST]
        side_vec = own_side_vec + opp_side_vec

        # 7. Megaevolución y Métrica de Turno (2 observaciones)
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
        """
        Reinicia el entorno al comenzar un nuevo combate.

        Extrae y almacena la máscara de acciones correspondiente al primer turno.
        """
        obs, info = self.env.reset(**kwargs)
        self._last_mask = obs["action_mask"]
        return obs, info

    def step(self, action):
        """Ejecuta una acción en el combate.

        Antes de enviarla al simulador, repara el caso en que los dos
        slots pidan cambiar al mismo Pokémon de banca.

        Actualiza la máscara con las acciones legales disponibles para el
        siguiente turno.
        """
        action = repair_conflicting_switches(action, self._last_mask)
        obs, reward, terminated, truncated, info = self.env.step(action)
        self._last_mask = obs["action_mask"]
        return obs, reward, terminated, truncated, info

    def action_masks(self):
        """
        Devuelve la máscara de acciones actual.

        Método requerido por librerías como `sb3-contrib` para filtrar
        las acciones inválidas antes de que la red neuronal elija una.
        """
        return self._last_mask

    def _fix_vgc_mask(self, mask):
        """
        Fuerza a False los índices de cambio de los Pokémon que 
        se quedaron en el banquillo durante el Team Preview.
        """
        env_base = self.env
        while hasattr(env_base, "env"):
            if hasattr(env_base, "current_battle"):
                break
            env_base = env_base.env
            
        battle = getattr(env_base, "current_battle", None)
        if not battle and hasattr(self.env, "agent1"):
            battle = getattr(self.env, "battle", None)

        # Si el combate no ha empezado o sigue en teampreview, no tocamos nada
        if not battle or battle.teampreview:
            return mask

        # En poke-env, los índices del 1 al 6 corresponden estrictamente
        # al orden original de los Pokémon en battle.team
        team_list = list(battle.team.values())
        
        valid_indices = []
        for i, mon in enumerate(team_list):
            # Comprobamos si el Pokémon fue seleccionado para entrar al combate
            if getattr(mon, "_selected_in_teampreview", False):
                valid_indices.append(i + 1) # +1 porque la acción 0 es 'pass'

        # La máscara contiene las acciones del slot 1 seguidas por las del slot 2
        half = len(mask) // 2
        
        # Desactivamos los índices (1 a 6) de los Pokémon baneados en ambas mitades
        for offset in [0, half]:
            for i in range(1, 7):
                if i not in valid_indices:
                    mask[offset + i] = False

        return mask


def repair_conflicting_switches(action, mask):
    """
        Repara dos combinaciones de acción imposibles en la práctica, que un
        jugador real nunca podría plantearse:
        1. Los dos slots piden cambiar al MISMO Pokémon de banca.
        2. Los dos slots piden "pass" a la vez (debe haber siempre al menos
           una acción real; "pass" en los dos solo tendría sentido si ninguno
           de los dos Pokémon pudiera actuar, algo que no ocurre en la práctica).
        En ambos casos se sustituye el segundo slot por otra opción válida de
        su propia máscara.
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
