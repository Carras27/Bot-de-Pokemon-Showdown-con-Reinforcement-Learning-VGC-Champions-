# Pokémon Showdown Bot — Setup inicial

Este proyecto arranca un servidor Showdown local y un bot en Python (con
[poke-env](https://github.com/hsahovic/poke-env)) que juega partidas de
**dobles** entre sí mismo y registra estadísticas turno a turno en SQLite.

## 1. Requisitos

- Node.js v10 o superior
- Python 3.10 o superior

## 2. Levantar el servidor Showdown local

```bash
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown
npm install
cp config/config-example.js config/config.js
node pokemon-showdown start --no-security
```

`--no-security` quita rate limiting y autenticación — perfecto para entrenar,
pero **solo úsalo en local**, nunca expuesto a internet.

Déjalo corriendo en esta terminal. Abre una segunda terminal para el bot.

## 3. Instalar el bot

```bash
python -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Ejecutar

```bash
python showdown_stats_bot.py --battles 10 --format gen9championsvgc2026regmb
```

Esto:
- Conecta dos bots aleatorios al servidor local.
- Juega 10 partidas de `gen9championsvgc2026regmb`.
- Guarda cada turno (Pokémon activos, HP de ambos equipos, etc.) y el
  resultado final de cada partida en `showdown_stats.db`.

## 5. Revisar los datos

```bash
sqlite3 showdown_stats.db
sqlite> SELECT * FROM battles;
sqlite> SELECT * FROM turns LIMIT 10;
```

=======
# Bot-de-Pokemon-Showdown-con-Reinforcement-Learning-VGC-Champions-
Un bot que pelea automáticamente en el formatd VGC de Pokémon Champions en play.pokemonshowdown.com y aprende a partir de estas partidas. Código creado en Python a partir de la biblioteca poke-env. 

