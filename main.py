import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("API_KEY")


def get_stock(symbol):
    url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={API_KEY}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def format_stock(name, data):
    price = data.get("c", 0)
    prev_close = data.get("pc", 0)
    change = data.get("d", 0)
    percent = data.get("dp", 0)

    icon = "🟢" if percent > 0 else "🔴"

    return (
        f"{name}\n"
        f"• Kaina šiandien: ${price}\n"
        f"• Vakar close: ${prev_close}\n"
        f"• Pokytis: {icon} {round(change, 2)}$ ({round(percent, 2)}%)\n"
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
    tsla = get_stock("TSLA")
    aapl = get_stock("AAPL")
    intc = get_stock("INTC")

    text = (
        "📊 PORTFOLIO UPDATE\n\n"
        + format_stock("Tesla", tsla) + "\n"
        + format_stock("Apple", aapl) + "\n"
        + format_stock("Intel", intc)
    )

    send_telegram_message(text)
    print("Žinutė išsiųsta sėkmingai.")


if __name__ == "__main__":
    main()