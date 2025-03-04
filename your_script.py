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

def fetch_all_spot_pairs():
    """Fetch all Binance US spot trading pairs."""
    markets = binance.load_markets()
    return [symbol for symbol in markets if "/USDT" in symbol]

def check_signal(symbol):
    """Check for buy/sell signals based on MACD and EMA crossovers."""
    try:
        data = binance.fetch_ohlcv(symbol, '1h', limit=100)
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['ema_44'] = df['close'].ewm(span=44, adjust=False).mean()
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()

        trend_direction = 'UP' if df.iloc[-1]['ema_9'] > df.iloc[-1]['ema_44'] else 'DOWN'

        if df.iloc[-2]['macd'] < df.iloc[-2]['signal'] and df.iloc[-1]['macd'] > df.iloc[-1]['signal'] and trend_direction == 'UP':
            return f"BUY Signal for {symbol}"
        elif df.iloc[-2]['macd'] > df.iloc[-2]['signal'] and df.iloc[-1]['macd'] < df.iloc[-1]['signal'] and trend_direction == 'DOWN':
            return f"SELL Signal for {symbol}"
        return None
    except Exception as e:
        return f"Error checking {symbol}: {str(e)}"

def monitor_pairs():
    """Monitor all Binance US pairs and send Telegram alerts."""
    pairs = fetch_all_spot_pairs()
    while True:
        for pair in pairs:
            signal = check_signal(pair)
            if signal:
                bot.send_message(CHAT_ID, signal)
        time.sleep(60)  # Check every minute

@app.route("/")
def home():
    return "Trading Bot is Running!"

if __name__ == "__main__":
    # Start monitoring in a separate thread
    threading.Thread(target=monitor_pairs, daemon=True).start()
    # Run Flask server
    app.run(host="0.0.0.0", port=10000)

