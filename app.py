# -------------------------------------------------
# app.py – Tibbir Forge Backend (Auth + Mint + Staking)
# -------------------------------------------------
from flask import Flask, request, jsonify
import requests
import os
import time
import logging
from web3 import Web3
from dotenv import load_dotenv

# -------------------------------------------------
# Load .env
# -------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)

# -------------------------------------------------
# Config
# -------------------------------------------------
MORALIS_KEY = os.getenv("MORALIS_KEY")
if not MORALIS_KEY:
    raise ValueError("MORALIS_KEY not set in .env")

ALCHEMY_KEY = os.getenv("ALCHEMY_KEY")
if not ALCHEMY_KEY:
    raise ValueError("ALCHEMY_KEY not set in .env")

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY not set in .env")

app = Flask(__name__)

# -------------------------------------------------
# Dynamic Port (Railway)
# -------------------------------------------------
PORT = int(os.getenv("PORT", 5000))

# -------------------------------------------------
# RPC (Base Sepolia – chainId 84532)
# -------------------------------------------------
RPC_URLS = [
    f"https://base-sepolia.g.alchemy.com/v2/{ALCHEMY_KEY}",
    "https://base-sepolia.blockpi.network/v1/rpc/public",
    "https://base-sepolia.drpc.org",
    "https://sepolia.base.org",
]

WEB3 = None
for url in RPC_URLS:
    try:
        w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
        if w3.is_connected() and w3.eth.chain_id == 84532:
            WEB3 = w3
            logging.info(f"Connected to Base Sepolia via: {url}")
            break
    except Exception as e:
        logging.warning(f"RPC failed ({url}): {e}")

if not WEB3:
    raise ConnectionError("No Base Sepolia RPC (chainId 84532) found.")

# -------------------------------------------------
# Contracts
# -------------------------------------------------
# $TIBBIR ERC-20 (replace with your token address)
TIBBIR_ADDRESS = "0xYourTibbirToken"  # ← UPDATE THIS

# Staking contract (deployed via Remix)
STAKING_ADDRESS = "0x4ED09B156d83625dc64FFdBc86A471eb72c3B627"

# $TIBBIR ERC-20 ABI
TIBBIR_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

# Staking ABI
STAKING_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "_tibbir", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}, {"internalType": "uint256", "name": "lockMonths", "type": "uint256"}],
        "name": "stake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "unstake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getVotingPower",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

tibbir = WEB3.eth.contract(address=TIBBIR_ADDRESS, abi=TIBBIR_ABI)
staking = WEB3.eth.contract(address=STAKING_ADDRESS, abi=STAKING_ABI)
ACCOUNT = WEB3.eth.account.from_key(PRIVATE_KEY)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def validate_address(addr):
    if not addr:
        return None
    try:
        return WEB3.to_checksum_address(addr.strip())
    except:
        return None

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
@app.route('/health')
def health():
    return jsonify({"status": "healthy", "time": time.time()}), 200

# -------------------------------------------------
# AUTHENTICATE
# -------------------------------------------------
@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.get_json() or {}
    address = validate_address(data.get('address', ''))
    if not address:
        return jsonify({"error": "invalid address"}), 400

    payload = {
        "chainId": "84531",
        "address": address,
        "domain": "tibbirforge.bubbleapps.io",
        "uri": "https://tibbirforge.bubbleapps.io",
        "statement": "Sign to authenticate for $TIBBIR Forge",
        "expiration": int(time.time()) + 120
    }

    headers = {"X-API-Key": MORALIS_KEY, "Content-Type": "application/json"}
    try:
        r = requests.post("https://auth.moralis.io/v2/wallets/challenge/request", json=payload, headers=headers, timeout=30)
        if r.status_code == 201:
            return jsonify(r.json()), 201
        else:
            return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------
# VERIFY
# -------------------------------------------------
@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json() or {}
    challenge_id = data.get('id')
    signature = data.get('signature')
    if not challenge_id or not signature:
        return jsonify({"error": "id and signature required"}), 400

    headers = {"X-API-Key": MORALIS_KEY, "Content-Type": "application/json"}
    payload = {"id": challenge_id, "signature": signature}

    try:
        r = requests.post("https://auth.moralis.io/v2/wallets/challenge/verify", json=payload, headers=headers, timeout=30)
        if r.status_code in (200, 201):
            return jsonify(r.json()), r.status_code
    except:
        pass

    try:
        r = requests.post("https://authapi.moralis.io/challenge/verify/evm", json=payload, headers=headers, timeout=30)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------
