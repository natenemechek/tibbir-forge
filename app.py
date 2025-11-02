# app.py – Tibbir Forge – REAL TIBBIR + AGENTIC AI PREDICTOR (NO DUPLICATES)
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

WEB3 = None
ACCOUNT = None
tibbir = None
staking = None

def ensure_abi_files():
    abis_dir = Path(__file__).parent / "abis"
    abis_dir.mkdir(exist_ok=True)

    tibbir_path = abis_dir / "tibbir_erc20.json"
    staking_path = abis_dir / "staking.json"

    for p in [tibbir_path, staking_path]:
        if p.exists():
            p.unlink()

    tibbir_abi = [  # (your full ERC20 ABI - shortened for brevity, paste full from earlier)
        # ... FULL TIBBIR ABI HERE (18 entries)
    ]
    with open(tibbir_path, "w") as f:
        json.dump(tibbir_abi, f, indent=2)

    staking_abi = [  # UPDATED FOR FEE CONTRACT
        # ... FULL STAKING ABI (9 entries)
    ]
    with open(staking_path, "w") as f:
        json.dump(staking_abi, f, indent=2)

def get_web3():
    global WEB3, ACCOUNT, tibbir, staking
    if WEB3: return WEB3
    ensure_abi_files()

    ALCHEMY_KEY = os.getenv('ALCHEMY_KEY')
    PRIVATE_KEY = os.getenv('PRIVATE_KEY')
    STAKING_ADDRESS = os.getenv('STAKING_ADDRESS')
    TIBBIR_ADDRESS_RAW = "0xa4a2e2ca3fbfe21aed83471d28b6f65a233c6e00"

    if not all([ALCHEMY_KEY, PRIVATE_KEY, STAKING_ADDRESS]):
        logging.error("Missing env vars")
        return None

    w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"))
    if not w3.is_connected() or w3.eth.chain_id != 8453:
        return None

    ACCOUNT = w3.eth.account.from_key(PRIVATE_KEY)
    TIBBIR_ABI = json.load(open(Path(__file__).parent / "abis" / "tibbir_erc20.json"))
    STAKING_ABI = json.load(open(Path(__file__).parent / "abis" / "staking.json"))

    TIBBIR_ADDRESS = w3.to_checksum_address(TIBBIR_ADDRESS_RAW)
    tibbir = w3.eth.contract(address=TIBBIR_ADDRESS, abi=TIBBIR_ABI)
    staking = w3.eth.contract(address=STAKING_ADDRESS, abi=STAKING_ABI)

    WEB3 = w3
    return w3

@app.route('/')
def index():
    return render_template_string("""<h1>Tibbir Forge — Agentic Staking on Base</h1><p>Real TIBBIR + AI Yield Agents</p>""")

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "chain": "Base Mainnet"})

@app.route('/balance', methods=['POST'])
def balance():
    # (your existing balance code - keep unchanged)
    # ...

@app.route('/ai', methods=['POST'])
def ai_explain():
    # (your existing AI code - keep unchanged)
    # ...

# SINGLE, UPGRADED /predict — AGENTIC YIELD ENGINE
@app.route('/predict', methods=['POST'])
def predict_yield():
    ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_KEY:
        return jsonify({"error": "AI key missing"}), 500

    data = request.get_json() or {}
    address = data.get("address", "")
    months = data.get("months", 12)
    amount = data.get("amount", 0)

    w3 = get_web3()
    context = f"TIBBIR ($314M cap on Base). Stake {amount} for {months} months. 1% fee to treasury. "
    if address and w3 and tibbir:
        try:
            addr = w3.to_checksum_address(address)
            bal = tibbir.functions.balanceOf(addr).call() / 1e18
            context += f"User balance: {bal:.2f}. "
        except: pass

    # FUTURE: Pull real oracle (mock for now)
    tibbir_price = 0.00067  # Coingecko mock - add API later
    context += f"TIBBIR @ ${tibbir_price:.5f}. Base gas: 0.01 gwei. "

    prompt = f"{context}Predict compounded APY with veTIBBIR boost. Innovative agentic FinTech: ERC-4337 gasless auto-restake, Chainlink Keepers compounding, treasury AI agents swapping fees during dips. 3 bullets, 2030 vision."

    try:
        resp = httpx.post("https://api.anthropic.com/v1/messages", headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }, json={
            "model": "claude-3-5-sonnet-20241022",  # Upgrade to latest for deeper reasoning
            "max_tokens": 250,
            "messages": [{"role": "user", "content": prompt}]
        }, timeout=30)
        resp.raise_for_status()
        answer = resp.json()["content"][0]["text"]
        return jsonify({"prediction": answer.strip(), "agentic_score": 9.8})  # Mock confidence
    except Exception as e:
        logging.error(f"AI error: {e}")
        return jsonify({"error": "Agent unavailable"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port)