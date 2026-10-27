# Contributing

Thanks for helping with Orbital Defense. Small, focused pull requests are the
easiest to review. For a bigger change, please open an issue first so we can
agree on the idea.

## Run the game and the tests

```bash
pip install -r requirements.txt
python main.py
```

The ship, enemy and projectile sprites and the audio are not in this repo. The
game still starts without them: it draws simple coloured shapes instead and
skips the sounds (see "A note on assets" in `README.md`).

There are no unit tests yet. If you add some, name the files `test_*.py` and
run them with `python -m pytest`.

The game has no headless flag. CI (`.github/workflows/tests.yml`) runs
`python -m pytest`, then starts the game in a virtual display (`xvfb-run`)
with audio off, starts a round with the placeholder sprites and renders a few
frames. It runs on every push to `main` and on every pull request.

## Add a round or an enemy (the game's "levels")

The settings are at the top of `main.py`:

- `TOTAL_ROUNDS`, `ENEMIES_ROUND_1` and `ENEMIES_PER_ROUND` control how many
  rounds there are and how many enemies each round has.
- `ENEMY_TYPES` lists each enemy: sprite, size in pixels, speed, hit radius and
  score. If you add a type, also add its number to the `random.choice` list in
  `spawn_enemy()`.

## Add a feature

- Game logic runs each frame in `Game.update()`.
- Menus, settings and pause screens are the `show_*` and `pause_*` methods.
- Pickups are made in `spawn_pickup()` and collected in `update()`.

## Add an asset

- Sprites go in `Resources/sprites/` and audio in `Resources/audio/`.
- The HP, shield and shield-sphere sprites in the repo are CC0.
- If a new sprite might be missing (for example, it is not committed), add its
  path to `EXTERNAL_ASSETS` and give it a shape and colour in `PLACEHOLDERS`,
  so the game still starts without it.

## Licence and assets

- Assets you commit must be CC0 or your own work. Please say where each asset
  comes from in your pull request.
- The code is MIT licensed (see `LICENSE`). By sending a contribution, you
  agree that it is released under the same MIT licence.
