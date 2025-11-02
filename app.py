# app.py – Tibbir Forge – GUNICORN-READY AGENTIC PREDICTOR
from flask import Flask, request, jsonify
import os
import logging
from web3 import Web3
import httpx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TIBBIR_ADDRESS = "0xa4a2e2ca3fbfe21aed83471d28b6f65a233c6e00"
BALANCE_ABI = [{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]

@app.route('/')
def index():
    return "<h1>Tibbir Forge AGENTIC LIVE</h1><p>/health | POST /balance | POST /predict</p>"

@app.route('/health')
def health():
    w3 = get_web3()
    status = "healthy" if w3 else "web3 down"
    logger.info(f"Health check: {status}")
    return jsonify({"status": status, "chain": "Base", "token": "TIBBIR"})

@app.route('/balance', methods=['POST'])
def balance():
    data = request.get_json() or {}
    addr = data.get('address', '').strip()
    if not addr:
        return jsonify({"error": "address required"}), 400
    try:
        addr = Web3.to_checksum_address(addr)
    except Exception as e:
        logger.error(f"Invalid address: {e}")
        return jsonify({"error": "invalid address"}), 400

    w3 = get_web3()
    if not w3:
        return jsonify({"error": "web3 down"}), 500

    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(TIBBIR_ADDRESS), abi=BALANCE_ABI)
        bal = contract.functions.balanceOf(addr).call() / 1e18
        logger.info(f"Balance for {addr}: {bal}")
        return jsonify({"balance": round(bal, 2)})
    except Exception as e:
        logger.error(f"Balance error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict_yield():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        logger.error("Missing ANTHROPIC_API_KEY")
        return jsonify({"error": "AI key missing"}), 500

    data = request.get_json() or {}
    address = data.get("address", "")
    months = int(data.get("months", 12))
    amount = float(data.get("amount", 0))

    context = f"Stake {amount} TIBBIR for {months} months on Base. 1% fee. veBoost. TVL $335M+. "
    w3 = get_web3()
    if address and w3:
        try:
            addr = w3.to_checksum_address(address)
            contract = w3.eth.contract(address=Web3.to_checksum_address(TIBBIR_ADDRESS), abi=BALANCE_ABI)
            bal = contract.functions.balanceOf(addr).call() / 1e18
            context += f"User balance: {bal:.2f} TIBBIR. "
        except Exception as e:
            logger.warning(f"Balance in prompt failed: {e}")

    prompt = f"{context}Predict compounded APY + returns. Agentic 2030: Gasless ERC-4337 auto-compound (Biconomy), treasury ML oracles swap 1% fees omnichain (LayerZero), Virtuals AI signals for 1000x efficiency in $1T DeFi. 3 bullets."

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=40
        )
        resp.raise_for_status()
        answer = resp.json()["content"][0]["text"]
        logger.info("Claude prediction generated")
        return jsonify({"prediction": answer.strip(), "agentic_confidence": 9.9})
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return jsonify({"error": str(e)}), 500

def get_web3():
    alchemy_key = os.getenv('ALCHEMY_KEY')
    if not alchemy_key:
        logger.error("Missing ALCHEMY_KEY")
        return None
    try:
        w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.g.alchemy.com/v2/{alchemy_key}", request_kwargs={'timeout': 15}))
        if w3.is_connected() and w3.eth.chain_id == 8453:
            logger.info("WEB3 CONNECTED TO BASE")
            return w3
        logger.error("Web3 connection failed: wrong chain or disconnect")
        return None
    except Exception as e:
        logger.error(f"Web3 init crash: {e}")
        return None

# No if __name__ for gunicorn