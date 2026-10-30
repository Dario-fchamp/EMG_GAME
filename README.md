# EMG Lane Dodger

A simple pygame game controlled by two commands, LEFT and RIGHT, designed to be driven by two EMG channels through [Bonsai](https://bonsai-rx.org) over OSC. The keyboard always works too.

Dodge rocks, trees, stickmen and crashed cars, and catch stars. **Score = meters driven + 50 per star.** A Top 10 is kept.

## Run

```
conda env create -f environment.yml     # once
conda activate emg_game
python lane_dodger.py                   # keyboard only
python lane_dodger.py --input osc       # + LEFT/RIGHT from Bonsai over OSC (localhost:5005)
```

Controls: ←/→ or A/D change lane (arrows only with `--input osc`) · SPACE/ENTER start · P pause · M music on/off · ESC back / quit.

Background music: put `music.ogg` (or `.mp3` / `.wav`) in `assets/`, or use `--music <file>`. Music files are not committed to git (copyright); see `assets/README.md`.

## OSC (from Bonsai)

Bonsai sends with `CreateUdpClient` (RemoteHostName `localhost`, RemotePort `5005`) → `SendMessage /mcoords`. The game understands two kinds of `/mcoords` messages:

| Message | From Bonsai | Effect |
|---|---|---|
| a key | `KeyDown A` / `KeyDown S` → `Merge` → `SendMessage` | A = LEFT, S = RIGHT (one lane per message) |
| 2 values (`ii`, `ff` or bools) | `Zip`/`CombineLatest(left, right)` → `SendMessage` | Item1 going 0 → 1 = LEFT, Item2 going 0 → 1 = RIGHT (one lane per contraction) |

The game also sends a **binary star signal** to `127.0.0.1:5006` (Bonsai's `UdpReceive`): **`/lanedodger/star`** = `0`, going to `1` for 0.1 s each time a star is caught, then back to `0`. In Bonsai, read it with `ReceiveMessage` (Address `/lanedodger/star`, TypeTag `i`).

Bonsai workflows: `bonsai/LaneDodger_KeyDown.bonsai` (keys A/S as stand-ins for the muscles) and `bonsai/LaneDodger_Osc.bonsai` (mouse X/Y as a stand-in). Test without Bonsai: `python osc_test_sender.py`.

See [GAME_IDEAS.md](GAME_IDEAS.md) for the full design, code explanations and the Bonsai integration guide (section 8).
