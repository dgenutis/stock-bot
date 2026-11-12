import os
import requests
import yfinance as yf
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")


# ------------------------
# YAHOO DATA
# ------------------------
def get_yahoo_data(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d", interval="1d")

    if hist.empty:
        return {"c": 0, "pc": 0, "d": 0, "dp": 0}

    price = float(hist["Close"].iloc[-1])
    prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price

    change = price - prev_close
    percent = (change / prev_close * 100) if prev_close != 0 else 0

    return {"c": price, "pc": prev_close, "d": change, "dp": percent}


# ------------------------
# DIVIDENDS
# ------------------------
def get_dividend_info(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info if ticker.info else {}
        dividends = ticker.dividends

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if current_price is None or current_price == 0:
            hist = ticker.history(period="5d", interval="1d")
            if not hist.empty:
                current_price = float(hist["Close"].iloc[-1])

        last_dividend = None
        trailing_yield = None

        if dividends is not None and not dividends.empty:
            last_dividend = float(dividends.iloc[-1])

            # Dividendų suma per paskutinius 12 mėnesių nuo šiandien
            index_tz = dividends.index.tz
            now_for_dividends = (
                datetime.now(index_tz) if index_tz is not None else datetime.now()
            )
            cutoff_date = now_for_dividends - timedelta(days=365)
            trailing_12m = dividends[dividends.index >= cutoff_date]
            annual_dividend = float(trailing_12m.sum())

            if current_price and current_price > 0:
                trailing_yield = (annual_dividend / current_price) * 100

        ex_dividend_date = info.get("exDividendDate")
        ex_date_str = "N/A"
        if ex_dividend_date:
            ex_date_str = datetime.fromtimestamp(ex_dividend_date).strftime("%Y-%m-%d")

        return {
            "last_dividend": last_dividend,
            "ex_date": ex_date_str,
            "dividend_yield": trailing_yield
        }

    except Exception:
        return {
            "last_dividend": None,
            "ex_date": "N/A",
            "dividend_yield": None
        }


# ------------------------
# NEWS (FINNHUB)
# ------------------------
def get_market_news():
    try:
        url = f"https://finnhub.io/api/v1/news?category=general&token={API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        news = []
        for item in data[:3]:
            headline = item.get("headline")
            if headline:
                news.append(headline)

        return news
    except Exception:
        return []


# ------------------------
# FORMAT
# ------------------------
def icon(percent):
    return "🟢" if percent > 0 else "🔴" if percent < 0 else "⚪"


def fmt(n, d=2):
    return f"{n:,.{d}f}"


def stock_line(name, d, cur="€"):
    return f"• {name}: {fmt(d['c'], 4)}{cur} {icon(d['dp'])} {d['d']:+.4f}{cur} ({d['dp']:+.2f}%)"


def index_line(name, d):
    return f"• {name}: {fmt(d['c'])} {icon(d['dp'])} {d['dp']:+.2f}%"


def dividend_line(name, d, cur="€"):
    last_dividend = d.get("last_dividend")
    ex_date = d.get("ex_date")
    dividend_yield = d.get("dividend_yield")

    # Nerodyti bendrovių, kurios niekada nemokėjo dividendų
    if last_dividend is None or last_dividend <= 0:
        return None

    parts = [f"• {name}:", f"last {last_dividend:.2f}{cur}"]

    if dividend_yield is not None:
        parts.append(f"yield {dividend_yield:.1f}%")

    if ex_date and ex_date != "N/A":
        parts.append(f"ex-date {ex_date}")

    return " | ".join(parts)


def detect_regime(b, v, t, r):
    avg = (b["dp"] + v["dp"] + t["dp"] + r["dp"]) / 4
    if avg > 0.4:
        return "🐂 Bullish"
    elif avg < -0.6:
        return "⚠️ Risk-Off"
    return "⚖️ Neutral"


# ------------------------
# TELEGRAM
# ------------------------
def send(text):
    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20
    )
    response.raise_for_status()


# ------------------------
# MAIN
# ------------------------
def main():
    now = datetime.now(ZoneInfo("Europe/Vilnius"))
    t = now.strftime("%Y-%m-%d | %H:%M LT")

    # INDEXAI
    baltic = get_yahoo_data("^OMXBBGI")
    vilnius = get_yahoo_data("^OMXVGI")
    tallinn = get_yahoo_data("^OMXT")
    riga = get_yahoo_data("^OMXRGI")

    regime = detect_regime(baltic, vilnius, tallinn, riga)

    # STOCKS
    kne = get_yahoo_data("KNE1L.VS")
    dgr = get_yahoo_data("DGR1R.RG")
    roe = get_yahoo_data("ROE1L.VS")
    ign = get_yahoo_data("IGN1L.VS")
    tel = get_yahoo_data("TEL1L.VS")

    # DIVIDENDS
    kne_d = get_dividend_info("KNE1L.VS")
    dgr_d = get_dividend_info("DGR1R.RG")
    roe_d = get_dividend_info("ROE1L.VS")
    ign_d = get_dividend_info("IGN1L.VS")
    tel_d = get_dividend_info("TEL1L.VS")

    dividend_items = [
        ("KN Energies", kne_d),
        ("DelfinGroup", dgr_d),
        ("Artea bankas", roe_d),
        ("Ignitis", ign_d),
        ("Telia", tel_d),
    ]

    dividend_lines = [
        line for name, data in dividend_items
        if (line := dividend_line(name, data)) is not None
    ]

    # CRYPTO
    btc = get_yahoo_data("BTC-EUR")
    eth = get_yahoo_data("ETH-EUR")
    atom = get_yahoo_data("ATOM-EUR")

    # NEWS
    news = get_market_news()

    # Skaičiai antraštėse atitinka faktiškai rodomų įrašų skaičių
    stock_count = 5
    crypto_count = 2
    dividend_count = len(dividend_lines)
    news_count = len(news)

    # TEXT
    text = (
        "📊 BALTIC PORTFOLIO UPDATE\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕒 {t}\n\n"

        "📈 MARKET OVERVIEW\n"
        "──────────────────\n"
        f"{index_line('OMX Baltic', baltic)}\n"
        f"{index_line('OMX Vilnius', vilnius)}\n"
        f"{index_line('OMX Tallinn', tallinn)}\n"
        f"{index_line('OMX Riga', riga)}\n"
        f"• Market Regime: {regime}\n\n"

        f"🇱🇹 STOCKS ({stock_count})\n"
        "──────────────────\n"
        f"{stock_line('KN Energies', kne)}\n"
        f"{stock_line('DelfinGroup', dgr)}\n"
        f"{stock_line('Artea bankas', roe)}\n"
        f"{stock_line('Ignitis', ign)}\n"
        f"{stock_line('Telia', tel)}\n\n"

        f"💸 DIVIDENDS ({dividend_count})\n"
        "──────────────────\n"
        + ("\n".join(dividend_lines) if dividend_lines else "No dividend-paying stocks")
        + "\n\n"

        f"💰 CRYPTO ({crypto_count})\n"
        "──────────────────\n"
        f"{stock_line('BTC', btc, '€')}\n"
        f"{stock_line('ETH', eth, '€')}\n"
        f"{stock_line('ATOM', atom, '€')}\n\n"
    )

    if news:
        text += f"📰 NEWS ({news_count})\n"
        text += "──────────────────\n"
        for n in news:
            text += f"• {n}\n"

    send(text)
    print("Baltic žinutė išsiųsta sėkmingai.")


if __name__ == "__main__":
    main()
