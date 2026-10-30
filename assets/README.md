# assets

## Background music

Put a music file here named **`music.ogg`**, **`music.mp3`** or **`music.wav`** (the first one found is used), or start the game with `python lane_dodger.py --music <path>`.

- `.ogg` is the most reliable format with pygame. `.mp3` usually works; convert to `.ogg` (e.g. with Audacity) if it doesn't.
- No file = the game runs silently.
- Volume: `MUSIC_VOLUME` in `config.py`. Press **M** in the game to mute or unmute.
- Music files are **not committed to git** (see `.gitignore`), because most music is copyrighted. If you use a track whose licence allows redistribution (e.g. CC0 from opengameart.org) and want it on GitHub, remove the music line from `.gitignore`.

## Sprites (optional)

With `USE_SPRITES = True` in `config.py`, `rock.png`, `tree.png`, `stickman.png` and `crashed_car.png` from this folder replace the drawn obstacles.
