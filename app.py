import os
import re
import json
import pytz
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from requests_oauthlib import OAuth1Session

app = Flask(__name__)

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")

def clean_text(raw_text):
    """Bereinigt JSON-Reste aus dem Text"""
    if not raw_text:
        return ""

    text = str(raw_text)

    try:
        if text.startswith('{') or text.startswith('['):
            parsed = json.loads(text)
            if isinstance(parsed, dict) and 'text' in parsed:
                text = parsed['text']
            elif isinstance(parsed, list) and len(parsed) > 0:
                if isinstance(parsed[0], dict) and 'text' in parsed[0]:
                    text = parsed[0]['text']
    except:
        pass

    text = re.sub(r'^\{"type":"text","text":"', '', text)
    text = re.sub(r'"\}$', '', text)
    text = re.sub(r'^\{"text":"', '', text)
    text = re.sub(r'^"', '', text)
    text = re.sub(r'"$', '', text)

    text = text.replace('\\n', '\n')
    text = text.replace('\\"', '"')
    text = text.replace('\\\\', '\\')

    return text.strip()

def get_stock_data(ticker, level_type):
    """Holt Aktien/Krypto Daten von Finnhub"""
    try:
        # Aktien Endpoint
        is_crypto = "USDT" in ticker.upper() or "USD" in ticker.upper() and len(ticker) > 6

        if is_crypto:
            # Krypto Symbol Format: BINANCE:BTCUSDT
            symbol = f"BINANCE:{ticker.upper()}"
            quote_url = f"https://finnhub.io/api/v1/crypto/candle"

            # 90 Tage Daten holen
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=90)).timestamp())

            params = {
                "symbol": symbol,
                "resolution": "D",
                "from": start_time,
                "to": end_time,
                "token": FINNHUB_API_KEY
            }
            response = requests.get(quote_url, params=params, timeout=10)
            data = response.json()

            if data.get('s') == 'ok' and 'h' in data and 'l' in data:
                highs = data['h']
                lows = data['l']
                closes = data['c']

                current = closes[-1] if closes else 0
                high_30d = max(highs[-30:]) if len(highs) >= 30 else max(highs)
                low_30d = min(lows[-30:]) if len(lows) >= 30 else min(lows)
                high_90d = max(highs)
                low_90d = min(lows)

                result = {"current": round(current, 2)}
                if level_type == "support":
                    result["high_30d"] = round(high_30d, 2)
                    result["high_90d"] = round(high_90d, 2)
                else:
                    result["low_30d"] = round(low_30d, 2)
                    result["low_90d"] = round(low_90d, 2)
                return result
        else:
            # Aktien
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=120)).timestamp())

            candle_url = "https://finnhub.io/api/v1/stock/candle"
            params = {
                "symbol": ticker.upper(),
                "resolution": "D",
                "from": start_time,
                "to": end_time,
                "token": FINNHUB_API_KEY
            }
            response = requests.get(candle_url, params=params, timeout=10)
            data = response.json()

            if data.get('s') == 'ok' and 'h' in data and 'l' in data:
                highs = data['h']
                lows = data['l']
                closes = data['c']

                current = closes[-1] if closes else 0
                high_30d = max(highs[-30:]) if len(highs) >= 30 else max(highs)
                low_30d = min(lows[-30:]) if len(lows) >= 30 else min(lows)
                high_90d = max(highs)
                low_90d = min(lows)

                result = {"current": round(current, 2)}
                if level_type == "support":
                    result["high_30d"] = round(high_30d, 2)
                    result["high_90d"] = round(high_90d, 2)
                else:
                    result["low_30d"] = round(low_30d, 2)
                    result["low_90d"] = round(low_90d, 2)
                return result

        return None
    except Exception as e:
        print(f"Finnhub Error: {e}")
        return None

def get_mez_time():
    mez = pytz.timezone('Europe/Berlin')
    now = datetime.now(mez)
    return now.strftime("%d.%m.%Y %H:%M MEZ")

@app.route("/post", methods=["POST"])
def post_tweet():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Kein Text"}), 400

    raw_text = data.get("text", "")
    ticker = data.get("ticker", "")
    alert_price = data.get("alert_price", "")
    level_type = data.get("level_type", "support")

    clean = clean_text(raw_text)
    mez_time = get_mez_time()

    # Finnhub Daten holen
    stock_data = get_stock_data(ticker, level_type) if ticker else None

    if stock_data:
        if level_type == "support":
            analyse = (
                f"\n\n📊 Analysis:\n"
                f"Price: ${alert_price}\n"
                f"30D High: ${stock_data['high_30d']}\n"
                f"90D High: ${stock_data['high_90d']}"
            )
        else:
            analyse = (
                f"\n\n📊 Analysis:\n"
                f"Price: ${alert_price}\n"
                f"30D Low: ${stock_data['low_30d']}\n"
                f"90D Low: ${stock_data['low_90d']}"
            )
        post_text = f"{clean}{analyse}\n\n⏰ {mez_time}"
    else:
        post_text = f"{clean}\n\n⏰ {mez_time}"

    if len(post_text) > 280:
        post_text = post_text[:277] + "..."

    twitter = OAuth1Session(
        os.environ.get("API_KEY"),
        os.environ.get("API_SECRET"),
        os.environ.get("ACCESS_TOKEN"),
        os.environ.get("ACCESS_TOKEN_SECRET")
    )

    response = twitter.post(
        "https://api.twitter.com/2/tweets",
        json={"text": post_text}
    )

    if response.status_code == 201:
        return jsonify({"success": True, "post": post_text}), 200
    else:
        return jsonify({"error": response.text}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
