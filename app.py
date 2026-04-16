import os
from flask import Flask, request, jsonify
from requests_oauthlib import OAuth1Session

app = Flask(__name__)

@app.route("/post", methods=["POST"])
def post_tweet():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Kein Text"}), 400

    text = data["text"][:280]

    twitter = OAuth1Session(
        os.environ.get("API_KEY"),
        os.environ.get("API_SECRET"),
        os.environ.get("ACCESS_TOKEN"),
        os.environ.get("ACCESS_TOKEN_SECRET")
    )

    response = twitter.post(
        "https://api.twitter.com/2/tweets",
        json={"text": text}
    )

    if response.status_code == 201:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": response.text}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
