import os
import re
import json
import pytz
from datetime import datetime
from flask import Flask, request, jsonify
from requests_oauthlib import OAuth1Session

app = Flask(__name__)

def clean_text(raw_text):
    """Bereinigt den Text von JSON-Resten und Sonderzeichen"""
    if not raw_text:
        return ""

    text = str(raw_text)

    # Falls es ein JSON String ist, versuche zu parsen
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

    # Entferne Reste von JSON-Strukturen
    text = re.sub(r'^\{"type":"text","text":"', '', text)
    text = re.sub(r'"\}$', '', text)
    text = re.sub(r'^\{"text":"', '', text)
    text = re.sub(r'^"', '', text)
    text = re.sub(r'"$', '', text)

    # Konvertiere escaped Zeichen zu echten
    text = text.replace('\\n', '\n')
    text = text.replace('\\"', '"')
    text = text.replace('\\\\', '\\')

    return text.strip()

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
    mez_time = get_mez_time()

    # Text bereinigen
    clean = clean_text(raw_text)

    # MEZ Zeit anhängen
    post_text = f"{clean}\n\n⏰ {mez_time}"

    # Auf 280 Zeichen kürzen
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
