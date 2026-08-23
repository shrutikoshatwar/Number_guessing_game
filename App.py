"""
app.py
Streamlit frontend for VAULT - a daily 4-digit code-breaking game.
Every guess is logged to a CSV with pandas so the sidebar can show
real stats (win rate, average attempts, attempt distribution chart).
"""

import os
from datetime import date, datetime

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from game_logic import (
    CODE_LENGTH,
    MAX_ATTEMPTS,
    get_daily_code,
    score_guess,
    is_valid_guess,
    is_win,
)

LOG_PATH = "vault_log.csv"

COLORS = {
    "correct": "#4C8C5E",
    "present": "#C9932F",
    "absent": "#242830",
}
BORDER = {
    "correct": "#6FB582",
    "present": "#E4B04C",
    "absent": "#343A44",
}

# ---------------------------------------------------------------- utilities

def load_log() -> pd.DataFrame:
    if os.path.exists(LOG_PATH):
        return pd.read_csv(LOG_PATH)
    return pd.DataFrame(
        columns=["timestamp", "date", "attempt_number", "guess", "feedback", "game_result"]
    )


def append_log(row: dict):
    df = load_log()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(LOG_PATH, index=False)


def render_row(guess: str, result: list, active: bool = False) -> str:
    boxes = ""
    for i in range(CODE_LENGTH):
        digit = guess[i] if i < len(guess) else ""
        state = result[i] if result else None
        bg = COLORS.get(state, "#181C23")
        border = BORDER.get(state, "#C9A24B" if active else "#2A2F38")
        color = "#EDEBE3" if state != "present" else "#1A1206"
        boxes += (
            f'<div style="width:52px;height:52px;background:{bg};'
            f'border:2px solid {border};color:{color};display:flex;'
            f'align-items:center;justify-content:center;font-family:monospace;'
            f'font-size:24px;font-weight:700;border-radius:6px;">{digit}</div>'
        )
    return f'<div style="display:flex;gap:8px;margin-bottom:8px;">{boxes}</div>'


# ---------------------------------------------------------------- page setup

st.set_page_config(page_title="Vault — Daily Code Breaker", page_icon="🔒", layout="centered")

st.markdown(
    """
    <style>
    .stApp { background-color: #12151A; color: #EDEBE3; }
    div[data-testid="stForm"] { border: none; padding: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("## 🔒 VAULT")
st.caption(f"Today's combination · {date.today().isoformat()}")

# ---------------------------------------------------------------- game state

today_str = date.today().isoformat()
target = get_daily_code()

if "rows" not in st.session_state or st.session_state.get("game_date") != today_str:
    st.session_state.rows = []  # list of (guess, result)
    st.session_state.status = "playing"  # playing | won | lost
    st.session_state.game_date = today_str

# ---------------------------------------------------------------- grid

for guess, result in st.session_state.rows:
    st.markdown(render_row(guess, result), unsafe_allow_html=True)

if st.session_state.status == "playing":
    st.markdown(render_row("", None, active=True), unsafe_allow_html=True)

for _ in range(MAX_ATTEMPTS - len(st.session_state.rows) - (1 if st.session_state.status == "playing" else 0)):
    st.markdown(render_row("", None), unsafe_allow_html=True)

st.write(f"Attempts used: **{len(st.session_state.rows)} / {MAX_ATTEMPTS}**")

# ---------------------------------------------------------------- input

if st.session_state.status == "playing":
    with st.form("guess_form", clear_on_submit=True):
        guess = st.text_input("Enter a 4-digit guess", max_chars=4, placeholder="e.g. 5890")
        submitted = st.form_submit_button("UNLOCK ⏎")

    if submitted:
        if not is_valid_guess(guess):
            st.error("Enter exactly 4 digits (0-9).")
        else:
            result = score_guess(guess, target)
            st.session_state.rows.append((guess, result))

            won = is_win(result)
            lost = (not won) and len(st.session_state.rows) >= MAX_ATTEMPTS
            game_result = "won" if won else ("lost" if lost else "ongoing")
            if won or lost:
                st.session_state.status = "won" if won else "lost"

            append_log(
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "date": today_str,
                    "attempt_number": len(st.session_state.rows),
                    "guess": guess,
                    "feedback": "".join(r[0].upper() for r in result),
                    "game_result": game_result,
                }
            )
            st.rerun()

elif st.session_state.status == "won":
    st.success(f"Vault cracked in {len(st.session_state.rows)} tries! Come back tomorrow.")
else:
    st.error(f"Out of attempts. Today's code was **{target}**. Try again tomorrow.")

# ---------------------------------------------------------------- stats sidebar

with st.sidebar:
    st.markdown("### 📊 Your Stats")
    log = load_log()

    if log.empty:
        st.write("No games logged yet — play a round!")
    else:
        # one row per finished game: the last logged attempt for that date
        finished = log[log["game_result"].isin(["won", "lost"])]
        games = finished.sort_values("attempt_number").groupby("date").tail(1)

        total_games = len(games)
        wins = (games["game_result"] == "won").sum()
        win_rate = (wins / total_games * 100) if total_games else 0
        avg_attempts = games.loc[games["game_result"] == "won", "attempt_number"].mean()

        col1, col2 = st.columns(2)
        col1.metric("Games played", total_games)
        col2.metric("Win rate", f"{win_rate:.0f}%")
        if pd.notna(avg_attempts):
            st.metric("Avg. attempts to solve", f"{avg_attempts:.1f}")

        if wins > 0:
            fig, ax = plt.subplots(figsize=(4, 2.5))
            won_games = games[games["game_result"] == "won"]
            ax.hist(
                won_games["attempt_number"],
                bins=range(1, MAX_ATTEMPTS + 2),
                color="#C9A24B",
                edgecolor="#12151A",
                align="left",
            )
            ax.set_xlabel("Attempts to solve")
            ax.set_ylabel("Games")
            ax.set_facecolor("#181C23")
            fig.patch.set_facecolor("#12151A")
            ax.tick_params(colors="#EDEBE3")
            ax.xaxis.label.set_color("#EDEBE3")
            ax.yaxis.label.set_color("#EDEBE3")
            for spine in ax.spines.values():
                spine.set_color("#2A2F38")
            st.pyplot(fig)

    st.divider()
    st.caption("How to play")
    st.markdown(
        "- 🟩 Right digit, right position\n"
        "- 🟨 Right digit, wrong position\n"
        "- ⬛ Digit isn't in the code\n\n"
        "Digits can repeat. A new code is set every day."
    )