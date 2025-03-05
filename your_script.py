from flask import Flask
import threading
import ccxt
import pandas as pd
import time
import telebot

app = Flask(__name__)

# ✅ Binance US API Initialization
binance = ccxt.binanceus()

# ✅ Telegram Bot Setup (Replace with your token & chat ID)
TELEGRAM_BOT_TOKEN = "8069024735:AAHD7z4RW0TjSBE9swxoTMQCoBOh4Hoo39Q"
CHAT_ID = "796853882"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# ✅ Cooldown Time (Avoid duplicate alerts)
COOLDOWN_PERIOD = 900  # 15 minutes
last_signal_time = {}

TIMEFRAMES = ['1m', '3m', '5m', '15m', '1h', '4h']

def fetch_all_usdt_pairs():
    """Fetch all Binance US spot trading pairs ending with /USDT."""
    try:
        markets = binance.load_markets()
        return [symbol for symbol in markets if symbol.endswith("/USDT")]
    except Exception as e:
        print(f"Error fetching USDT pairs: {str(e)}")
        return []

def check_signal(symbol, timeframe):
    """Check for EMA 9 / EMA 44 cross and MACD confirmation."""
    try:
        formatted_pair = symbol.replace("/", "")  # Convert AXS/USDT -> AXSUSDT
        data = binance.fetch_ohlcv(formatted_pair, timeframe, limit=300)

        if not data:
            return None

        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_44'] = df['close'].ewm(span=44, adjust=False).mean()
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # ✅ EMA Cross Confirmation
        prev_ema_9 = df.iloc[-2]['ema_9']
        prev_ema_44 = df.iloc[-2]['ema_44']
        curr_ema_9 = df.iloc[-1]['ema_9']
        curr_ema_44 = df.iloc[-1]['ema_44']

        # ✅ Confirming EMA Cross with MACD Signal
        if prev_ema_9 < prev_ema_44 and curr_ema_9 > curr_ema_44 and df.iloc[-1]['macd'] > df.iloc[-1]['signal']:
            return f"🚀 BUY Signal for {symbol} ({timeframe} EMA 9 crossed above EMA 44)"
        elif prev_ema_9 > prev_ema_44 and curr_ema_9 < curr_ema_44 and df.iloc[-1]['macd'] < df.iloc[-1]['signal']:
            return f"⚠️ SELL Signal for {symbol} ({timeframe} EMA 9 crossed below EMA 44)"
        return None
    except Exception as e:
        print(f"Error checking {symbol} on {timeframe}: {str(e)}")
        return None

def monitor_pairs():
    """Monitor all USDT pairs and send Telegram alerts."""
    while True:
        pairs = fetch_all_usdt_pairs()
        if not pairs:
            print("No USDT pairs found. Retrying in 5 minutes...")
            time.sleep(300)
            continue

        for pair in pairs:
            for timeframe in TIMEFRAMES:
                signal = check_signal(pair, timeframe)
                if signal:
                    current_time = time.time()
                    signal_key = f"{pair}_{timeframe}"
                    if signal_key in last_signal_time and (current_time - last_signal_time[signal_key]) < COOLDOWN_PERIOD:
                        continue  # ✅ Skip if within cooldown

                    bot.send_message(CHAT_ID, signal)
                    last_signal_time[signal_key] = current_time  # ✅ Update last signal time

        time.sleep(300)  # ✅ Re-check every 5 minutes

@app.route("/")
def home():
    return "Trading Bot is Running!"

if __name__ == "__main__":
    # ✅ Start monitoring in a separate thread
    threading.Thread(target=monitor_pairs, daemon=True).start()
    # ✅ Run Flask server
    app.run(host="0.0.0.0", port=10000)
