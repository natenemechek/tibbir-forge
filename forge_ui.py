import streamlit as st
import requests
import pandas as pd
import chardet
import numpy as np
import os
from io import StringIO
from dotenv import load_dotenv
import time

# -------------------------------------------------
# Load .env (for local testing)
# -------------------------------------------------
load_dotenv()

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
BASE_URL = "https://tibbir-forge-production.up.railway.app"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    st.error("ANTHROPIC_API_KEY not found in .env")
    st.info("Get your key at https://console.anthropic.com")
    st.stop()

st.set_page_config(page_title="Tibbir Elite Forge", page_icon="🔥")
st.title("🔥 Tibbir Elite Trader Forge")
st.markdown("**AI‑verified expertise → On‑chain NFT badges**")

# -------------------------------------------------
# Session state
# -------------------------------------------------
for k in ["authResponse", "verified", "minted", "address", "ai_score"]:
    if k not in st.session_state:
        st.session_state[k] = None if k != "verified" and k != "minted" else False

# -------------------------------------------------
# 1. Wallet connection
# -------------------------------------------------
if not st.session_state.verified:
    address = st.text_input("Wallet (Base Sepolia)", placeholder="0x...")
    if st.button("Connect Wallet", type="primary"):
        if not address:
            st.warning("Enter address")
        else:
            with st.spinner("Requesting challenge..."):
                r = requests.post(f"{BASE_URL}/authenticate", json={"address": address})
                if r.status_code == 201:
                    st.session_state.authResponse = r.json()
                    st.session_state.address = address
                    st.success("Challenge ready!")
                    st.code(r.json().get("message", ""))
                else:
                    st.error(f"Auth failed: {r.status_code}")
                    st.code(r.text)

# -------------------------------------------------
# 2. Demo sign
# -------------------------------------------------
if st.session_state.authResponse and not st.session_state.verified:
    if st.button("Sign Challenge (DEMO)", type="secondary"):
        st.session_state.verified = True
        st.balloons()
        st.success("Verified (demo)!")

