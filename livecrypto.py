import time
import requests
from datetime import datetime
import pyttsx3

TV_SCAN_URL = "https://scanner.tradingview.com/crypto/scan"

# --- Speech settings ---
SPEAK_EVERY_TICK = True     # speak on every update
SPEAK_ON_CHANGE_ONLY = False # set True to speak only when price changes
CHANGE_THRESHOLD_PCT = 0.01  # if SPEAK_ON_CHANGE_ONLY, speak when abs % change since last spoken >= this
VOICE_RATE_WPM = 180         # speed; ~150-200 is natural
# ------------------------

def tts_engine():
    eng = pyttsx3.init()  # Windows uses SAPI5
    eng.setProperty("rate", VOICE_RATE_WPM)
    return eng

def speak(engine, text):
    engine.say(text)
    engine.runAndWait()

def fetch_fields(ticker: str, columns=None):
    if columns is None:
        # add fields you like; close = last price
        columns = ["name", "close", "change", "change_abs", "volume"]

    payload = {
        "symbols": {"tickers": [ticker], "query": {"types": []}},
        "columns": columns,
        "range": [0, 1]
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.tradingview.com/"
    }
    r = requests.post(TV_SCAN_URL, json=payload, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    rows = data.get("data", [])
    if not rows:
        return None
    values = rows[0].get("d", [])
    return {col: (values[i] if i < len(values) else None) for i, col in enumerate(columns)}

def stream_price(ticker: str, interval_sec: int = 3):
    engine = tts_engine()
    last_spoken_price = None

    print(f"Polling TradingView for {ticker} every {interval_sec}s. Ctrl+C to stop.")
    while True:
        try:
            row = fetch_fields(ticker)
            if not row:
                print("No data returned (check ticker like 'BINANCE:BTCUSDT').")
            else:
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                name = row.get("name", ticker)
                close = row.get("close")
                chg = row.get("change")
                chg_abs = row.get("change_abs")
                vol = row.get("volume")

                # Pretty print
                extra = []
                if isinstance(chg, (int, float)): extra.append(f"{chg:.2f}%")
                if isinstance(chg_abs, (int, float)): extra.append(f"{chg_abs}")
                if isinstance(vol, (int, float)): extra.append(f"vol {int(vol)}")
                print(f"[{now}] {name}: {close}  ({', '.join(extra)})")

                # Speak logic
                should_speak = False
                if SPEAK_EVERY_TICK:
                    should_speak = True
                elif SPEAK_ON_CHANGE_ONLY and isinstance(close, (int, float)) and isinstance(last_spoken_price, (int, float)):
                    pct = abs((close - last_spoken_price) / last_spoken_price) * 100 if last_spoken_price else 100.0
                    if pct >= CHANGE_THRESHOLD_PCT:
                        should_speak = True
                elif SPEAK_ON_CHANGE_ONLY and last_spoken_price is None:
                    should_speak = True  # first time

                if should_speak:
                    # Build a natural sentence
                    price_str = f"{float(close):,.2f}" if isinstance(close, (int, float)) else str(close)
                    # If we have % change, add it
                    if isinstance(chg, (int, float)):
                        phrase = f"{name} price {price_str}. Change {chg:.2f} percent."
                    else:
                        phrase = f"{name} price {price_str}."
                    speak(engine, phrase)
                    if isinstance(close, (int, float)):
                        last_spoken_price = close

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Error: {e}. Retrying in 5s…")
            time.sleep(5)
            continue

        time.sleep(interval_sec)

if __name__ == "__main__":
    # Example: BINANCE:BTCUSDT  |  COINBASE:ETHUSD  |  BYBIT:SOLUSDT
    stream_price("BINANCE:LTCUSDT", interval_sec=3)
