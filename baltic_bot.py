import os
import requests
import yfinance as yf
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def get_yahoo_data(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d")

    if hist.empty:
        raise ValueError(f"Neradau duomenų simboliui: {symbol}")

    price = float(hist["Close"].iloc[-1])

    if len(hist) >= 2:
        prev_close = float(hist["Close"].iloc[-2])
    else:
        prev_close = price

    change = price - prev_close
    percent = (change / prev_close * 100) if prev_close != 0 else 0

    return {
        "c": price,
        "pc": prev_close,
        "d": change,
        "dp": percent
    }


def format_stock(name, data):
    price = data.get("c", 0)
    prev_close = data.get("pc", 0)
    change = data.get("d", 0)
    percent = data.get("dp", 0)

    if percent > 0:
        icon = "🟢"
    elif percent < 0:
        icon = "🔴"
    else:
        icon = "⚪"

    return (
        f"{name}\n"
        f"• Kaina: {round(price, 4)}$\n"
        f"• Vakar: {round(prev_close, 4)}$\n"
        f"• Pokytis: {icon} {round(change, 4)}$ ({round(percent, 2)}%)\n"
    )


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    response = requests.post(url, data=payload, timeout=20)
    response.raise_for_status()


def main():
    # 🕒 Vilniaus laikas
    now = datetime.now(ZoneInfo("Europe/Vilnius"))
    update_time = now.strftime("%Y-%m-%d %H:%M LT")

    # Baltic akcijos
    kne = get_yahoo_data("KNE1L.VS")
    dgr = get_yahoo_data("DGR1R.RG")
    roe = get_yahoo_data("ROE1L.VS")
    ign = get_yahoo_data("IGN1L.VS")
    tel = get_yahoo_data("TEL1L.VS")

    # Crypto
    btc = get_yahoo_data("BTC-USD")
    eth = get_yahoo_data("ETH-USD")

    text = (
        f"🇱🇹 BALTIC PORTFELIS\n\n"
        f"🕒 Update: {update_time}\n\n\n"

        + format_stock("KN Energies", kne) + "\n"
        + format_stock("DelfinGroup", dgr) + "\n"
        + format_stock("Rokiškio sūris", roe) + "\n"
        + format_stock("Ignitis", ign) + "\n"
        + format_stock("Telia", tel) + "\n"

        + "\n₿ CRYPTO\n\n"
        + format_stock("Bitcoin", btc) + "\n"
        + format_stock("Ethereum", eth)
    )

    send_telegram_message(text)
    print("Baltic + crypto žinutė išsiųsta")


if __name__ == "__main__":
    main()