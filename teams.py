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
OPPONENT_TEAMS = [
# LADDERS BAJAS (1000-1300)
"""
Froslass @ Froslassite
Ability: Cursed Body
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Aurora Veil
- Blizzard
- Shadow Ball
- Protect

Sneasler @ White Herb  
Ability: Unburden  
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature 
- Fake Out  
- Close Combat  
- Dire Claw  
- Coaching  

Basculegion @ Life Orb
Ability: Adaptability
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature
- Aqua Jet
- Last Respects
- Wave Crash
- Protect

Kingambit @ Black Glasses
Ability: Defiant
EVs: 32 HP / 32 Atk / 2 SpD
Adamant Nature
- Kowtow Cleave
- Sucker Punch
- Swords Dance
- Protect 

Lycanroc-Dusk @ Focus Sash
Ability: Tough Claws
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature
- Accelerock
- Rock Slide
- Close Combat
- Protect

Scovillain @ Scovillainite
Level: 50
Ability: Moody
EVs: 32 HP / 10 Def / 24 SpD
Bold Nature
- Overheat
- Giga Drain
- Rage Powder
- Protect
""",
"""
Slowbro @ Slowbronite
Ability: Regenerator
EVs: 32 HP / 2 Def / 32 SpD
Timid Nature
- Muddy Water
- Protect
- Expanding Force
- Scald

Farigiraf @ Colbur Berry
Ability: Armor Tail
EVs: 30 HP / 24 Def / 12 SpD
Bold Nature
- Trick Room
- Psychic Terrain
- Dazzling Gleam
- Psychic

Torkoal @ Charcoal
Ability: Drought
EVs: 32 HP / 32 SpA / 2 SpD
Quiet Nature
- Protect
- Weather Ball
- Eruption
- Earth Power

Araquanid @ Leftovers
Ability: Water Bubble
EVs: 32 HP / 32 Atk / 2 Def
Brave Nature
- Rain Dance
- Infestation
- Liquidation
- Wide Guard

Torterra @ White Herb
Ability: Shell Armor
EVs: 32 HP / 32 Atk / 2 SpD
Brave Nature
- Wood Hammer
- Wide Guard 
- Headlong Rush
- Earthquake

Malamar @ Roseli Berry
Ability: Contrary
EVs: 30 HP / 28 Atk / 4 Def / 4 SpD
Timid Nature
- Trick Room
- Superpower
- Protect
- Knock Off
""",
"""
Politoed @ Sitrus Berry
Ability: Drizzle
EVs: 31 HP / 23 Def / 12 SpD
Calm Nature
- Weather Ball
- Helping Hand
- Ice Beam
- Protect

Scizor @ Scizorite
Ability: Technician
EVs: 32 HP / 32 Atk / 2 SpD
Adamant Nature
- Swords Dance
- Bullet Punch
- Protect
- Bug Bite

Gliscor @ Yache Berry
Ability: Hyper Cutter
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature
- Protect
- Tailwind
- High Horsepower
- Dual Wingbeat

Archaludon @ Leftovers
Ability: Stamina
EVs: 32 HP / 1 Def / 5 SpA / 25 SpD / 3 Spe
Modest Nature
- Electro Shot
- Dragon Pulse
- Flash Cannon
- Protect

Dragonite @ Dragon Fang
Ability: Inner Focus
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature
- Dragon Claw
- Extreme Speed
- Low Kick
- Protect

Sneasler @ White Herb  
Ability: Unburden  
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature 
- Fake Out  
- Close Combat  
- Dire Claw  
- Coaching
""",
"""
Pinsir @ Pinsirite  
Ability: Aerilate  
EVs: 2 Atk / 2 SpD / 32 Spe
Jolly Nature
- Rock Slide  
- Facade  
- Protect  
- Feint  

Araquanid @ Leftovers  
Ability: Water Bubble 
EVs: 32 HP / 32 Atk / 2 Def  
Adamant Nature
- Liquidation  
- Lunge  
- Soak  
- Wide Guard  

Whimsicott @ Fairy Feather  
Ability: Prankster  
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
- Tailwind  
- Moonblast  
- Encore  
- Protect  

Tsareena (F) @ Wide Lens  
Ability: Queenly Majesty  
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature  
- Power Whip  
- Protect  
- Triple Axel  
- Taunt  

Manectric @ Life Orb  
Ability: Lightning Rod  
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature 
- Thunderbolt  
- Snarl  
- Flamethrower  
- Protect  

Sneasler @ White Herb  
Ability: Unburden  
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature 
- Fake Out  
- Close Combat  
- Dire Claw  
- Coaching  
""",
"""
Sinistcha @ Kasib Berry
Ability: Hospitality
EVs: 32 HP / 14 Def / 20 SpD
Bold Nature
- Matcha Gotcha
- Life Dew
- Protect
- Rage Powder

Incineroar @ Sitrus Berry
Level: 50
Ability: Intimidate
EVs: 32 HP / 20 Def / 12 SpD / 2 Spe
Careful Nature
- Fake Out
- Flare Blitz
- Throat Chop
- Parting Shot

Metagross @ Metagrossite
Level: 50
Ability: Clear Body
EVs: 2 HP / 32 Atk / 32 Spe
Jolly Nature
- Psychic Fangs
- Ice Punch
- Earthquake
- Bullet Punch

Garchomp @ Life Orb
Level: 50
Ability: Rough Skin
EVs: 2 HP / 32 Atk / 32 Spe
Jolly Nature
- Swords Dance
- Scale Shot
- Earthquake
- Rock Slide

Kingambit @ Black Glasses
Level: 50
Ability: Supreme Overlord
EVs: 32 Atk / 2 Def / 32 Spe
Adamant Nature
- Swords Dance
- Kowtow Cleave
- Low Kick
- Sucker Punch

Whimsicott @ Focus Sash
Level: 50
Ability: Prankster
EVs: 18 HP / 6 Def / 10 SpA / 32 Spe
Timid Nature
- Moonblast
- Encore
- Tailwind
- Protect
""",
"""
Ceruledge (F) @ Kasib Berry 
Ability: Flash Fire
EVs: 31 HP / 25 Atk / 10 Def
Jolly Nature
Level: 50
- Bitter Blade
- Shadow Sneak
- Brick Break
- Will-O-Wisp


Ninetales-Alola (F) @ Never-Melt Ice 
Ability: Snow Warning
EVs: 1 HP / 32 SpA / 1 SpD / 32 Spe 
Timid Nature
Level: 50
- Blizzard
- Freeze-Dry
- Aurora Veil
- Roar


Milotic (F) @ Leftovers 
Ability: Competitive
EVs: 32 HP / 32 Def / 2 SpD
Bold Nature
Level: 50
- Scald
- Icy Wind
- Life Dew
- Protect


Raichu (M) @ Raichunite X 
Ability: Static
EVs: 2 Atk / 32 SpA / 32 Spe
Hasty Nature
Level: 50
- Rising Voltage
- Volt Switch
- Fake Out
- Focus Punch


Gengar @ Gengarite 
Ability: Cursed Body
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
Level: 50
- Perish Song
- Sludge Bomb
- Shadow Ball
- Protect


Incineroar @ Sitrus Berry 
Ability: Intimidate
EVs: 32 HP / 20 Def / 12 SpD / 2 Spe
Careful Nature
Level: 50
- Fake Out
- Flare Blitz
- Parting Shot
- Darkest Lariat
""",
"""
Maushold @ King's Rock 
Ability: Technician
EVs: 2 HP / 32 Atk / 32 Spe
Jolly Nature
Level: 50
- Population Bomb
- Tidy Up
- Beat Up
- Protect


Sableye (F) @ Roseli Berry 
Ability: Prankster
EVs: 32 HP / 9 Def / 25 SpD
Bold Nature
Level: 50
- Gravity
- Light Screen
- Quash
- Reflect


Gallade (M) @ Choice Scarf 
Ability: Sharpness
EVs: 2 HP / 32 Atk / 32 Spe
Jolly Nature
Level: 50
- Sacred Sword
- Triple Axel
- Leaf Blade
- Night Slash


Charizard (F) @ Charizardite Y 
Ability: Blaze
EVs: 2 HP / 32 SpA / 32 Spe
Modest Nature
Level: 50
- Dragon Pulse
- Heat Wave
- Scorching Sands
- Solar Beam


Gholdengo @ White Herb 
Ability: Good as Gold
EVs: 32 HP / 8 Def / 7 SpA / 3 SpD / 16 Spe
Modest Nature
Level: 50
- Dazzling Gleam
- Make It Rain
- Nasty Plot
- Protect


Whimsicott (F) @ Focus Sash 
Ability: Prankster
EVs: 2 HP / 32 SpA / 32 Spe
Timid Nature
Level: 50
- Moonblast
- Tailwind
- Encore
- Endeavor
""",
"""
Staraptor-Mega @ Staraptite  
Ability: Intimidate  
Level: 50  
EVs: 11 HP / 23 Atk / 32 Spe  
Jolly Nature  
- Close Combat  
- Brave Bird  
- Roost  
- Protect  

Tinkaton (F) @ Lum Berry  
Ability: Mold Breaker  
Level: 50  
EVs: 15 HP / 32 Atk / 19 Spe  
Adamant Nature  
- Fake Out  
- Encore  
- Gigaton Hammer  
- Thunder Wave  

Umbreon @ Black Glasses  
Ability: Inner Focus  
Level: 50  
EVs: 32 HP / 32 Atk / 2 SpD  
Brave Nature  
- Foul Play  
- Moonlight  
- Yawn  
- Fake Tears  

Talonflame @ Wide Lens  
Ability: Gale Wings  
Level: 50  
EVs: 7 HP / 32 Atk / 27 Spe  
Adamant Nature  
- Dual Wingbeat  
- Tailwind  
- Feather Dance  
- Taunt  

Eelektross-Mega @ Eelektrossite  
Ability: Levitate  
Level: 50  
EVs: 29 HP / 5 SpA / 32 SpD  
Quiet Nature  
- Flamethrower  
- Discharge  
- Thunderbolt  
- Rock Tomb  

Garchomp @ Choice Scarf  
Ability: Rough Skin  
Level: 50  
EVs: 2 HP / 32 Atk / 32 Spe  
Jolly Nature  
- Dragon Claw  
- Rock Tomb  
- Earthquake  
- Stomping Tantrum 
""",
"""
Swampert (M) @ Swampertite 
Ability: Damp
EVs: 10 HP / 30 Atk / 26 Spe
Adamant Nature
Level: 50
- Wave Crash
- Earthquake
- Ice Punch
- Protect


Metagross @ Metagrossite 
Ability: Clear Body
EVs: 14 HP / 25 Atk / 27 Spe
Jolly Nature
Level: 50
- Iron Head
- Body Press
- Psychic Fangs
- Protect


Grimmsnarl (M) @ Light Clay 
Ability: Prankster
EVs: 32 HP / 14 Def / 20 SpD
Calm Nature
Level: 50
- Light Screen
- Reflect
- Parting Shot
- Foul Play


Pelipper (M) @ Sitrus Berry 
Ability: Drizzle
EVs: 31 HP / 14 Def / 18 SpD / 3 Spe
Modest Nature
Level: 50
- Hurricane
- Tailwind
- Wide Guard
- Weather Ball


Sinistcha-Masterpiece @ Coba Berry 
Ability: Hospitality
EVs: 32 HP / 14 Def / 20 SpD
Relaxed Nature
Level: 50
- Matcha Gotcha
- Rage Powder
- Protect
- Trick Room


Archaludon (M) @ Leftovers 
Ability: Stamina
EVs: 32 HP / 1 Def / 5 SpA / 25 SpD / 3 Spe
Modest Nature
Level: 50
- Electro Shot
- Protect
- Dragon Pulse
- Flash Cannon
""",
"""
Ninetales-Alola @ Never-Melt Ice  
Ability: Snow Warning  
Level: 50  
EVs: 1 HP / 32 SpA / 1 SpD / 32 Spe  
Timid Nature  
- Blizzard  
- Freeze-Dry  
- Protect  
- Roar  

Raichu @ Raichunite Y  
Ability: LIghtning Rod  
Level: 50  
EVs: 30 HP / 13 Def / 23 Spe  
Timid Nature  
- Zap Cannon  
- Focus Blast  
- Protect  
- Fake Out  

Talonflame @ Sharp Beak  
Ability: Gale Wings  
Level: 50  
EVs: 2 HP / 32 Atk / 32 Spe  
Jolly Nature  
- Brave Bird  
- Flare Blitz  
- Quick Guard  
- Tailwind  

Sneasler @ White Herb  
Ability: Unburden  
Level: 50  
EVs: 2 HP / 32 Atk / 32 Spe  
Jolly Nature  
- Close Combat  
- Dire Claw  
- Quick Guard  
- Fake Out  

Tauros-Paldea-Combat (M) @ Sitrus Berry  
Ability: Intimidate  
Level: 50  
EVs: 2 HP / 32 Atk / 32 Spe  
Adamant Nature  
- Raging Bull  
- Earthquake  
- Protect  
- Rock Slide  

Houndoom @ Houndoominite  
Ability: Flash Fire  
Level: 50  
EVs: 1 HP / 32 SpA / 1 SpD / 32 Spe  
Timid Nature  
- Heat Wave  
- Dark Pulse  
- Protect  
- Nasty Plot
""",
"""
Froslass (F) @ Froslassite 
Ability: Cursed Body
EVs: 2 HP / 32 SpA / 32 Spe
Modest Nature
Level: 50
- Blizzard
- Shadow Ball
- Aurora Veil
- Protect


Scovillain (F) @ Scovillainite 
Ability: Moody
EVs: 32 HP / 10 Def / 24 SpD
Modest Nature
Level: 50
- Overheat
- Giga Drain
- Rage Powder
- Protect


Lycanroc-Dusk (F) @ Focus Sash 
Ability: Tough Claws
EVs: 2 HP / 32 Atk / 32 Spe
Adamant Nature
Level: 50
- Rock Slide
- Close Combat
- Accelerock
- Protect


Kingambit (F) @ Black Glasses 
Ability: Defiant
EVs: 32 HP / 32 Atk / 2 SpD
Adamant Nature
Level: 50
- Kowtow Cleave
- Sucker Punch
- Swords Dance
- Protect


Basculegion (M) @ Life Orb 
Ability: Adaptability
EVs: 2 HP / 32 Atk / 32 Spe
Jolly Nature
Level: 50
- Wave Crash
- Aqua Jet
- Last Respects
- Protect


Sneasler (M) @ White Herb 
Ability: Poison Touch
EVs: 2 HP / 32 Atk / 32 Spe
Jolly Nature
Level: 50
- Fake Out
- Close Combat
- Poison Jab
- Protect
"""]

