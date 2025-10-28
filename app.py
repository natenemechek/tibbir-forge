# -------------------------------------------------
# app.py – Expert Token Forge (Auth + Verify + REAL MINT)
# -------------------------------------------------
from flask import Flask, request, jsonify
import requests
import os
import time
import logging
from web3 import Web3
from dotenv import load_dotenv

# ------------------- LOAD .ENV -------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)

# ------------------- CONFIG -------------------
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

# ------------------- RPC CONNECTION (REAL CHAIN ID = 84532) -------------------
REAL_CHAIN_ID = 84532
MORALIS_CHAIN_ID = "84531"  # ← Moralis still expects this

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
        if w3.is_connected():
            chain_id = w3.eth.chain_id
            if chain_id == REAL_CHAIN_ID:
                WEB3 = w3
                logging.info(f"Connected to Base Sepolia via: {url} (chainId: {chain_id})")
                break
            else:
                logging.warning(f"Skipping RPC: wrong chain ID {chain_id} at {url}")
    except Exception as e:
        logging.warning(f"RPC failed ({url}): {e}")
        continue

if not WEB3:
    raise ConnectionError(f"No RPC with chain ID {REAL_CHAIN_ID}. Check ALCHEMY_KEY.")

# ------------------- CONTRACT & WALLET -------------------
CONTRACT_ADDRESS = "0x61D2A8bD780d6F5a5F96F61860E562Fd0A80d00f"

ABI = [
    {
        "inputs": [{"internalType": "address", "name": "_tibbir", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "string", "name": "metadata", "type": "string"},
            {"internalType": "uint256", "name": "stakeAmount", "type": "uint256"}
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

contract = WEB3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)
ACCOUNT = WEB3.eth.account.from_key(PRIVATE_KEY)

# ------------------- MORALIS ENDPOINTS -------------------
ENDPOINTS = {
    "v2": {
        "challenge": "https://auth.moralis.io/v2/wallets/challenge/request",
        "verify": "https://auth.moralis.io/v2/wallets/challenge/verify"
    },
    "v1": {
        "challenge": "https://authapi.moralis.io/challenge/request/evm",
        "verify": "https://authapi.moralis.io/challenge/verify/evm"
    }
}

# ------------------- HELPERS -------------------
def validate_address(addr):
    if not addr:
        return None
    try:
        return WEB3.to_checksum_address(addr.strip())
    except:
        return None

def build_moralis_payload(address):
    return {
        "chainId": MORALIS_CHAIN_ID,  # ← 84531 for Moralis
        "address": address,
        "domain": "tibbirforge.bubbleapps.io",
        "uri": "https://tibbirforge.bubbleapps.io",
        "statement": "Sign to authenticate for $TIBBIR Forge",
        "expiration": int(time.time()) + 120
    }

def build_v1_payload(address):
    return {
        "chainId": MORALIS_CHAIN_ID,
        "provider": "walletconnect",
        "address": address,
        "domain": "tibbirforge.bubbleapps.io",
        "uri": "https://tibbirforge.bubbleapps.io",
        "statement": "Sign to authenticate for $TIBBIR Forge",
        "timeout": 120
    }

# ------------------- AUTHENTICATE -------------------
@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.get_json() or {}
    address = validate_address(data.get('address', ''))
    if not address:
        return jsonify({"error": "invalid or missing address"}), 400

    headers = {"X-API-Key": MORALIS_KEY, "Content-Type": "application/json"}

    # Try v2
    try:
        r = requests.post(
            ENDPOINTS["v2"]["challenge"],
            json=build_moralis_payload(address),
            headers=headers,
            timeout=15
        )
        if r.status_code == 201:
            return jsonify(r.json()), 201
    except:
        pass

    # Try v1
    try:
        r = requests.post(
            ENDPOINTS["v1"]["challenge"],
            json=build_v1_payload(address),
            headers=headers,
            timeout=15
        )
        if r.status_code == 201:
            return jsonify(r.json()), 201
        else:
            return jsonify({"error": "auth failed", "detail": r.json()}), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- VERIFY -------------------
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
        r = requests.post(ENDPOINTS["v2"]["verify"], json=payload, headers=headers, timeout=15)
        if r.status_code in (200, 201):
            return jsonify(r.json()), r.status_code
    except:
        pass

    try:
        r = requests.post(ENDPOINTS["v1"]["verify"], json=payload, headers=headers, timeout=15)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- MINT TOKEN -------------------
@app.route('/mint', methods=['POST'])
def mint_token():
    data = request.get_json() or {}
    address = validate_address(data.get('address'))
    metadata_uri = data.get('metadata_uri', '').strip()

    if not address or not metadata_uri:
        return jsonify({"error": "address and metadata_uri required"}), 400

    try:
        if WEB3.eth.chain_id != REAL_CHAIN_ID:
            return jsonify({"error": f"Wrong chain {WEB3.eth.chain_id}, need {REAL_CHAIN_ID}"}), 500

        nonce = WEB3.eth.get_transaction_count(ACCOUNT.address)
        tx = contract.functions.mint(
            address,
            metadata_uri,
            WEB3.to_wei(1, 'ether')
        ).build_transaction({
            'chainId': REAL_CHAIN_ID,  # ← 84532
            'gas': 300_000,
            'gasPrice': WEB3.to_wei('0.1', 'gwei'),
            'nonce': nonce,
        })

        signed_tx = WEB3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = WEB3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = WEB3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        try:
            token_id = receipt.logs[0].topics[3].hex()[-32:]
            token_id = str(int(token_id, 16))
        except:
            token_id = "unknown"

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

# ------------------- RUN -------------------
if __name__ == '__main__':
    print("Expert Token Forge API Running on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)