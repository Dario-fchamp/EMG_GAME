"""Top-10 scores, saved as JSON next to the scripts (works whatever the working directory).

Entry: {"name", "score", "meters", "stars", "date"}, ranked by score = meters + STAR_POINTS * stars.
"""
import json
import os
import tempfile
from datetime import datetime

import config as C


def path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), C.HIGHSCORE_FILE)


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _normalize(e):
    """Return a clean entry, or None if invalid. Entries from before stars existed get score = meters."""
    if not (isinstance(e, dict) and isinstance(e.get("name"), str) and _is_int(e.get("meters"))):
        return None
    stars = e.get("stars", 0) if _is_int(e.get("stars", 0)) else 0
    score = e.get("score") if _is_int(e.get("score")) else e["meters"] + C.STAR_POINTS * stars
    return {"name": e["name"][:C.NAME_MAX_LEN], "score": score, "meters": e["meters"],
            "stars": stars, "date": str(e.get("date", ""))}


def load():
    """Return the scores sorted best first. A missing or corrupt file gives an empty list."""
    p = path()
    if not os.path.exists(p):
        return []
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError) as e:
        print(f"Warning: could not read {p} ({e}). Starting with an empty Top {C.N_HIGHSCORES}.")
        return []
    if not isinstance(data, list):
        print(f"Warning: unexpected content in {p}. Starting with an empty Top {C.N_HIGHSCORES}.")
        return []
    scores = [n for n in map(_normalize, data) if n is not None]
    scores.sort(key=lambda e: -e["score"])      # stable: ties keep their order
    return scores[:C.N_HIGHSCORES]


def rank_for(scores, score):
    """0-based rank a new score would get. Ties: the older entry stays above."""
    return sum(1 for e in scores if e["score"] >= score)


def qualifies(scores, score):
    return score > 0 and rank_for(scores, score) < C.N_HIGHSCORES


def insert(scores, name, score, meters, stars):
    """Return (new_scores, rank). rank is 0-based, or None if the entry did not make the list."""
    entry = {"name": (name or C.DEFAULT_NAME)[:C.NAME_MAX_LEN],
             "score": score, "meters": meters, "stars": stars,
             "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
    new_scores = sorted(scores + [entry], key=lambda e: -e["score"])[:C.N_HIGHSCORES]
    rank = next((i for i, e in enumerate(new_scores) if e is entry), None)
    return new_scores, rank


def save(scores):
    """Atomic write (temp file + replace), so a crash never leaves a corrupt file."""
    p = path()
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2, ensure_ascii=False)
        os.replace(tmp, p)
    except OSError as e:
        print(f"Warning: could not save high scores to {p} ({e}).")
