"""
game_logic.py
Core logic for the Vault daily 4-digit code-breaking game.
Kept separate from app.py so it can be unit tested / reused (e.g. in a
notebook for the "optimal next guess" analysis) without importing Streamlit.
"""

import random
from datetime import date

CODE_LENGTH = 4
MAX_ATTEMPTS = 8


def get_daily_code(on_date: date = None) -> str:
    """
    Deterministically generate today's 4-digit code from the date, so every
    player who opens the app on the same day gets the same code (like Wordle).
    Digits can repeat.
    """
    if on_date is None:
        on_date = date.today()
    seed = int(on_date.strftime("%Y%m%d"))
    rng = random.Random(seed)
    return "".join(str(rng.randint(0, 9)) for _ in range(CODE_LENGTH))


def score_guess(guess: str, target: str) -> list:
    """
    Wordle-style scoring that correctly handles repeated digits.
    Returns a list of 4 labels: 'correct', 'present', or 'absent'.
    """
    guess = list(guess)
    target = list(target)
    result = ["absent"] * CODE_LENGTH
    remaining = {}

    # first pass: exact position matches
    for i in range(CODE_LENGTH):
        if guess[i] == target[i]:
            result[i] = "correct"
        else:
            remaining[target[i]] = remaining.get(target[i], 0) + 1

    # second pass: right digit, wrong position
    for i in range(CODE_LENGTH):
        if result[i] == "correct":
            continue
        d = guess[i]
        if remaining.get(d, 0) > 0:
            result[i] = "present"
            remaining[d] -= 1

    return result


def is_valid_guess(guess: str) -> bool:
    return guess.isdigit() and len(guess) == CODE_LENGTH


def is_win(result: list) -> bool:
    return all(r == "correct" for r in result)