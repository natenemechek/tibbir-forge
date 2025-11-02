# app.py – Tibbir Forge – REAL TIBBIR + AGENTIC PREDICTOR (NO ABI FILES)
from flask import Flask, request, jsonify, render_template_string
import os
import logging
from web3 import Web3
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

TIBBIR_ADDRESS = "0xa4a2e2ca3fbfe21aed83471d28b6f65a233c6e00"

# FULL TIBBIR ERC20 ABI (from Etherscan)
TIBBIR_ABI = json.loads('''[
  {"inputs":[],"stateMutability":"nonpayable","type":"constructor"},
  {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},
  {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},
  {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}
]''')

# STAKING ABI (your contract - paste full if different)
STAKING_ABI = json.loads('''[
  {"inputs":[{"internalType":"address","name":"_tibbir","type":"address"},{"internalType":"address","name":"_feeWallet","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},
  {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getVotingPower","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"uint256","name":"months","type":"uint256"}],"name":"stake","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"unstake","outputs":[],"stateMutability":"nonpayable","type":"function"}
]''')  # Add your full events/functions

def get_web3():
    global WEB3, ACCOUNT, tibbir, staking
    if WEB3:
        return WEB3

    ALCHEMY_KEY = os.getenv('ALCHEMY_KEY')
    PRIVATE_KEY = os.getenv('PRIVATE_KEY')
    STAKING_ADDRESS = os.getenv('STAKING_ADDRESS')

    if not ALCHEMY_KEY:
        logging.error("Missing ALCHEMY_KEY")
        return None

    w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"))
    if not w3.is_connected():
        return None

    if PRIVATE_KEY:
        ACCOUNT = w3.eth.account.from_key(PRIVATE_KEY)

    global tibbir
    tibbir = w3.eth.contract(address=w3.to_checksum_address(TIBBIR_ADDRESS), abi=TIBBIR_ABI)

    if STAKING_ADDRESS:
        global staking
        staking = w3.eth.contract(address=w3.to_checksum_address(STAKING_ADDRESS), abi=STAKING_ABI)

    WEB3 = w3
    return w3

# ... (keep your /, /health, /balance, /ai routes unchanged)

@app.route('/predict', methods=['POST'])
def predict_yield():
    ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_KEY:
        return jsonify({"error": "AI key missing"}), 500

    data = request.get_json() or {}
    address = data.get("address", "")
    months = data.get("months", 12)
    amount = float(data.get("amount", 0))

    w3 = get_web3()
    context = f"Stake {amount} TIBBIR for {months} months. 1% fee. veTIBBIR boost. Base TVL exploding. "
    if address and w3 and tibbir:
        try:
            bal = tibbir.functions.balanceOf(w3.to_checksum_address(address)).call() / 1e18
            context += f"User balance: {bal:.2f}. "
        except Exception as e:
            logging.warning(f"Balance fail: {e}")

    prompt = f"{context}Predict APY + compounded. Agentic: Gasless auto-compound, treasury ML swaps, omnichain migration. 3 bullets."

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
        logging.error(f"Claude fail: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))