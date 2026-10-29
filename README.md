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

Controls: ←/→ or A/D change lane (arrows only with `--input osc`) · SPACE/ENTER start · P pause · ESC back / quit.

## OSC (from Bonsai)

Bonsai sends with `CreateUdpClient` (RemoteHostName `localhost`, RemotePort `5005`) → `SendMessage /mcoords`. The game understands two kinds of `/mcoords` messages:

| Message | From Bonsai | Effect |
|---|---|---|
| a key | `KeyDown A` / `KeyDown S` → `Merge` → `SendMessage` | A = LEFT, S = RIGHT (one lane per message) |
| 2 values (`ii`, `ff` or bools) | `Zip`/`CombineLatest(left, right)` → `SendMessage` | Item1 going 0 → 1 = LEFT, Item2 going 0 → 1 = RIGHT (one lane per contraction) |

Bonsai workflows: `bonsai/LaneDodger_KeyDown.bonsai` (keys A/S as stand-ins for the muscles) and `bonsai/LaneDodger_Osc.bonsai` (mouse X/Y as a stand-in). Test without Bonsai: `python osc_test_sender.py`.

See [GAME_IDEAS.md](GAME_IDEAS.md) for the full design, code explanations and the Bonsai integration guide (section 8).