# -------------------------------------------------
# 3. CSV + Claude AI Scoring
# -------------------------------------------------
if st.session_state.verified and not st.session_state.ai_score:
    st.markdown("### Upload Trade History (CSV)")
    uploaded = st.file_uploader("Columns: date, asset, entry_price, exit_price, quantity, side", type="csv")

    if uploaded:
        with st.spinner("Reading CSV..."):
            raw = uploaded.getvalue()
            enc = chardet.detect(raw)['encoding']
            df = pd.read_csv(StringIO(raw.decode(enc)))

            # Validate
            req = ["date", "asset", "entry_price", "exit_price", "quantity", "side"]
            if not all(c.lower() in df.columns.str.lower() for c in req):
                st.error(f"Missing columns. Need: {req}")
                st.stop()

            st.dataframe(df)

            # PnL
            df["pnl"] = 0.0
            for i, row in df.iterrows():
                if row["side"].lower() == "buy":
                    df.loc[i, "pnl"] = (row["exit_price"] - row["entry_price"]) * row["quantity"]
                else:
                    df.loc[i, "pnl"] = (row["entry_price"] - row["exit_price"]) * row["quantity"]

            # Metrics
            total_pnl = df["pnl"].sum()
            wins = df[df["pnl"] > 0]["pnl"]
            losses = df[df["pnl"] < 0]["pnl"]
            win_rate = len(wins) / len(df) if len(df) else 0
            avg_win = wins.mean() if len(wins) else 0
            avg_loss = -losses.mean() if len(losses) else 0
            profit_factor = avg_win / avg_loss if avg_loss else float("inf")
            ev_per_trade = (avg_win * win_rate) - (avg_loss * (1 - win_rate))
            returns = df["pnl"] / (df["entry_price"] * df["quantity"])
            sharpe = returns.mean() / returns.std() if returns.std() != 0 else 0
            equity = (df["entry_price"] * df["quantity"]).cumsum() + df["pnl"].cumsum()
            peak = equity.cummax()
            drawdown = (equity - peak) / peak
            max_dd = drawdown.min() * 100
            annual_return = total_pnl / (df["quantity"] * df["entry_price"]).sum()
            calmar = annual_return / (-max_dd / 100) if max_dd < 0 else float("inf")

            # Claude Prompt
            prompt = f"""
You are a senior quant. Return JSON only with:
{{
  "ev_per_trade": {ev_per_trade:.2f},
  "sharpe": {sharpe:.2f},
  "profit_factor": {profit_factor:.2f},
  "max_dd_percent": {max_dd:.1f},
  "calmar": {calmar:.2f},
  "badge": "Gold" or "Silver" or "Bronze" or "None",
  "verdict": "One sentence"
}}

Metrics:
- Total PnL: ${total_pnl:,.2f}
- Win Rate: {win_rate:.1%}
- EV/Trade: ${ev_per_trade:,.2f}
- Trades: {len(df)}

Badge rules:
- Gold: EV>$2000, Calmar>3.0, Max DD<25%
- Silver: EV>$500, Sharpe>1.5, PF>2.0
- Bronze: EV>$100, PF>1.5, Trades>50
"""

            with st.spinner("Asking Claude..."):
                headers = {
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 300,
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": prompt}]
                }
                r = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
                if r.status_code == 200:
                    result = r.json()["content"][0]["text"]
                    try:
                        ai_data = json.loads(result)
                    except:
                        ai_data = {"badge": "None", "verdict": "AI error"}
                else:
                    ai_data = {"badge": "None", "verdict": "Claude unavailable"}

            # Local fallback
            badge = "None"
            if ev_per_trade > 2000 and calmar > 3.0 and max_dd > -25:
                badge = "Gold"
            elif ev_per_trade > 500 and sharpe > 1.5 and profit_factor > 2.0:
                badge = "Silver"
            elif ev_per_trade > 100 and profit_factor > 1.5 and len(df) > 50:
                badge = "Bronze"

            st.session_state.ai_score = {
                "metrics": {
                    "ev_per_trade": ev_per_trade,
                    "sharpe": sharpe,
                    "profit_factor": profit_factor,
                    "max_dd": max_dd,
                    "calmar": calmar
                },
                "ai": ai_data,
                "badge": badge
            }

            st.success("Analysis complete!")
            st.json(st.session_state.ai_score["metrics"])
            st.markdown(f"### 🏅 **Badge: {badge}**")
            st.write(ai_data.get("verdict", ""))

# -------------------------------------------------
# 4. Mint NFT
# -------------------------------------------------
if st.session_state.ai_score and not st.session_state.minted:
    badge = st.session_state.ai_score["badge"]
    if badge != "None":
        st.markdown(f"### Mint {badge} Trader NFT")
        if st.button("Mint NFT", type="primary"):
            metadata = f"badge:{badge}|{st.session_state.ai_score['ai'].get('verdict', '')}"
            payload = {
                "address": st.session_state.address,
                "metadata_uri": f"ipfs://tibbir/{badge.lower()}-{int(time.time())}|{metadata}"
            }
            with st.spinner("Minting..."):
                m = requests.post(f"{BASE_URL}/mint", json=payload)
                if m.status_code == 200:
                    result = m.json()
                    st.session_state.minted = True
                    st.balloons()
                    st.success(f"**{badge} NFT minted!**")
                    st.json(result)
                    st.markdown(f"[View on Basescan]({result['explorer']})")
                else:
                    st.error("Mint failed")
                    st.code(m.text)
    else:
        st.warning("Not eligible yet")

# -------------------------------------------------
# Success
# -------------------------------------------------
if st.session_state.minted:
    st.markdown("## 🎉 **Elite Status Achieved!**")
    st.caption("Powered by Claude AI • On‑chain proof")