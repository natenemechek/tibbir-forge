from flask import Flask, jsonify
import os
import logging
import time

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
PORT = int(os.getenv("PORT", 5000))

# Health check (instant)
@app.route('/health')
def health():
    logging.info("Health check OK")
    return jsonify({"status": "healthy", "time": time.time()}), 200

# Home
@app.route('/')
def home():
    return jsonify({"message": "Tibbir Forge LIVE"}), 200

# Authenticate (Moralis)
@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.get_json() or {}
    address = data.get('address', '').strip()
    if not address:
        return jsonify({"error": "address required"}), 400

    payload = {
        "chainId": "84531",
        "address": address,
        "domain": "tibbirforge.bubbleapps.io",
        "uri": "https://tibbirforge.bubbleapps.io",
        "statement": "Sign to authenticate",
        "expiration": int(time.time()) + 120
    }

    headers = {"X-API-Key": os.getenv("MORALIS_KEY"), "Content-Type": "application/json"}
    try:
        r = requests.post("https://auth.moralis.io/v2/wallets/challenge/request", json=payload, headers=headers, timeout=30)
        if r.status_code == 201:
            return jsonify(r.json()), 201
        else:
            return jsonify(r.json()), r.status_code
    except Exception as e:
        logging.error(f"Auth error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logging.info(f"Starting on 0.0.0.0:{PORT}")
    app.run(host='::', port=PORT)