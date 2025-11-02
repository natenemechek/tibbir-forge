# app.py – Tibbir Forge – CRASH-PROOF AGENTIC PREDICTOR
from flask import Flask, request, jsonify
import os
import logging
from web3 import Web3
import httpx

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

TIBBIR_ADDRESS = "0xa4a2e2ca3fbfe21aed83471d28b6f65a233c6e00"
BALANCE_ABI = [{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]

@app.route('/')
def index():
    return "<h1>Tibbir Forge LIVE</h1><p>/health | POST /balance | POST /predict</p>"

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "chain": "Base", "token": "TIBBIR"})

@app.route('/balance', methods=['POST'])
def balance():
    data = request.get_json() or {}
    addr = data.get('address', '').strip()
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
        contract = w3.eth.contract(address=w3.to_checksum_address(TIBBIR_ADDRESS), abi=BALANCE_ABI)
        bal = contract.functions.balanceOf(addr).call() / 1e18
        return jsonify({"balance": bal})
    except Exception as e:
        logging.error(f"Balance error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict_yield():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        logging.error("No ANTHROPIC_API_KEY")
        return jsonify({"error": "AI key missing"}), 500

    data = request.get_json() or {}
    address = data.get("address", "")
    months = data.get("months", 12)
    amount = float(data.get("amount", 0))

    context = f"Stake {amount} TIBBIR for {months} months on Base. 1% treasury fee. veTIBBIR boost. TVL $335M+. "
    w3 = get_web3()
    if address and w3:
        try:
            addr = Web3.to_checksum_address(address)
            contract = w3.eth.contract(address=w3.to_checksum_address(TIBBIR_ADDRESS), abi=BALANCE_ABI)
            bal = contract.functions.balanceOf(addr).call() / 1e18
            context += f"User balance: {bal:.2f} TIBBIR. "
        except Exception as e:
            logging.warning(f"Balance in prompt: {e}")

    prompt = f"{context}Predict APY, compounded returns. 2030 agentic: ERC-4337 gasless auto-compound via Biconomy, treasury ML oracles swap fees omnichain (LayerZero), Virtuals AI signals for 500x efficiency. 3 bullets."

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-3-5-sonnet-20241022", "max_tokens": 250, "messages": [{"role": "user", "content": prompt}]},
            timeout=30
        )
        resp.raise_for_status()
        answer = resp.json()["content"][0]["text"]
        return jsonify({"prediction": answer.strip(), "agentic_confidence": 9.9})
    except Exception as e:
        logging.error(f"Claude error: {e}")
        return jsonify({"error": str(e)}), 500

def get_web3():
    key = os.getenv('ALCHEMY_KEY')
    if not key:
        logging.error("Missing ALCHEMY_KEY")
        return None
    try:
        w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.g.alchemy.com/v2/{key}", request_kwargs={'timeout': 10}))
        if w3.is_connected() and w3.eth.chain_id == 8453:
            logging.info("WEB3 LIVE")
            return w3
        logging.error("Web3 connect fail")
        return None
    except Exception as e:
        logging.error(f"Web3 init error: {e}")
        return None

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))