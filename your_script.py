from flask import Flask
import threading
import ccxt
import pandas as pd
import time
import telebot

app = Flask(__name__)

# Initialize Binance US API
binance = ccxt.binanceus()

# Telegram Bot Token (Keep this secure!)
TELEGRAM_BOT_TOKEN = "8069024735:AAHD7z4RW0TjSBE9swxoTMQCoBOh4Hoo39Q"
CHAT_ID = "796853882"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Store last signal to avoid spam
last_signal = {}
last_signal_time = {}

COOLDOWN_PERIOD = 3600  # 1-hour cooldown (in seconds)

def fetch_all_usdt_pairs():
    """Fetch all Binance US spot trading pairs ending with USDT."""
    try:
        markets = binance.load_markets()
        return [symbol for symbol in markets if symbol.endswith("/USDT")]
    except Exception as e:
        print(f"Error fetching USDT pairs: {e}")
        return []

def check_signal(symbol):
    """Check for buy/sell signals based on MACD and EMA crossovers."""
    try:
        formatted_pair = symbol.replace("/", "")  # Convert AXS/USDT → AXSUSDT
        data = binance.fetch_ohlcv(formatted_pair, '1h', limit=100)

        if not data:
            print(f"No data for {symbol}")
            return None
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['ema_44'] = df['close'].ewm(span=44, adjust=False).mean()
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()

        trend_direction = 'UP' if df.iloc[-1]['ema_9'] > df.iloc[-1]['ema_44'] else 'DOWN'
        signal = None

        if df.iloc[-2]['macd'] < df.iloc[-2]['signal'] and df.iloc[-1]['macd'] > df.iloc[-1]['signal'] and trend_direction == 'UP':
            signal = f"BUY Signal for {symbol}"
        elif df.iloc[-2]['macd'] > df.iloc[-2]['signal'] and df.iloc[-1]['macd'] < df.iloc[-1]['signal'] and trend_direction == 'DOWN':
            signal = f"SELL Signal for {symbol}"

        if signal:
            current_time = time.time()

            # Check cooldown (1 hour)
            if symbol in last_signal_time and (current_time - last_signal_time[symbol]) < COOLDOWN_PERIOD:
                return None  # Ignore repeated signal within cooldown period
            
            last_signal[symbol] = signal
            last_signal_time[symbol] = current_time
            return signal

        return None  # No new signal

    except Exception as e:
        print(f"Error checking {symbol}: {str(e)}")
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
            signal = check_signal(pair)
            if signal:
                bot.send_message(CHAT_ID, signal)
        time.sleep(300)  # Check every 5 minutes

@app.route("/")
def home():
    return "Trading Bot is Running!"

if __name__ == "__main__":
    # Start monitoring in a separate thread
    threading.Thread(target=monitor_pairs, daemon=True).start()
    # Run Flask server
    app.run(host="0.0.0.0", port=10000)
