# -------------------------------------------------
# app.py – Tibbir Forge (MINIMAL - 502 FIX)
# -------------------------------------------------
from flask import Flask, jsonify
import os
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
PORT = int(os.getenv("PORT", 5000))

# Health check
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "time": time.time()}), 200

# Test route
@app.route('/')
def home():
    return jsonify({"message": "Tibbir Forge API is LIVE"}), 200

if __name__ == '__main__':
    logging.info(f"Starting on 0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)