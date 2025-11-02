# app.py – Tibbir Forge TESTNET (Base Sepolia) + AI Predictor
from flask import Flask, request, jsonify, render_template_string
import os
import logging
from web3 import Web3
from pathlib import Path
import json
from dotenv import load_dotenv
import httpx

load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

WEB3 = None
ACCOUNT = None
tibbir = None
staking = None

def ensure_abi_files():
    abis_dir = Path(__file__).parent / "abis"
    abis_dir.mkdir(exist_ok=True)
    # ... (keep your existing tibbir_erc20.json and staking.json creation)

def get_web3():
    global WEB3, ACCOUNT, tibbir, staking
    if WEB3: return WEB3
    ensure_abi_files()

    ALCHEMY_KEY = os.getenv('ALCHEMY_KEY')  # Sepolia key
    PRIVATE_KEY = os.getenv('PRIVATE_KEY')
    STAKING_ADDRESS = os.getenv('STAKING_ADDRESS', '0xA274cDA0A8Dc75e0C9eC8d382ECb7506C71549b2')
    TIBBIR_ADDRESS = os.getenv('TIBBIR_ADDRESS')  # Mock address

    if not all([ALCHEMY_KEY, PRIVATE_KEY, TIBBIR_ADDRESS]):
        logging.error("Missing env: ALCHEMY_KEY, PRIVATE_KEY, TIBBIR_ADDRESS")
        return None

    rpc_url = f"https://base-sepolia.g.alchemy.com/v2/{ALCHEMY_KEY}"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected() or w3.eth.chain_id != 84532:
        logging.error("Not connected to Base Sepolia")
        return None

    ACCOUNT = w3.eth.account.from_key(PRIVATE_KEY)
    base_dir = Path(__file__).parent
    TIBBIR_ABI = json.load(open(base_dir / "abis" / "tibbir_erc20.json"))
    STAKING_ABI = json.load(open(base_dir / "abis" / "staking.json"))

    tibbir_addr = w3.to_checksum_address(TIBBIR_ADDRESS)
    staking_addr = w3.to_checksum_address(STAKING_ADDRESS)

    global tibbir, staking
    tibbir = w3.eth.contract(address=tibbir_addr, abi=TIBBIR_ABI)
    staking = w3.eth.contract(address=staking_addr, abi=STAKING_ABI)

    WEB3 = w3
    logging.info("WEB3 LIVE: Base Sepolia")
    return w3

# ... (keep your existing /, /health, /balance, /ai routes)

@app.route('/predict', methods=['POST'])
def predict_yield():
    ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_KEY:
        return jsonify({"error": "AI not configured"}), 500

    data = request.get_json() or {}
    address = data.get("address", "")
    months = data.get("months", 12)
    amount = data.get("amount", 0) or 0

    w3 = get_web3()
    if not w3: return jsonify({"error": "Web3 down"}), 500

    context = f"Mock TIBBIR on Base Sepolia testnet. User stakes {amount} for {months} months. 1% fee, vePower boost. "
    if address:
        try:
            addr = w3.to_checksum_address(address)
            bal = tibbir.functions.balanceOf(addr).call() / 1e18
            staked = staking.functions.balanceOf(addr).call() / 1e18 if staking else 0
            context += f"Current: {bal:.2f} balance, {staked:.2f} staked. Base TVL simulations growing. "
        except: pass

    prompt = f"{context}Predict APY (5-20% test range + lock bonus). Innovative: Auto-restake via Chainlink Keepers, agentic treasury. 3 bullets."

    try:
        resp = httpx.post("https://api.anthropic.com/v1/messages", headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }, json={
            "model": "claude-3-haiku-20240307",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        }, timeout=30)
        resp.raise_for_status()
        answer = resp.json()["content"][0]["text"]
        return jsonify({"prediction": answer.strip()})
    except Exception as e:
        logging.error(f"AI failed: {e}")
        return jsonify({"error": "AI unavailable"}), 500

@app.route('/predict', methods=['POST'])
def predict_yield():
    ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_KEY:
        return jsonify({"error": "AI not configured"}), 500

    data = request.get_json() or {}
    address = data.get("address", "")
    months = data.get("months", 12)
    amount = data.get("amount", 0)

    context = f"TIBBIR on Base Mainnet. User stakes {amount} for {months} months. 1% fee, vePower boost. "
    if address:
        try:
            addr = Web3.to_checksum_address(address)
            bal = tibbir.functions.balanceOf(addr).call() / 1e18
            context += f"Current balance: {bal:.2f} TIBBIR. "
        except: pass

    prompt = f"{context}Predict APY (5-20% range + lock bonus). Innovative: Auto-restake via Chainlink Keepers, agentic treasury. 3 bullets."

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        resp.raise_for_status()
        answer = resp.json()["content"][0]["text"]
        return jsonify({"prediction": answer.strip()})
    except Exception as e:
        logging.error(f"AI failed: {e}")
        return jsonify({"error": "AI unavailable"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port)