# MINT
# -------------------------------------------------
@app.route('/mint', methods=['POST'])
def mint_token():
    data = request.get_json() or {}
    address = validate_address(data.get('address'))
    metadata_uri = data.get('metadata_uri', '').strip()

    if not address or not metadata_uri:
        return jsonify({"error": "address and metadata_uri required"}), 400

    try:
        if WEB3.eth.chain_id != 84532:
            return jsonify({"error": f"Wrong chain {WEB3.eth.chain_id}"}, 500)

        nonce = WEB3.eth.get_transaction_count(ACCOUNT.address)
        tx = contract.functions.mint(
            address,
            metadata_uri,
            WEB3.to_wei(1, 'ether')
        ).build_transaction({
            'chainId': 84532,
            'gas': 300000,
            'gasPrice': WEB3.to_wei('0.1', 'gwei'),
            'nonce': nonce,
        })

        signed = WEB3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = WEB3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = WEB3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        token_id = "unknown"
        try:
            token_id = receipt.logs[0].topics[3].hex()[-32:]
            token_id = str(int(token_id, 16))
        except:
            pass

        result = {
            "status": "minted",
            "tx_hash": tx_hash.hex(),
            "explorer": f"https://sepolia.basescan.org/tx/{tx_hash.hex()}",
            "token_id": token_id
        }
        logging.info(f"Mint success: {result['tx_hash']}")
        return jsonify(result), 200

    except Exception as e:
        logging.exception("Mint failed")
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------
# STAKING ENDPOINTS
# -------------------------------------------------
@app.route('/balance', methods=['POST'])
def balance():
    data = request.get_json()
    addr = validate_address(data['address'])
    if not addr:
        return jsonify({"error": "invalid address"}), 400

    try:
        tibbir_bal = tibbir.functions.balanceOf(addr).call() / 1e18
        staked = staking.functions.balanceOf(addr).call() / 1e18
        ve = staking.functions.getVotingPower(addr).call() / 1e18
        return jsonify({"balance": tibbir_bal, "staked": staked, "veTIBBIR": ve})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/approve', methods=['POST'])
def approve():
    data = request.get_json()
    addr = validate_address(data['address'])
    amount = int(data['amount'] * 1e18)

    try:
        nonce = WEB3.eth.get_transaction_count(ACCOUNT.address)
        tx = tibbir.functions.approve(STAKING_ADDRESS, amount).build_transaction({
            'chainId': 84532,
            'gas': 100000,
            'gasPrice': WEB3.to_wei('0.1', 'gwei'),
            'nonce': nonce,
        })
        signed = WEB3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = WEB3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = WEB3.eth.wait_for_transaction_receipt(tx_hash)
        return jsonify({"tx_hash": tx_hash.hex()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stake', methods=['POST'])
def stake():
    data = request.get_json()
    addr = validate_address(data['address'])
    amount = int(data['amount'] * 1e18)
    months = data['lock_months']

    try:
        nonce = WEB3.eth.get_transaction_count(ACCOUNT.address)
        tx = staking.functions.stake(amount, months).build_transaction({
            'chainId': 84532,
            'gas': 300000,
            'gasPrice': WEB3.to_wei('0.1', 'gwei'),
            'nonce': nonce,
        })
        signed = WEB3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = WEB3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = WEB3.eth.wait_for_transaction_receipt(tx_hash)
        return jsonify({"tx_hash": tx_hash.hex()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/unstake', methods=['POST'])
def unstake():
    data = request.get_json()
    addr = validate_address(data['address'])

    try:
        nonce = WEB3.eth.get_transaction_count(ACCOUNT.address)
        tx = staking.functions.unstake().build_transaction({
            'chainId': 84532,
            'gas': 200000,
            'gasPrice': WEB3.to_wei('0.1', 'gwei'),
            'nonce': nonce,
        })
        signed = WEB3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = WEB3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = WEB3.eth.wait_for_transaction_receipt(tx_hash)
        return jsonify({"tx_hash": tx_hash.hex()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------
# Run
# -------------------------------------------------
if __name__ == '__main__':
    logging.info(f"Starting Tibbir Forge on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)