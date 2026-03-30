import os
import requests
import yfinance as yf
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")


def get_stock(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={API_KEY}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def get_yahoo_index(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2d", interval="1d")

    if hist.empty:
        return {"c": 0, "d": 0, "dp": 0}

    close_today = float(hist["Close"].iloc[-1])

    if len(hist) >= 2:
        close_prev = float(hist["Close"].iloc[-2])
    else:
        close_prev = close_today

    change = close_today - close_prev
    percent = (change / close_prev * 100) if close_prev != 0 else 0

    return {
        "c": close_today,
        "d": change,
        "dp": percent
    }


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def get_icon(percent):
    if percent > 0:
        return "✅"
    elif percent < 0:
        return "🔴"
    return "⚪"


def format_number(value, decimals=2):
    return f"{value:,.{decimals}f}"


def format_price_line(name, data):
    price = safe_float(data.get("c"))
    change = safe_float(data.get("d"))
    percent = safe_float(data.get("dp"))
    icon = get_icon(percent)

    return f"• {name}: {format_number(price)}$ {icon} {change:+.2f}$ ({percent:+.2f}%)"


def format_index_line(name, data):
    price = safe_float(data.get("c"))
    percent = safe_float(data.get("dp"))
    icon = get_icon(percent)

    return f"• {name}: {format_number(price)} {icon} {percent:+.2f}%"


def detect_market_regime(sp500_data, nasdaq_data, vix_data):
    sp500_change = safe_float(sp500_data.get("dp"))
    nasdaq_change = safe_float(nasdaq_data.get("dp"))
    vix_value = safe_float(vix_data.get("c"))

    avg_change = (sp500_change + nasdaq_change) / 2

    if avg_change > 0.5 and vix_value < 20:
        return "🐂 Bullish"
    elif avg_change < -1.0 or vix_value > 25:
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

    # Indeksai per Yahoo
    sp500 = get_yahoo_index("^GSPC")
    nasdaq = get_yahoo_index("^IXIC")
    vix = get_yahoo_index("^VIX")

    market_regime = detect_market_regime(sp500, nasdaq, vix)

    # Akcijos per Finnhub
    tsla = get_stock("TSLA")
    aapl = get_stock("AAPL")
    intc = get_stock("INTC")
    bac = get_stock("BAC")
    t = get_stock("T")
    wkey = get_stock("WKEY")
    lucid = get_stock("LCID")
    tal = get_stock("TAL")

    # Crypto per Finnhub
    btc = get_stock("BINANCE:BTCUSDT")
    eth = get_stock("BINANCE:ETHUSDT")

    text = (
        "📊 PORTFOLIO UPDATE\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕒 {update_time}\n\n"

        "📈 MARKET OVERVIEW\n"
        "──────────────────\n"
        f"{format_index_line('S&P 500', sp500)}\n"
        f"{format_index_line('NASDAQ', nasdaq)}\n"
        f"{format_index_line('VIX Index', vix)}\n"
        f"• Market Regime: {market_regime}\n\n"

        "📊 STOCKS\n"
        "──────────────────\n"
        f"{format_price_line('Tesla', tsla)}\n"
        f"{format_price_line('Apple', aapl)}\n"
        f"{format_price_line('Intel', intc)}\n"
        f"{format_price_line('Bank of America', bac)}\n"
        f"{format_price_line('AT&T', t)}\n"
        f"{format_price_line('WISeKey', wkey)}\n"
        f"{format_price_line('Lucid', lucid)}\n"
        f"{format_price_line('TAL Education', tal)}\n\n"

        "💰 CRYPTO\n"
        "──────────────────\n"
        f"{format_price_line('Bitcoin', btc)}\n"
        f"{format_price_line('Ethereum', eth)}\n\n"

        "Disclaimer: For informational purposes only. Not financial advice."
    )

    send_telegram_message(text)
    print("Žinutė išsiųsta sėkmingai.")


if __name__ == "__main__":
    main()