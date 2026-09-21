"""
Central configuration for the signal bot.
All values come from environment variables (set these on Render).
"""
import os

# --- Deriv API ---
DERIV_APP_ID = os.getenv("DERIV_APP_ID", "1089")  # 1089 is Deriv's public demo app_id
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "")  # your account's API token (read-only is enough)
DERIV_WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}"

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # your chat/channel id

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signal_bot.db")  # Render will inject the real Postgres URL

# --- Watchlist ---
# Deriv symbol codes. Mix of forex majors + synthetic indices.
# Adjust freely -- these are just a sensible starting set.
WATCHLIST = [
    # Forex majors/crosses
    "frxEURUSD",
    "frxGBPUSD",
    "frxEURGBP",
    "frxUSDJPY",
    "frxAUDUSD",
    # Synthetic indices
    "R_10",
    "R_25",
    "R_50",
    "R_75",
    "R_100",
]

# --- Timeframes (Deriv granularity in seconds) ---
HTF_GRANULARITY = 14400   # 4H -- used for trend + key levels
LTF_GRANULARITY = 3600    # 1H -- used for pattern detection / entries
CANDLES_TO_FETCH = 200    # how many candles to pull per request (need enough history for swings/MA/Fib)

# --- Strategy constants (from the Candlestick Trading Bible) ---
MA_FAST = 8
MA_SLOW = 21
FIB_LEVELS = (0.5, 0.618)
FIB_TOLERANCE = 0.003        # price must be within 0.3% of a fib level to "count"
LEVEL_TOLERANCE = 0.0015     # price must be within 0.15% of an S/R level to "count"
MIN_RR = 2.0                 # reject any setup with reward:risk below this
SWING_LOOKBACK = 5           # bars on each side to confirm a swing high/low
MIN_TOUCHES_FOR_RANGE = 2    # touches needed on each boundary to call a market "ranging"

# --- Confluence / signal policy ---
STRICT_CONFLUENCE = True     # require Trend + Level + Signal to all align (locked decision)
BEST_OF_ONLY = True          # only ever alert the single top-ranked setup per scan cycle (locked decision)

# --- SL/TP confirmation ---
CLOSE_CONFIRMATION_ONLY = True  # SL/TP only counts as hit on a candle CLOSE beyond the level (locked decision)
