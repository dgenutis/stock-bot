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
    close_prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else close_today

    change = close_today - close_prev
    percent = (change / close_prev * 100) if close_prev != 0 else 0

    return {
        "c": close_today,
        "d": change,
        "dp": percent
    }


def get_yahoo_quote(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d", interval="1d")

    if hist.empty:
        return {"c": 0, "d": 0, "dp": 0}

    close_today = float(hist["Close"].iloc[-1])
    close_prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else close_today

    change = close_today - close_prev
    percent = (change / close_prev * 100) if close_prev != 0 else 0

    return {
        "c": close_today,
        "d": change,
        "dp": percent
    }


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


def get_market_news(category="general", limit=3):
    try:
        url = f"https://finnhub.io/api/v1/news?category={category}&token={API_KEY}"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        headlines = []
        for item in data[:limit]:
            headline = item.get("headline")
            if headline:
                headlines.append(headline)

        return headlines
    except Exception:
        return []


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def get_icon(percent):
    if percent > 0:
        return "🟢"
    elif percent < 0:
        return "🔴"
    return "⚪"


def format_number(value, decimals=2):
    return f"{value:,.{decimals}f}"


def format_price_line(name, data, currency="$"):
    price = safe_float(data.get("c"))
    change = safe_float(data.get("d"))
    percent = safe_float(data.get("dp"))
    icon = get_icon(percent)

    return f"• {name}: {format_number(price)}{currency} {icon} {change:+.2f}{currency} ({percent:+.2f}%)"


def format_etf_line(name, data, currency="€"):
    price = safe_float(data.get("c"))
    change = safe_float(data.get("d"))
    percent = safe_float(data.get("dp"))
    icon = get_icon(percent)

    return f"• {name}: {format_number(price)}{currency} {icon} {change:+.2f}{currency} ({percent:+.2f}%)"


def format_index_line(name, data):
    price = safe_float(data.get("c"))
    percent = safe_float(data.get("dp"))
    icon = get_icon(percent)

    return f"• {name}: {format_number(price)} {icon} {percent:+.2f}%"



def format_dividend_line(name, div_data):
    last_dividend = div_data.get("last_dividend")
    ex_date = div_data.get("ex_date")
    dividend_yield = div_data.get("dividend_yield")

    # Jei akcija niekada nemokėjo dividendų – nerodyti
    if last_dividend is None or last_dividend <= 0:
        return None

    parts = [f"• {name}:"]

    parts.append(f"last {last_dividend:.2f}$")

    if dividend_yield is not None:
        parts.append(f"yield {dividend_yield:.1f}%")

    if ex_date != "N/A":
        parts.append(f"ex-date {ex_date}")

    return " | ".join(parts)



def detect_market_regime(sp500_data, nasdaq_data, vix_data):
    sp500_change = safe_float(sp500_data.get("dp"))
    nasdaq_change = safe_float(nasdaq_data.get("dp"))
    vix_value = safe_float(sp500_data.get("c")) if False else safe_float(vix_data.get("c"))

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

    # ETF duomenys
    spyl = get_yahoo_quote("SPYL.DE")
    wexe = get_yahoo_quote("WEXE.DE")

    etf_items = [
        ("SPYL (Acc)", spyl, "€"),
        ("WEXE (Acc)", wexe, "€"),
    ]

    # Akcijų duomenys
    tsla = get_stock("TSLA")
    aapl = get_stock("AAPL")
    intc = get_stock("INTC")
    bac = get_stock("BAC")
    t = get_stock("T")
    wkey = get_stock("WKEY")
    lucid = get_stock("LCID")
    tal = get_stock("TAL")
    msft = get_stock("MSFT")
    beam = get_stock("BEAM")
    netfkix = get_stock("NFLX")
    nike = get_stock("NKE")
    elf = get_stock("ELF")
    celcius = get_stock("CELH")
    sofi = get_stock("SOFI")
    o = get_stock("O")
    hnst = get_stock("HNST")
    vf = get_stock("VFC")
    lac = get_stock("LAC")

    stock_items = [
        ("Tesla", tsla),
        ("Apple", aapl),
        ("Intel", intc),
        ("Bank of America", bac),
        ("AT&T", t),
        ("WISeKey", wkey),
        ("Lucid", lucid),
        ("TAL", tal),
        ("Microsoft", msft),
        ("Beam", beam),
        ("Netflix", netfkix),
        ("Nike", nike),
        ("e.l.f.", elf),
        ("Celsius", celcius),
        ("SoFi", sofi),
        ("Realty", o),
        ("Honest", hnst),
        ("VF", vf),
        ("Lithium", lac),
    ]

    # Dividendų duomenys
    tsla_div = get_dividend_info("TSLA")
    aapl_div = get_dividend_info("AAPL")
    intc_div = get_dividend_info("INTC")
    bac_div = get_dividend_info("BAC")
    t_div = get_dividend_info("T")
    wkey_div = get_dividend_info("WKEY")
    lucid_div = get_dividend_info("LCID")
    tal_div = get_dividend_info("TAL")
    msft_div = get_dividend_info("MSFT")
    beam_div = get_dividend_info("BEAM")
    netfkix_div = get_dividend_info("NFLX")
    nike_div = get_dividend_info("NKE")
    elf_div = get_dividend_info("ELF")
    celcius_div = get_dividend_info("CELH")
    sofi_div = get_dividend_info("SOFI")
    o_div = get_dividend_info("O")
    hnst_div = get_dividend_info("HNST")
    vf_div = get_dividend_info("VFC")
    lac_div = get_dividend_info("LAC")

    dividend_items = [
        ("Tesla", tsla_div),
        ("Apple", aapl_div),
        ("Intel", intc_div),
        ("Bank of America", bac_div),
        ("AT&T", t_div),
        ("WISeKey", wkey_div),
        ("Lucid", lucid_div),
        ("TAL", tal_div),
        ("Microsoft", msft_div),
        ("Beam", beam_div),
        ("Netflix", netfkix_div),
        ("Nike", nike_div),
        ("e.l.f.", elf_div),
        ("Celsius", celcius_div),
        ("SoFi", sofi_div),
        ("Realty", o_div),
        ("Honest", hnst_div),
        ("VF", vf_div),
        ("Lithium", lac_div),
    ]

    # Kriptovaliutos
    btc = get_stock("BINANCE:BTCEUR")
    eth = get_stock("BINANCE:ETHEUR")
    atom = get_stock("BINANCE:ATOMEUR")

    crypto_items = [
        ("Bitcoin", btc, "€"),
        ("Ethereum", eth, "€"),
        ("Atom", atom, "€"),
    ]

    # Naujienos
    news = get_market_news(category="general", limit=3)

    # Eilutės generuojamos iš tų pačių sąrašų, pagal kuriuos skaičiuojami kiekiai
    etf_lines = [
        format_etf_line(name, data, currency)
        for name, data, currency in etf_items
    ]

    stock_lines = [
        format_price_line(name, data)
        for name, data in stock_items
    ]

    dividend_lines = [
        line for name, data in dividend_items
        if (line := format_dividend_line(name, data)) is not None
    ]

    crypto_lines = [
        format_price_line(name, data, currency)
        for name, data, currency in crypto_items
    ]

    text = (
        "📊 PORTFOLIO UPDATE\\n"
        "━━━━━━━━━━━━━━━━━━\\n"
        f"🕒 {update_time}\\n\\n"

        "📈 MARKET OVERVIEW\\n"
        "──────────────────\\n"
        f"{format_index_line('S&P 500', sp500)}\\n"
        f"{format_index_line('NASDAQ', nasdaq)}\\n"
        f"{format_index_line('VIX Index', vix)}\\n"
        f"• Market Regime: {market_regime}\\n\\n"

        f"📦 ETFs ({len(etf_items)})\\n"
        "──────────────────\\n"
        + "\\n".join(etf_lines) + "\\n\\n"

        f"📊 STOCKS ({len(stock_items)})\\n"
        "──────────────────\\n"
        + "\\n".join(stock_lines) + "\\n\\n"

        f"💸 DIVIDENDS ({len(dividend_lines)})\\n"
        "──────────────────\\n"
        + ("\\n".join(dividend_lines) if dividend_lines else "No dividend-paying stocks")
        + "\\n\\n"

        f"💰 CRYPTO ({len(crypto_items)})\\n"
        "──────────────────\\n"
        + "\\n".join(crypto_lines) + "\\n\\n"
    )

    if news:
        text += f"📰 NEWS ({len(news)})\\n"
        text += "──────────────────\\n"
        for headline in news:
            text += f"• {headline}\\n"
        text += "\\n"

    send_telegram_message(text)
    print("Žinutė išsiųsta sėkmingai.")


if __name__ == "__main__":
    main()