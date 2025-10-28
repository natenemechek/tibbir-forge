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
# DYNAMIC PORT (Railway)
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
# $TIBBIR ERC‑20 (replace with your token address)
TIBBIR_ADDRESS = "0xYourTibbirToken"  # ← UPDATE THIS

# Staking contract (deployed via Remix)
STAKING_ADDRESS = "0x4ED09B156d83625dc64FFdBc86A471eb72c3B627"

# Minimal ERC‑20 ABI
TIBBIR_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

# Staking ABI
STAKING_ABI = [
    {"inputs": [{"internalType": "address", "name": "_tibbir", "type": "address"}], "stateMutability": "nonpayable", "type": "constructor"},
    {"inputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}, {"internalType": "uint256", "name": "lockMonths", "type": "uint256"}], "name": "stake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "unstake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}], "name": "getVotingPower", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]

tibbir = WEB3.eth.contract(address=T...