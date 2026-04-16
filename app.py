import os
from flask import Flask, request, jsonify
import tweepy

app = Flask(__name__)

# X API Keys - aus Umgebungsvariablen (sicher!)
API_KEY = os.environ.get("API_KEY")
API_SECRET = os.environ.get("API_SECRET")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")

def get_twitter_client():
    return tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )

@app.route("/post", methods=["POST"])
def post_tweet():
    data = request.get_json()

    if not data or "text" not in data:
        return jsonify({"error": "Kein Text vorhanden"}), 400

    text = data["text"]

    # X erlaubt max. 280 Zeichen
    if len(text) > 280:
        text = text[:277] + "..."

    try:
        client = get_twitter_client()
        response = client.create_tweet(text=text)
        return jsonify({"success": True, "tweet_id": response.data["id"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
