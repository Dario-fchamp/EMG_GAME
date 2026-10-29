# EMG Lane Dodger

A simple pygame game controlled by two commands, LEFT and RIGHT, designed to be driven by two EMG channels through [Bonsai](https://bonsai-rx.org) over OSC. The keyboard always works too.

Dodge rocks, trees, stickmen and crashed cars, and catch stars. **Score = meters driven + 50 per star.** A Top 10 is kept.

## Run

```
conda env create -f environment.yml     # once
conda activate emg_game
python lane_dodger.py                   # keyboard only
python lane_dodger.py --input osc       # + LEFT/RIGHT from Bonsai over OSC (127.0.0.1:5005)
```

Controls: ←/→ or A/D change lane · SPACE/ENTER start · P pause · ESC back / quit.

## OSC (from Bonsai)

| Address | Argument | Effect |
|---|---|---|
| `/lanedodger/cmd` | int `1` / `2` | LEFT / RIGHT (`0` ignored) |
| `/lanedodger/left`, `/lanedodger/right` | `true` / non-zero | LEFT / RIGHT (`false` / `0` ignored) |

Example Bonsai workflow: `bonsai/LaneDodger_OscSend.bonsai`. Test without Bonsai: `python osc_test_sender.py`.

See [GAME_IDEAS.md](GAME_IDEAS.md) for the full design, code explanations and the Bonsai integration guide (section 8).
