# app.py – Tibbir Forge – USES REAL TIBBIR ON BASE MAINNET
from flask import Flask, request, jsonify
import os
import logging
from web3 import Web3
from pathlib import Path
import json
from dotenv import load_dotenv
import httpx

# -------------------------------------------------
# 1. Load .env
# -------------------------------------------------
load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# -------------------------------------------------
# 2. Global objects (lazy loaded)
# -------------------------------------------------
WEB3 = None
ACCOUNT = None
tibbir = None
staking = None

# -------------------------------------------------
# 3. AUTO-CREATE ABI FILES
# -------------------------------------------------
def ensure_abi_files():
    abis_dir = Path(__file__).parent / "abis"
    abis_dir.mkdir(exist_ok=True)

    tibbir_path = abis_dir / "tibbir_erc20.json"
    staking_path = abis_dir / "staking.json"

    # FORCE RECREATE (clean files)
    for p in [tibbir_path, staking_path]:
        if p.exists():
            p.unlink()

    # REAL TIBBIR ERC20 ABI (OpenZeppelin standard)
    tibbir_abi = [
        {"inputs": [], "stateMutability": "nonpayable", "type": "constructor"},
        {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}, {"internalType": "uint256", "name": "allowance", "type": "uint256"}, {"internalType": "uint256", "name": "needed", "type": "uint256"}], "name": "ERC20InsufficientAllowance", "type": "error"},
        {"inputs": [{"internalType": "address", "name": "sender", "type": "address"}, {"internalType": "uint256", "name": "balance", "type": "uint256"}, {"internalType": "uint256", "name": "needed", "type": "uint256"}], "name": "ERC20InsufficientBalance", "type": "error"},
        {"inputs": [{"internalType": "address", "name": "approver", "type": "address"}], "name": "ERC20InvalidApprover", "type": "error"},
        {"inputs": [{"internalType": "address", "name": "receiver", "type": "address"}], "name": "ERC20InvalidReceiver", "type": "error"},
        {"inputs": [{"internalType": "address", "name": "sender", "type": "address"}], "name": "ERC20InvalidSender", "type": "error"},
        {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}], "name": "ERC20InvalidSpender", "type": "error"},
        {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "owner", "type": "address"}, {"indexed": True, "internalType": "address", "name": "spender", "type": "address"}, {"indexed": False, "internalType": "uint256", "name": "value", "type": "uint256"}], "name": "Approval", "type": "event"},
        {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "from", "type": "address"}, {"indexed": True, "internalType": "address", "name": "to", "type": "address"}, {"indexed": False, "internalType": "uint256", "name": "value", "type": "uint256"}], "name": "Transfer", "type": "event"},
        {"inputs": [{"internalType": "address", "name": "owner", "type": "address"}, {"internalType": "address", "name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"internalType": "address", "name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "decimals", "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "name", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "symbol", "outputs": [{"internalType": "string", "name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "totalSupply", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "transfer", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"internalType": "address", "name": "from", "type": "address"}, {"internalType": "address", "name": "to", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "transferFrom", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"}
    ]
    with open(tibbir_path, "w", encoding="utf-8") as f:
        json.dump(tibbir_abi, f, indent=2)
    logging.info("RECREATED tibbir_erc20.json (18 entries)")

    # YOUR STAKING ABI (9 functions)
    staking_abi = [
        {"inputs": [{"internalType": "address", "name": "_tibbir", "type": "address"}], "stateMutability": "nonpayable", "type": "constructor"},
        {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "user", "type": "address"}, {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}, {"indexed": False, "internalType": "uint256", "name": "lockMonths", "type": "uint256"}], "name": "Staked", "type": "event"},
        {"anonymous": False, "inputs": [{"indexed": True, "internalType": "address", "name": "user", "type": "address"}, {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "Unstaked", "type": "event"},
        {"inputs": [{"internalType": "address", "name": "user", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"internalType": "address", "name": "user", "type": "address"}], "name": "getVotingPower", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}, {"internalType": "uint256", "name": "lockMonths", "type": "uint256"}], "name": "stake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [], "name": "unstake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [], "name": "tibbir", "outputs": [{"internalType": "contract IERC20", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "totalStaked", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
    ]
    with open(staking_path, "w", encoding="utf-8") as f:
        json.dump(staking_abi, f, indent=2)
    logging.info("RECREATED staking.json (9 entries)")

# -------------------------------------------------
# 4. Web3 INIT – BASE MAINNET
# -------------------------------------------------
def get_web3():
    global WEB3, ACCOUNT, tibbir, staking
    if WEB3 is not None:
        return WEB3

    logging.info("=== INITIALIZING WEB3 (BASE MAINNET) ===")
    ensure_abi_files()

    ALCHEMY_KEY = os.getenv('ALCHEMY_KEY')
    PRIVATE_KEY = os.getenv('PRIVATE_KEY')
    STAKING_ADDRESS = os.getenv('STAKING_ADDRESS')  # Your deployed staking

    if not all([ALCHEMY_KEY, PRIVATE_KEY, STAKING_ADDRESS]):
        logging.error("Missing .env: ALCHEMY_KEY, PRIVATE_KEY, STAKING_ADDRESS")
        return None

    # BASE MAINNET RPC
    w3 = None
    for url in [
        f"https://base-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}",
        "https://mainnet.base.org"
    ]:
        try:
            cand = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
            if cand.is_connected() and cand.eth.chain_id == 8453:
                w3 = cand
                logging.info(f"Web3 CONNECTED: {url}")
                break
        except Exception as e:
            logging.error(f"RPC failed: {e}")

    if not w3:
        return None

    try:
        ACCOUNT = w3.eth.account.from_key(PRIVATE_KEY)
        logging.info(f"Account: {ACCOUNT.address}")
    except Exception as e:
        logging.error(f"Invalid PRIVATE_KEY: {e}")
        return None

    base_dir = Path(__file__).parent
    try:
        TIBBIR_ABI = json.load(open(base_dir / "abis" / "tibbir_erc20.json"))
        STAKING_ABI = json.load(open(base_dir / "abis" / "staking.json"))
        logging.info(f"ABIs loaded: TIBBIR={len(TIBBIR_ABI)}, STAKING={len(STAKING_ABI)}")
    except Exception as e:
        logging.error(f"ABI load failed: {e}")
        return None

    # REAL TIBBIR – FORCE CHECKSUM (web3.py bug workaround)
    TIBBIR_ADDRESS_RAW = "0xa4a2e2ca3fbfe21aed83471d28b6f65a233c6e00"
    try:
        TIBBIR_ADDRESS = w3.to_checksum_address(TIBBIR_ADDRESS_RAW)
        tibbir = w3.eth.contract(address=TIBBIR_ADDRESS, abi=TIBBIR_ABI)
        logging.info(f"TIBBIR attached: {TIBBIR_ADDRESS}")
    except Exception as e:
        logging.error(f"TIBBIR attach failed: {e}")
        return None

    # YOUR STAKING
    try:
        staking = w3.eth.contract(address=STAKING_ADDRESS, abi=STAKING_ABI)
        logging.info(f"STAKING attached: {STAKING_ADDRESS}")
    except Exception as e:
        logging.warning(f"STAKING attach failed: {e} → using mock mode")
        staking = None

    WEB3 = w3
    logging.info("=== WEB3 LIVE (BASE MAINNET) ===")
    return WEB3

# -------------------------------------------------
# 5. ENDPOINTS
# -------------------------------------------------
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "chain": "Base Mainnet", "token": "TIBBIR"}), 200

@app.route('/balance', methods=['POST'])
def balance():
    data = request.get_json() or {}
    addr = data.get('address', '').strip()
    if not addr:
        return jsonify({"error": "address required"}), 400

    try:
        addr = Web3.to_checksum_address(addr)
        logging.info(f"Checksummed: {addr}")
    except:
        return jsonify({"error": "Invalid address"}), 400

    w3 = get_web3()
    if not w3:
        return jsonify({"error": "Web3 not available"}), 500

    try:
        bal = tibbir.functions.balanceOf(addr).call() / 1e18
    except Exception as e:
        logging.error(f"TIBBIR balance failed: {e}")
        bal = 0.0

    staked = 0.0
    ve = 0.0
    if staking:
        try:
            staked = staking.functions.balanceOf(addr).call() / 1e18
            ve = staking.functions.getVotingPower(addr).call() / 1e18
        except Exception as e:
            logging.warning(f"Staking call failed: {e} → returning 0")
            staked = ve = 0.0

    logging.info(f"RESULT → balance={bal:.6f}, staked={staked:.6f}, veTIBBIR={ve:.6f}")
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

    context = f"TIBBIR is a real token on Base with $335M market cap. "
    if address:
        try:
            addr = Web3.to_checksum_address(address)
            bal = tibbir.functions.balanceOf(addr).call() / 1e18
            context += f"User holds {bal:.2f} TIBBIR. "
        except:
            pass

    prompt = f"{context}Question: {question}\nAnswer in 2 sentences:"

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

# -------------------------------------------------
# 6. RUN
# -------------------------------------------------
if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    logging.info(f"Starting on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)