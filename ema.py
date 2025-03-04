import ccxt
import pandas as pd
import time
import telebot

# Initialize Binance Futures API
binance = ccxt.binance({"options": {"defaultType": "future"}})

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "8069024735:AAHD7z4RW0TjSBE9swxoTMQCoBOh4Hoo39Q"
CHAT_ID = "796853882"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def fetch_all_futures_pairs():
    markets = binance.load_markets()
    return [symbol for symbol in markets if "/USDT" in symbol and markets[symbol].get("type") == "future"]

def fetch_ohlcv(symbol, timeframe='1h', limit=100):
    return binance.fetch_ohlcv(symbol, timeframe, limit=limit)

def calculate_macd(df):
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['histogram'] = df['macd'] - df['signal']
    return df

def calculate_ema(df):
    df['ema_44'] = df['close'].ewm(span=44, adjust=False).mean()
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    return df

def check_signal(symbol):
    data = fetch_ohlcv(symbol)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = calculate_macd(df)
    df = calculate_ema(df)
    
    if len(df) < 2:
        return None
    
    macd_current = df.iloc[-1]['macd']
    signal_current = df.iloc[-1]['signal']
    macd_previous = df.iloc[-2]['macd']
    signal_previous = df.iloc[-2]['signal']
    ema_44 = df.iloc[-1]['ema_44']
    ema_9 = df.iloc[-1]['ema_9']
    
    trend_direction = 'UP' if ema_9 > ema_44 else 'DOWN'
    
    if macd_previous < signal_previous and macd_current > signal_current and trend_direction == 'UP':
        return f"BUY Signal for {symbol}"
    elif macd_previous > signal_previous and macd_current < signal_current and trend_direction == 'DOWN':
        return f"SELL Signal for {symbol}"
    return None

def monitor_pairs():
    pairs = fetch_all_futures_pairs()
    while True:
        for pair in pairs:
            try:
                signal = check_signal(pair)
                if signal:
                    print(signal)
                    bot.send_message(CHAT_ID, signal)
            except Exception as e:
                print(f"Error checking {pair}: {e}")
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    monitor_pairs()
