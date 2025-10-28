import streamlit as st
import requests
import time
from web3 import Web3

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
BASE_URL = "https://tibbir-forge-production.up.railway.app"
TIBBIR_ADDRESS = "0xYourTibbirContract"  # ← Replace with real $TIBBIR ERC-20
STAKING_CONTRACT = "0xYourStakingContract"  # ← Deployed below

st.set_page_config(page_title="Tibbir Staking", page_icon="🔥")
st.title("🔥 $TIBBIR Staking Dashboard")
st.markdown("**Stake to reduce fees, earn yield, and govern the Forge**")

# -------------------------------------------------
# Connect Wallet
# -------------------------------------------------
if 'address' not in st.session_state:
    st.session_state.address = None

address = st.text_input("Wallet (Base Sepolia)", value=st.session_state.address or "")
if st.button("Connect"):
    if Web3.is_address(address):
        st.session_state.address = address
        st.success("Connected!")
    else:
        st.error("Invalid address")

if not st.session_state.address:
    st.stop()

# -------------------------------------------------
# Load Balances
# -------------------------------------------------
with st.spinner("Loading balances..."):
    try:
        bal = requests.post(f"{BASE_URL}/balance", json={"address": address, "token": TIBBIR_ADDRESS})
        if bal.status_code == 200:
            data = bal.json()
            tibbir_balance = data["balance"]
            staked = data.get("staked", 0)
            ve_tibbir = data.get("veTIBBIR", 0)
            discount = min(75, ve_tibbir // 1000)  # 1 veTIBBIR = 0.1% discount
        else:
            st.error("Failed to load balance")
            st.stop()
    except:
        st.error("Backend error")
        st.stop()

# -------------------------------------------------
# UI
# -------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Wallet $TIBBIR", f"{tibbir_balance:,.2f}")
with col2:
    st.metric("Staked", f"{staked:,.2f}")
with col3:
    st.metric("veTIBBIR", f"{ve_tibbir:,.0f}")

st.markdown(f"### Fee Discount: **{discount}%**")

# -------------------------------------------------
# Stake
# -------------------------------------------------
st.markdown("### Stake $TIBBIR")
amount = st.number_input("Amount to stake", min_value=0.0, value=0.0, step=1.0)
lock_months = st.slider("Lock duration (months)", 1, 36, 12)

if st.button("Stake", type="primary"):
    if amount <= 0:
        st.warning("Enter amount")
    elif amount > tibbir_balance:
        st.error("Not enough $TIBBIR")
    else:
        with st.spinner("Approving & staking..."):
            # 1. Approve
            approve = requests.post(f"{BASE_URL}/approve", json={
                "address": st.session_state.address,
                "spender": STAKING_CONTRACT,
                "amount": amount,
                "token": TIBBIR_ADDRESS
            })
            if approve.status_code != 200:
                st.error("Approve failed")
                st.code(approve.text)
                st.stop()

            # 2. Stake
            stake = requests.post(f"{BASE_URL}/stake", json={
                "address": st.session_state.address,
                "amount": amount,
                "lock_months": lock_months
            })
            if stake.status_code == 200:
                st.balloons()
                st.success(f"Staked {amount:,.2f} $TIBBIR for {lock_months} months!")
                st.json(stake.json())
            else:
                st.error("Stake failed")
                st.code(stake.text)

# -------------------------------------------------
# Unstake
# -------------------------------------------------
st.markdown("### Unstake")
if staked > 0:
    if st.button("Unstake All"):
        with st.spinner("Unstaking..."):
            unstake = requests.post(f"{BASE_URL}/unstake", json={"address": st.session_state.address})
            if unstake.status_code == 200:
                st.success("Unstaked!")
            else:
                st.error("Failed")
                st.code(unstake.text)
else:
    st.info("No $TIBBIR staked")

# -------------------------------------------------
# Governance
# -------------------------------------------------
st.markdown("### Governance")
if ve_tibbir > 0:
    st.write(f"You have **{ve_tibbir:,.0f} veTIBBIR** voting power")
    proposal = st.text_area("Propose change (e.g., 'Lower EV threshold to $300')")
    if st.button("Submit Proposal"):
        st.success("Proposal submitted to DAO!")
else:
    st.info("Stake $TIBBIR to vote")