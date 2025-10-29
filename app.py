# -------------------------------------------------
# app.py – Tibbir Forge (FULL PRODUCTION)
# -------------------------------------------------
from flask import Flask, request, jsonify
import requests
import os
import time
import logging
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

PORT = int(os.getenv("PORT", 5000))

# Lazy load
WEB3 = None
ACCOUNT = None
tibbir = None
staking = None

def get_web3():
    global WEB3, ACCOUNT, tibbir, staking
    if WEB3 is None:
        RPC_URLS = [
            f"https://base-sepolia.g.alchemy.com/v2/{os.getenv('ALCHEMY_KEY')}",
            "https://base-sepolia.blockpi.network/v1/rpc/public",
        ]
        for url in RPC_URLS:
            try:
                w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
                if w3.is_connected() and w3.eth.chain_id == 84532:
                    WEB3 = w3
                    ACCOUNT = w3.eth.account.from_key(os.getenv("PRIVATE_KEY"))
                    TIBBIR_ADDRESS = "0xYourTibbirToken"  # ← UPDATE
                    STAKING_ADDRESS = "0x4ED09B156d83625dc64FFdBc86A471eb72c3B627"
                    tibbir = w3.eth.contract(address=TIBBIR_ADDRESS, abi=TIBBIR_ABI)
                    staking = w3.eth.contract(address=STAKING_ADDRESS, abi=STAKING_ABI)
                    logging.info(f"Web3 connected: {url}")
                    break
            except:
                pass
        if not WEB3:
            logging.error("No RPC")
    return WEB3

# Health check
@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

# Authenticate
@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.get_json() or {}
    address = data.get('address', '').strip()
    if not address:
        return jsonify({"error": "address required"}), 400

    payload = {
        "chainId": "84531",
        "address": address,
        "domain": "tibbirforge.bubbleapps.io",
        "uri": "https://tibbirforge.bubbleapps.io",
        "statement": "Sign to authenticate",
        "expiration": int(time.time()) + 120
    }

    headers = {"X-API-Key": os.getenv("MORALIS_KEY"), "Content-Type": "application/json"}
    try:
        r = requests.post("https://auth.moralis.io/v2/wallets/challenge/request", json=payload, headers=headers, timeout=30)
        if r.status_code == 201:
            return jsonify(r.json()), 201
        else:
            return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Verify
@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json() or {}
    challenge_id = data.get('id')
    signature = data.get('signature')
    if not challenge_id or not signature:
        return jsonify({"error": "id and signature required"}), 400

    headers = {"X-API-Key": os.getenv("MORALIS_KEY"), "Content-Type": "application/json"}
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

# Mint
@app.route('/mint', methods=['POST'])
def mint_token():
    data = request.get_json() or {}
    address = data.get('address')
    metadata_uri = data.get('metadata_uri', '').strip()

    if not address or not metadata_uri:
        return jsonify({"error": "address and metadata_uri required"}), 400

    try:
        w3 = get_web3()
        if not w3:
            return jsonify({"error": "Web3 not available"}), 500

        if w3.eth.chain_id != 84532:
            return jsonify({"error": f"Wrong chain {w3.eth.chain_id}"}, 500)

        nonce = w3.eth.get_transaction_count(ACCOUNT.address)
        tx = contract.functions.mint(
            address,
            metadata_uri,
            w3.to_wei(1, 'ether')
        ).build_transaction({
            'chainId': 84532,
            'gas': 300000,
            'gasPrice': w3.to_wei('0.1', 'gwei'),
            'nonce': nonce,
        })

        signed = w3.eth.account.sign_transaction(tx, os.getenv("PRIVATE_KEY"))
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

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

# Balance
@app.route('/balance', methods=['POST'])
def balance():
    data = request.get_json()
    addr = data.get('address')
    if not addr:
        return jsonify({"error": "address required"}), 400

    try:
        w3 = get_web3()
        if not w3:
            return jsonify({"error": "Web3 not available"}), 500

        tibbir_bal = tibbir.functions.balanceOf(addr).call() / 1e18
        staked = staking.functions.balanceOf(addr).call() / 1e18
        ve = staking.functions.getVotingPower(addr).call() / 1e18
        return jsonify({"balance": tibbir_bal, "staked": staked, "veTIBBIR": ve})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Approve
@app.route('/approve', methods=['POST'])
def approve():
    data = request.get_json()
    addr = data.get('address')
    amount = int(data['amount'] * 1e18)

    try:
        w3 = get_web3()
        if not w3:
            return jsonify({"error": "Web3 not available"}), 500

        nonce = w3.eth.get_transaction_count(ACCOUNT.address)
        tx = tibbir.functions.approve(STAKING_ADDRESS, amount).build_transaction({
            'chainId': 84532,
            'gas': 100000,
            'gasPrice': w3.to_wei('0.1', 'gwei'),
            'nonce': nonce,
        })
        signed = w3.eth.account.sign_transaction(tx, os.getenv("PRIVATE_KEY"))
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return jsonify({"tx_hash": tx_hash.hex()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Stake
@app.route('/stake', methods=['POST'])
def stake():
    data = request.get_json()
    addr = data.get('address')
    amount = int(data['amount'] * 1e18)
    months = data['lock_months']

    try:
        w3 = get_web3()
        if not w3:
            return jsonify({"error": "Web3 not available"}), 500

        nonce = w3.eth.get_transaction_count(ACCOUNT.address)
        tx = staking.functions.stake(amount, months).build_transaction({
            'chainId': 84532,
            'gas': 300000,
            'gasPrice': w3.to_wei('0.1', 'gwei'),
            'nonce': nonce,
        })
        signed = w3.eth.account.sign_transaction(tx, os.getenv("PRIVATE_KEY"))
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return jsonify({"tx_hash": tx_hash.hex()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Unstake
@app.route('/unstake', methods=['POST'])
def unstake():
    data = request.get_json()
    addr = data.get('address')

    try:
        w3 = get_web3()
        if not w3:
            return jsonify({"error": "Web3 not available"}), 500

        nonce = w3.eth.get_transaction_count(ACCOUNT.address)
        tx = staking.functions.unstake().build_transaction({
            'chainId': 84532,
            'gas': 200000,
            'gasPrice': w3.to_wei('0.1', 'gwei'),
            'nonce': nonce,
        })
        signed = w3.eth.account.sign_transaction(tx, os.getenv("PRIVATE_KEY"))
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return jsonify({"tx_hash": tx_hash.hex()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logging.info(f"Starting on 0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT)