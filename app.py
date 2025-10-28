from flask import Flask, jsonify
import os
import logging
import time

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
PORT = int(os.getenv("PORT", 5000))

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "time": time.time()}), 200

@app.route('/')
def home():
    return jsonify({"message": "Tibbir Forge LIVE"}), 200

if __name__ == '__main__':
    logging.info(f"Starting on 0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT)