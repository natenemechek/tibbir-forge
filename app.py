# app.py – Tibbir Forge – MINIMAL AGENTIC PREDICTOR (NO ABIs, NO FILES)
from flask import Flask, request, jsonify
import os
import logging
from web3 import Web3
from dotenv import load_dotenv
import httpx

load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

WEB3 = None
TIBBIR_ADDRESS = "0xa4a2e2ca3fbfe21aed83471d28b6f65a233c6e00"

def get_web3():
    global WEB3
    if WEB3:
        return WEB3
    ALCHEMY_KEY = os.getenv('ALCHEMY_KEY')
    if not ALCHEMY_KEY:
        logging.error("No ALCHEMY_KEY")
        return None
    w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"))
    if w3.is_connected() and w3.eth.chain_id == 8453:
        WEB3 = w3
        logging.info("WEB3 LIVE")
    return WEB3

@app.route('/')
def index():
    return "<h1>Tibbir Forge Agentic AI</h1><p>/health | /balance | /predict</p>"

@app.route('/health')
def health():
    w3 = get_web3()
    return jsonify({"status": "healthy" if w3 else "web3 down", "chain": "Base"})

@app.route('/balance', methods=['POST'])
def balance():
    data = request.get_json() or {}
    addr = data.get('address', '')
    if not addr:
        return jsonify({"error": "address required"}), 400
    try:
        addr = Web3.to_checksum_address(addr)
    except:
        return jsonify({"error": "invalid address"}), 400
    w3 = get_web3()
    if not w3:
        return jsonify({"error": "web3 down"}), 500
    try:
        bal = w3.eth.contract(address=w3.to_checksum_address(TIBBIR_ADDRESS), abi=[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]).functions.balanceOf(addr).call() / 1e18
        return jsonify({"balance": bal})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict_yield():
    ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_KEY:
        return jsonify({"error": "No AI key"}), 500
    data = request.get_json() or {}
    address = data.get("address", "")
    months = data.get("months", 12)
    amount = float(data.get("amount", 0))
    context = f"Stake {amount} TIBBIR for {months} months on Base. 1% fee. veBoost. TVL surging. "
    w3 = get_web3()
    if address and w3:
        try:
            addr = w3.to_checksum_address(address)
            bal = w3.eth.contract(address=w3.to_checksum_address(TIBBIR_ADDRESS), abi=[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]).functions.balanceOf(addr).call() / 1e18
            context += f"User has {bal:.2f} TIBBIR. "
        except:
            pass
    prompt = f"{context}Predict compounded APY. Agentic FinTech: Gasless auto-restake, treasury AI swaps, omnichain yields. 3 bullets, 2030 vision."
    try:
        resp = httpx.post("https://api.anthropic.com/v1/messages", headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }, json={
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 250,
            "messages": [{"role": "user", "content": prompt}]
        }, timeout=30)
        resp.raise_for_status()
        answer = resp.json()["content"][0]["text"]
        return jsonify({"prediction": answer.strip(), "confidence": 9.9})
    except Exception as e:
        logging.error(f"Claude error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))