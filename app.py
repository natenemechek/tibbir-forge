# app.py – Tibbir Forge – REAL TIBBIR + AGENTIC AI PREDICTOR (FIXED INDENTS)
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

    # Recreate for safety
    for p in [tibbir_path, staking_path]:
        if p.exists():
            p.unlink()

    # FULL TIBBIR ERC20 ABI (paste your 18-entry array here)
    tibbir_abi = [
        # ... YOUR FULL ABI FROM EARLIER (balanceOf, approve, etc.)
    ]
    with open(tibbir_path, "w", encoding="utf-8") as f:
        json.dump(tibbir_abi, f, indent=2)
    logging.info("Recreated tibbir_erc20.json")

    # STAKING ABI (for 1% fee contract)
    staking_abi = [
        # ... YOUR FULL 9-ENTRY ABI
    ]
    with open(staking_path, "w", encoding="utf-8") as f:
        json.dump(staking_abi, f, indent=2)
    logging.info("Recreated staking.json")

def get_web3():
    global WEB3, ACCOUNT, tibbir, staking
    if WEB3 is not None:
        return WEB3

    ensure_abi_files()

    ALCHEMY_KEY = os.getenv('ALCHEMY_KEY')
    PRIVATE_KEY = os.getenv('PRIVATE_KEY')
    STAKING_ADDRESS = os.getenv('STAKING_ADDRESS')

    if not all([ALCHEMY_KEY, PRIVATE_KEY]):
        logging.error("Missing ALCHEMY_KEY or PRIVATE_KEY")
        return None

    rpc_url = f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
    if not w3.is_connected() or w3.eth.chain_id != 8453:
        logging.error("Not connected to Base Mainnet")
        return None

    try:
        ACCOUNT = w3.eth.account.from_key(PRIVATE_KEY)
        logging.info(f"Account loaded: {ACCOUNT.address}")
    except Exception as e:
        logging.error(f"Private key invalid: {e}")
        return None

    base_dir = Path(__file__).parent
    try:
        TIBBIR_ABI = json.load(open(base_dir / "abis" / "tibbir_erc20.json"))
        STAKING_ABI = json.load(open(base_dir / "abis" / "staking.json"))
    except Exception as e:
        logging.error(f"ABI load failed: {e}")
        return None

    TIBBIR_ADDRESS = w3.to_checksum_address("0xa4a2e2ca3fbfe21aed83471d28b6f65a233c6e00")
    global tibbir
    tibbir = w3.eth.contract(address=TIBBIR_ADDRESS, abi=TIBBIR_ABI)
    logging.info(f"TIBBIR attached: {TIBBIR_ADDRESS}")

    if STAKING_ADDRESS:
        staking_addr = w3.to_checksum_address(STAKING_ADDRESS)
        global staking
        staking = w3.eth.contract(address=staking_addr, abi=STAKING_ABI)
        logging.info(f"Staking attached: {staking_addr}")
    else:
        logging.warning("No STAKING_ADDRESS - staking calls disabled")

    WEB3 = w3
    logging.info("WEB3 LIVE on Base Mainnet")
    return w3

@app.route('/')
def index():
    return render_template_string("""
    <h1>Tibbir Forge — Agentic AI Staking on Base</h1>
    <p>Real TIBBIR ($314M) + Autonomous Yield Agents</p>
    <ul>
        <li>POST /balance {"address": "0x..."}</li>
        <li>POST /predict {"address": "0x...", "months": 12, "amount": 500}</li>
        <li>POST /ai {"question": "..."}</li>
    </ul>
    """)

@app.route('/health')
def health():
    w3 = get_web3()
    status = "healthy" if w3 else "web3 down"
    return jsonify({"status": status, "chain": "Base Mainnet", "token": "TIBBIR"})

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
        return jsonify({"error": "web3 unavailable"}), 500

    bal = 0.0
    try:
        bal = tibbir.functions.balanceOf(addr).call() / 1e18
    except Exception as e:
        logging.warning(f"Balance call failed: {e}")

    staked = 0.0
    ve = 0.0
    if staking:
        try:
            staked = staking.functions.balanceOf(addr).call() / 1e18
            ve = staking.functions.getVotingPower(addr).call() / 1e18
        except Exception as e:
            logging.warning(f"Staking call failed: {e}")

    return jsonify({"balance": bal, "staked": staked, "veTIBBIR": ve})

@app.route('/ai', methods=['POST'])
def ai_explain():
    ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_KEY:
        return jsonify({"error": "AI not configured"}), 500

    data = request.get_json() or {}
    question = data.get("question", "").strip()
    address = data.get("address", "")

    if not question:
        return jsonify({"error": "question required"}), 400

    context = "TIBBIR on Base Mainnet ($314M cap). "
    w3 = get_web3()
    if address and w3 and tibbir:
        try:
            addr = w3.to_checksum_address(address)
            bal = tibbir.functions.balanceOf(addr).call() / 1e18
            context += f"User has {bal:.2f} TIBBIR. "
        except:
            pass

    prompt = f"{context}Question: {question}. Answer innovatively for 2030 FinTech."

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
                "max_tokens": 150,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        resp.raise_for_status()
        answer = resp.json()["content"][0]["text"]
        return jsonify({"answer": answer.strip()})
    except Exception as e:
        logging.error(f"AI failed: {e}")
        return jsonify({"error": "AI unavailable"}), 500

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
    context = f"Stake {amount} TIBBIR for {months} months on Base. 1% treasury fee. veTIBBIR boost. "
    if address and w3:
        try:
            addr = w3.to_checksum_address(address)
            bal = tibbir.functions.balanceOf(addr).call() / 1e18
            context += f"User balance: {bal:.2f}. "
        except:
            pass

    # Mock oracle (future: Coingecko API or Chainlink)
    context += "TIBBIR ~$0.00067. Base gas low. TVL growing 20% MoM. "

    prompt = f"{context}Predict APY + compounded returns. Agentic 2030 vision: ERC-4337 gasless agents auto-compound via flash loans, treasury DAOs swap fees with ML predictions, omnichain migration via LayerZero. 3 bullets."

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 250,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        resp.raise_for_status()
        answer = resp.json()["content"][0]["text"]
        return jsonify({"prediction": answer.strip(), "agentic_confidence": 9.7})
    except Exception as e:
        logging.error(f"Predictor failed: {e}")
        return jsonify({"error": "Agent down"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    logging.info(f"Starting Waitress on port {port}")
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)