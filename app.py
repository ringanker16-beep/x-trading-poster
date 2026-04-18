import os
import pytz
from datetime import datetime
from flask import Flask, request, jsonify
from requests_oauthlib import OAuth1Session
import yfinance as yf
from curl_cffi import requests as curl_requests
session = curl_requests.Session(impersonate="chrome")

app = Flask(__name__)

def get_stock_data(ticker, level_type):
    try:
        stock = yf.Ticker(ticker, session=session)
        hist_90 = stock.history(period="90d")
        hist_35 = stock.history(period="35d")

        if hist_90.empty:
            return None

        current_price = hist_35['Close'].iloc[-1]
        price_1d_ago = hist_35['Close'].iloc[-2] if len(hist_35) >= 2 else current_price
        price_7d_ago = hist_35['Close'].iloc[-8] if len(hist_35) >= 8 else hist_35['Close'].iloc[0]
        price_30d_ago = hist_35['Close'].iloc[-31] if len(hist_35) >= 31 else hist_35['Close'].iloc[0]

        change_1d = ((current_price - price_1d_ago) / price_1d_ago) * 100
        change_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
        change_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100

        high_30d = hist_35['High'].max()
        low_30d = hist_35['Low'].min()
        high_90d = hist_90['High'].max()
        low_90d = hist_90['Low'].min()

        info = stock.info
        company_name = info.get('longName', ticker)
        week_52_high = info.get('fiftyTwoWeekHigh', 'N/A')
        week_52_low = info.get('fiftyTwoWeekLow', 'N/A')
        sector = info.get('sector', 'N/A')

        result = {
            "company_name": company_name,
            "sector": sector,
            "current_price": round(current_price, 2),
            "change_1d": round(change_1d, 2),
            "change_7d": round(change_7d, 2),
            "change_30d": round(change_30d, 2),
            "week_52_high": week_52_high,
            "week_52_low": week_52_low,
        }

        if level_type == "support":
            result["high_30d"] = round(high_30d, 2)
            result["high_90d"] = round(high_90d, 2)
        else:
            result["low_30d"] = round(low_30d, 2)
            result["low_90d"] = round(low_90d, 2)

        return result

    except Exception as e:
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

    ticker = data.get("ticker", "")
    alert_price = data.get("alert_price", "")
    level_type = data.get("level_type", "support")
    claude_text = data.get("text", "")
    mez_time = get_mez_time()

    stock_data = get_stock_data(ticker, level_type) if ticker else None

    if stock_data:
        def arrow(val):
            return "▲" if val >= 0 else "▼"

        if level_type == "support":
            analyse = (
                f"📊 Analysis ${ticker}:\n"
                f"Price:      ${alert_price}\n"
                f"30D High:   ${stock_data['high_30d']}\n"
                f"90D High:   ${stock_data['high_90d']}\n"
                f"52W Range:  ${stock_data['week_52_low']} – ${stock_data['week_52_high']}"
            )
        else:
            analyse = (
                f"📊 Analysis ${ticker}:\n"
                f"Price:      ${alert_price}\n"
                f"30D Low:    ${stock_data['low_30d']}\n"
                f"90D Low:    ${stock_data['low_90d']}\n"
                f"52W Range:  ${stock_data['week_52_low']} – ${stock_data['week_52_high']}"
            )

        post_text = f"{claude_text}\n\n{analyse}\n\n⏰ {mez_time}"
    else:
        post_text = f"{claude_text}\n\n⏰ {mez_time}"

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

