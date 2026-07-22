# teams.py

# Habrá un solo equipo USER_TEAM, que es el que entrenaremos y evaluaremos.
# Se puede cambiar a cualquier otro equipo válido de Showdown.
USER_TEAM = """
Aerodactyl @ Aerodactylite  
Ability: Unnerve  
Level: 50  
EVs: 2 HP / 32 Atk / 32 Spe  
Jolly Nature  
- Protect  
- Dual Wingbeat  
- Rock Slide  
- Tailwind  

Meowscarada @ Choice Scarf  
Ability: Protean  
Level: 50  
EVs: 2 HP / 32 Atk / 32 Spe  
Jolly Nature  
- Flower Trick  
- Knock Off  
- U-turn  
- Triple Axel

Gyarados @ Focus Sash  
Ability: Intimidate  
Level: 50  
EVs: 2 HP / 32 Atk / 32 Spe  
Jolly Nature  
- Waterfall  
- Earthquake  
- Ice Fang  
- Dragon Dance  

Hippowdon @ Sitrus Berry  
Ability: Sand Stream  
Level: 50  
EVs: 32 HP / 32 Def / 2 SpD  
Impish Nature  
- Earthquake  
- Slack Off  
- Yawn  
- Stealth Rock  

Archaludon @ Leftovers  
Ability: Stamina  
Level: 50  
EVs: 32 HP / 2 Def / 32 SpD  
Calm Nature  
- Thunderbolt  
- Draco Meteor  
- Stealth Rock  
- Roar  

Primarina @ Mystic Water  
Ability: Torrent  
Level: 50  
EVs: 32 HP / 32 SpA / 2 Spe  
Modest Nature  
- Sparkling Aria  
- Aqua Jet  
- Flip Turn  
- Moonblast  
"""
# Se guardarán varios equipos de oponentes en OPPONENT_TEAMS,
# y el agente entrenará y evaluará contra un equipo elegido aleatoriamente de este diccionario.
OPPONENT_TEAMS = ["""
Kangaskhan-Mega @ Kangaskhanite
Ability: Scrappy
EVs: 2 HP / 32 Atk / 32 Spe
Jolly Nature
- Fake Out
- Double-Edge
- Sucker Punch
- Low Kick

Starmie @ Leftovers
Ability: Natural Cure
EVs: 32 SpA / 2 Def / 32 Spe
Timid Nature
- Surf
- Ice Beam
- Recover
- Rapid Spin

Arcanine @ Quick Claw
Ability: Intimidate
EVs: 32 HP / 2 Atk / 32 Spe
Jolly Nature
- Flare Blitz
- Extreme Speed
- Will-O-Wisp
- Morning Sun

Clefable @ Sitrus Berry
Ability: Unaware
EVs: 32 HP / 32 Def / 2 SpD
Bold Nature
- Moonblast
- Helping Hand
- Thunder Wave
- Stealth Rock

Alakazam @ Focus Sash
Ability: Magic Guard
EVs: 32 SpA / 2 SpD / 32 Spe
Timid Nature
- Psychic
- Shadow Ball
- Encore
- Focus Blast

Tauros-Paldea-Blaze @ Choice Scarf
Ability: Cud Chew
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Raging Bull
- Close Combat
- Flare Blitz
- Earthquake
""",
"""
Charizard @ Charizardite Y
Ability: Blaze
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Fire Blast
- Solar Beam
- Air Slash
- Roost

Venusaur @ Life Orb
Ability: Chlorophyll
EVs: 32 SpA / 2 SpD / 32 Spe
Timid Nature
- Giga Drain
- Sludge Bomb
- Earth Power
- Sleep Powder

Arcanine-Hisui @ Black Belt
Ability: Rock Head
EVs: 32 Atk / 2 Def / 32 Spe
Adamant Nature
- Head Smash
- Flare Blitz
- Extreme Speed
- Close Combat

Starmie @ Leftovers
Ability: Natural Cure
EVs: 32 SpA / 2 Def / 32 Spe
Timid Nature
- Surf
- Recover
- Rapid Spin
- Ice Beam

Clefable @ Sitrus Berry
Ability: Unaware
EVs: 32 HP / 32 Def / 2 SpD
Bold Nature
- Moonblast
- Stealth Rock
- Helping Hand
- Thunder Wave

Raichu-Alola @ Focus Sash
Ability: Surge Surfer
EVs: 32 SpA / 2 SpD / 32 Spe
Timid Nature
- Thunderbolt
- Grass Knot
- Encore
- Nasty Plot
""",
"""
Gengar @ Gengarite
Ability: Cursed Body
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Shadow Ball
- Sludge Bomb
- Focus Blast
- Destiny Bond

Machamp @ Quick Claw
Ability: No Guard
EVs: 32 HP / 32 Atk / 2 Def
Adamant Nature
- Dynamic Punch
- Knock Off
- Bullet Punch
- Ice Punch

Pidgeot-Mega @ Pidgeotite
Ability: No Guard
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Hurricane
- Heat Wave
- U-turn
- Roost

Starmie @ Leftovers
Ability: Natural Cure
EVs: 32 SpA / 2 Def / 32 Spe
Timid Nature
- Surf
- Recover
- Rapid Spin
- Thunderbolt

Ninetales-Alola @ Light Clay
Ability: Snow Warning
EVs: 32 HP / 2 SpD / 32 Spe
Timid Nature
- Aurora Veil
- Freeze-Dry
- Encore
- Moonblast

Tauros @ Choice Scarf
Ability: Intimidate
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Body Slam
- Earthquake
- Rock Slide
- Close Combat
""",
"""
Tyranitar @ Tyranitarite
Ability: Sand Stream
EVs: 32 HP / 32 Atk / 2 SpD
Adamant Nature
- Rock Slide
- Knock Off
- Low Kick
- Dragon Dance

Excadrill @ Life Orb
Ability: Sand Rush
EVs: 32 Atk / 2 Def / 32 Spe
Jolly Nature
- Earthquake
- Iron Head
- Rock Slide
- Protect

Rotom-Wash @ Sitrus Berry
Ability: Levitate
EVs: 32 HP / 22 Def / 12 SpD
Bold Nature
- Hydro Pump
- Volt Switch
- Will-O-Wisp
- Protect

Corviknight @ Leftovers
Ability: Mirror Armor
EVs: 32 HP / 22 Def / 12 SpD
Impish Nature
- Brave Bird
- Body Press
- Roost
- U-turn

Sinistcha @ Occa Berry
Ability: Hospitality
EVs: 32 HP / 20 Def / 14 SpD
Bold Nature
- Matcha Gotcha
- Rage Powder
- Strength Sap
- Trick Room

Primarina @ Mystic Water
Ability: Torrent
EVs: 32 HP / 32 SpA / 2 SpD
Modest Nature
- Moonblast
- Hydro Pump
- Ice Beam
- Psychic Noise
"""]

