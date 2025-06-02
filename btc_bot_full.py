
import ccxt
import pandas as pd
import time
import datetime
import os
from telegram import Bot
from dotenv import load_dotenv

# بارگذاری فایل .env
load_dotenv(dotenv_path="./.env")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

bot = Bot(token=TELEGRAM_TOKEN)

def send_to_telegram(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

symbol = 'BTC/USDT'
timeframe = '5m'
limit = 200
exchange = ccxt.binance()

def get_data():
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def apply_indicators(df):
    df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    df['BB_MID'] = df['close'].rolling(window=20).mean()
    df['BB_STD'] = df['close'].rolling(window=20).std()
    df['BB_upper'] = df['BB_MID'] + 2 * df['BB_STD']
    df['BB_lower'] = df['BB_MID'] - 2 * df['BB_STD']
    return df

def check_signal(df):
    latest = df.iloc[-1]
    signals = []

    if (
        latest['EMA_20'] > latest['EMA_50']
        and latest['RSI'] < 70
        and latest['MACD'] > latest['MACD_signal']
        and latest['close'] > latest['BB_lower']
    ):
        signals.append('💹 سیگنال خرید')

    if (
        latest['EMA_20'] < latest['EMA_50']
        and latest['RSI'] > 30
        and latest['MACD'] < latest['MACD_signal']
        and latest['close'] < latest['BB_upper']
    ):
        signals.append('🔻 سیگنال فروش')

    return signals

def run_backtest(df):
    print("📊 شروع بک‌تست:")
    for i in range(50, len(df)):
        sample = df.iloc[:i+1]
        signals = check_signal(sample)
        date = sample.iloc[-1]['timestamp']
        if signals:
            for sig in signals:
                print(f"{date} - {sig}")

# حالت اجرای زنده یا بک‌تست
if __name__ == "__main__":
    df = get_data()
    df = apply_indicators(df)

    # اجرای بک‌تست
    run_backtest(df)

    # اجرای زنده با ارسال تلگرام
    while True:
        try:
            df = get_data()
            df = apply_indicators(df)
            signals = check_signal(df)

            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if signals:
                for signal in signals:
                    msg = f'{now}\n{signal}'
                    print(msg)
                    send_to_telegram(msg)
            else:
                print(f'{now} - هیچ سیگنالی نیست')

            time.sleep(60)

        except Exception as e:
            print("خطا:", e)
            time.sleep(60)
