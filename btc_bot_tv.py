import os
import time
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
from dotenv import load_dotenv
from telegram import Bot

# بارگذاری متغیرها
load_dotenv()
TV_USER = os.getenv("TV_USER")
TV_PASS = os.getenv("TV_PASS")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=TOKEN)

def send_message(text):
    bot.send_message(chat_id=CHAT_ID, text=text)

def get_data():
    tv = TvDatafeed(username=TV_USER, password=TV_PASS)
    df = tv.get_hist(symbol='BTCUSDT', exchange='BINANCE', interval=Interval.in_5_minute, n_bars=100)
    df = df.reset_index()
    return df

def analyze(df):
    df['EMA20'] = df['close'].ewm(span=20).mean()
    df['EMA50'] = df['close'].ewm(span=50).mean()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    RS = gain / loss
    df['RSI'] = 100 - (100 / (1 + RS))

    exp1 = df['close'].ewm(span=12).mean()
    exp2 = df['close'].ewm(span=26).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9).mean()

    df['MA20'] = df['close'].rolling(window=20).mean()
    df['stddev'] = df['close'].rolling(window=20).std()
    df['Upper'] = df['MA20'] + (df['stddev'] * 2)
    df['Lower'] = df['MA20'] - (df['stddev'] * 2)

    return df

def check_signal(df):
    last = df.iloc[-1]
    signal = None

    if (
        last['EMA20'] > last['EMA50'] and
        last['close'] > last['Upper'] and
        last['RSI'] < 70 and
        last['MACD'] > last['Signal']
    ):
        signal = "📈 سیگنال ورود (خرید)"
    elif (
        last['EMA20'] < last['EMA50'] and
        last['close'] < last['Lower'] and
        last['RSI'] > 30 and
        last['MACD'] < last['Signal']
    ):
        signal = "📉 سیگنال خروج (فروش)"
    return signal

# اجرای اولیه: بک‌تست
df = analyze(get_data())
sig = check_signal(df)
print("📊 بک‌تست اولیه:", sig if sig else "هیچ سیگنالی نبود")

# اجرای زنده
while True:
    df = analyze(get_data())
    signal = check_signal(df)

    now = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    if signal:
        msg = f"{now} - {signal}"
    else:
        msg = f"{now} - هیچ سیگنالی نیست ❌"

    print(msg)
    send_message(msg)
    time.sleep(60)
