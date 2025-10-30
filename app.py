from flask import Flask, jsonify
import os
import logging
import time

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
PORT = int(os.getenv("PORT", 5000))

@app.route('/health')
def health():
    logging.info("Health check")
    return jsonify({"status": "healthy"}), 200

@app.route('/')
def home():
    return jsonify({"message": "LIVE"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)