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
    hist = ticker.history(period="5d", interval="1d")

    if hist.empty:
        return {"c": 0, "pc": 0, "d": 0, "dp": 0}

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


def get_icon(percent):
    if percent > 0:
        return "✅"
    elif percent < 0:
        return "🔴"
    return "⚪"


def format_number(value, decimals=2):
    return f"{value:,.{decimals}f}"


def format_index_line(name, data):
    price = data.get("c", 0)
    percent = data.get("dp", 0)
    icon = get_icon(percent)

    return f"• {name}: {format_number(price)} {icon} {percent:+.2f}%"


def format_stock_line(name, data, currency="€"):
    price = data.get("c", 0)
    change = data.get("d", 0)
    percent = data.get("dp", 0)
    icon = get_icon(percent)

    return (
        f"• {name}: {format_number(price, 4)}{currency} "
        f"{icon} {change:+.4f}{currency} ({percent:+.2f}%)"
    )


def detect_baltic_regime(baltic_data, vilnius_data, tallinn_data, riga_data):
    changes = [
        baltic_data.get("dp", 0),
        vilnius_data.get("dp", 0),
        tallinn_data.get("dp", 0),
        riga_data.get("dp", 0),
    ]
    avg_change = sum(changes) / len(changes)

    if avg_change > 0.4:
        return "🐂 Bullish"
    elif avg_change < -0.6:
        return "⚠️ Risk-Off"
    else:
        return "⚖️ Neutral"


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    response = requests.post(url, data=payload, timeout=20)
    response.raise_for_status()


def main():
    now = datetime.now(ZoneInfo("Europe/Vilnius"))
    update_time = now.strftime("%Y-%m-%d | %H:%M LT")

    # Baltic indeksai
    omx_baltic = get_yahoo_data("^OMXBBGI")
    omx_vilnius = get_yahoo_data("^OMXVGI")
    omx_tallinn = get_yahoo_data("^OMXT")
    omx_riga = get_yahoo_data("^OMXRGI")

    market_regime = detect_baltic_regime(
        omx_baltic, omx_vilnius, omx_tallinn, omx_riga
    )

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
        "📊 BALTIC PORTFOLIO UPDATE\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕒 {update_time}\n\n"

        "📈 MARKET OVERVIEW\n"
        "──────────────────\n"
        f"{format_index_line('OMX Baltic', omx_baltic)}\n"
        f"{format_index_line('OMX Vilnius', omx_vilnius)}\n"
        f"{format_index_line('OMX Tallinn', omx_tallinn)}\n"
        f"{format_index_line('OMX Riga', omx_riga)}\n"
        f"• Market Regime: {market_regime}\n\n"

        "🇱🇹 BALTIC STOCKS\n"
        "──────────────────\n"
        f"{format_stock_line('KN Energies', kne)}\n"
        f"{format_stock_line('DelfinGroup', dgr)}\n"
        f"{format_stock_line('Artea', roe)}\n"
        f"{format_stock_line('Ignitis', ign)}\n"
        f"{format_stock_line('Telia', tel)}\n\n"

        "💰 CRYPTO\n"
        "──────────────────\n"
        f"{format_stock_line('Bitcoin', btc, '$')}\n"
        f"{format_stock_line('Ethereum', eth, '$')}\n\n"

        "Disclaimer: For informational purposes only. Not financial advice."
    )

    send_telegram_message(text)
    print("Baltic + indeksai + crypto žinutė išsiųsta.")


if __name__ == "__main__":
    main()