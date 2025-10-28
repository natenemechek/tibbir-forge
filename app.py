from flask import Flask, request, jsonify
import os
import time
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

PORT = int(os.getenv("PORT", 5000))

# Lazy globals
WEB3 = None
ACCOUNT = None
tibbir = None
staking = None

def lazy_load_web3():
    global WEB3, ACCOUNT, tibbir, staking
    if WEB3 is None:
        from web3 import Web3
        RPC_URLS = [
            f"https://base-sepolia.g.alchemy.com/v2/{os.getenv('ALCHEMY_KEY')}",
            "https://base-sepolia.blockpi.network/v1/rpc/public",
        ]
        for url in RPC_URLS:
            try:
                w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
                if w3.is_connected() and w3.eth.chain_id == 84532:
                    WEB3 = w3
                    ACCOUNT = w3.eth.account.from_key(os.getenv("PRIVATE_KEY"))
                    TIBBIR_ADDRESS = "0xYourTibbirToken"
                    STAKING_ADDRESS = "0x4ED09B156d83625dc64FFdBc86A471eb72c3B627"
                    tibbir = w3.eth.contract(address=TIBBIR_ADDRESS, abi=TIBBIR_ABI)
                    staking = w3.eth.contract(address=STAKING_ADDRESS, abi=STAKING_ABI)
                    logging.info(f"Web3 loaded: {url}")
                    break
            except:
                pass
        if not WEB3:
            logging.error("No RPC")
    return WEB3

# Health check (instant)
@app.route('/health')
def health():
    logging.info("Health check OK")
    return jsonify({"status": "healthy", "time": time.time()}), 200

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

# ... add verify, mint, staking endpoints from previous ...

if __name__ == '__main__':
    logging.info(f"Starting on 0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT)