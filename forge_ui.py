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
# Load env (must be at the very top)
# -------------------------------------------------
load_dotenv()
GROK_API_KEY = os.getenv("GROK_API_KEY")
if not GROK_API_KEY:
    st.error("GROK_API_KEY not found in .env")
    st.stop()

BASE_URL = "https://tibbir-forge-production.up.railway.app"

st.set_page_config(page_title="$TIBBIR Elite Forge", page_icon="🧠")
st.title("🧠 $TIBBIR Elite Trader Forge")
st.markdown("**AI‑verified expertise → tiered NFT badges**")

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
            with st.spinner("Moralis challenge…"):
                r = requests.post(f"{BASE_URL}/authenticate", json={"address": address})
                if r.status_code == 201:
                    st.session_state.authResponse = r.json()
                    st.session_state.address = address
                    st.success("Challenge ready")
                    st.code(r.json().get("message", ""))
                else:
                    st.error(f"Auth failed – {r.status_code}")
                    st.code(r.text)

# -------------------------------------------------
# 2. Demo sign (bypass)
# -------------------------------------------------
if st.session_state.authResponse and not st.session_state.verified:
    if st.button("Sign Challenge (DEMO)", type="secondary"):
        st.session_state.verified = True
        st.balloons()
        st.success("Verified (demo)")

# -------------------------------------------------
# 3. CSV upload + EV calculation + Grok verdict
# -------------------------------------------------
if st.session_state.verified and not st.session_state.ai_score:
    st.markdown("### Upload Trade History (CSV)")
    uploaded = st.file_uploader(
        "Columns: **date, asset, entry_price, exit_price, quantity, side**",
        type="csv"
    )

    if uploaded:
        with st.spinner("Reading CSV…"):
            raw = uploaded.getvalue()
            enc = chardet.detect(raw)['encoding']
            df = pd.read_csv(StringIO(raw.decode(enc)))

            # ----- Basic validation -----
            req = ["date", "asset", "entry_price", "exit_price", "quantity", "side"]
            if not all(c.lower() in df.columns.str.lower() for c in req):
                st.error(f"Missing columns. Need: {req}")
                st.stop()

            st.dataframe(df)

            # ----- PnL per trade -----
            df["pnl"] = 0.0
            for i, row in df.iterrows():
                if row["side"].lower() == "buy":
                    df.loc[i, "pnl"] = (row["exit_price"] - row["entry_price"]) * row["quantity"]
                else:
                    df.loc[i, "pnl"] = (row["entry_price"] - row["exit_price"]) * row["quantity"]

            # ----- Core metrics -----
            total_pnl = df["pnl"].sum()
            wins = df[df["pnl"] > 0]["pnl"]
            losses = df[df["pnl"] < 0]["pnl"]
            win_rate = len(wins) / len(df) if len(df) else 0
            avg_win = wins.mean() if len(wins) else 0
            avg_loss = -losses.mean() if len(losses) else 0
            profit_factor = avg_win / avg_loss if avg_loss else float("inf")
            ev_per_trade = (avg_win * win_rate) - (avg_loss * (1 - win_rate))

            # ----- Sharpe (risk‑free = 0) -----
            returns = df["pnl"] / (df["entry_price"] * df["quantity"])
            sharpe = returns.mean() / returns.std() if returns.std() != 0 else 0

            # ----- Max Drawdown -----
            equity = (df["entry_price"] * df["quantity"]).cumsum() + df["pnl"].cumsum()
            peak = equity.cummax()
            drawdown = (equity - peak) / peak
            max_dd = drawdown.min() * 100  # percent

            # ----- Calmar -----
            annual_return = total_pnl / (df["quantity"] * df["entry_price"]).sum()
            calmar = annual_return / (-max_dd / 100) if max_dd < 0 else float("inf")

            # ----- Store for later -----
            metrics = {
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "ev_per_trade": ev_per_trade,
                "sharpe": sharpe,
                "max_dd": max_dd,
                "calmar": calmar,
                "trades": len(df),
            }

            # ----- GROK PROMPT (EV‑focused) -----
            prompt = f"""
You are a senior quant analyst. Using ONLY the numbers below, assign a badge (None / Bronze / Silver / Gold) and give a one‑sentence verdict.

Metrics:
- Total PnL: ${total_pnl:,.2f}
- Win Rate: {win_rate:.1%}
- Avg Win: ${avg_win:,.2f}
- Avg Loss: ${avg_loss:,.2f}
- EV per Trade: ${ev_per_trade:,.2f}
- Profit Factor: {profit_factor:.2f}
- Sharpe Ratio: {sharpe:.2f}
- Max Drawdown: {max_dd:.1f}%
- Calmar Ratio: {calmar:.2f}
- Trades: {len(df)}

Badge thresholds (must meet ALL):
- Bronze: EV>$100, PF>1.5, Trades>50
- Silver: EV>$500, Sharpe>1.5, PF>2.0
- Gold:   EV>$2,000, Calmar>3.0, Max DD<25%
"""

            with st.spinner("Asking Grok…"):
                grok_resp = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "grok-beta", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
                )
                if grok_resp.status_code == 200:
                    verdict = grok_resp.json()["choices"][0]["message"]["content"]
                else:
                    verdict = "Grok unavailable – using local thresholds."
                    st.warning("Grok call failed, falling back to local rules.")

            # ----- Local fallback badge -----
            badge = "None"
            if metrics["ev_per_trade"] > 2000 and metrics["calmar"] > 3.0 and metrics["max_dd"] > -25:
                badge = "Gold"
            elif metrics["ev_per_trade"] > 500 and metrics["sharpe"] > 1.5 and metrics["profit_factor"] > 2.0:
                badge = "Silver"
            elif metrics["ev_per_trade"] > 100 and metrics["profit_factor"] > 1.5 and metrics["trades"] > 50:
                badge = "Bronze"

            # ----- Store everything -----
            st.session_state.ai_score = {
                "metrics": metrics,
                "grok_verdict": verdict,
                "badge": badge,
            }

            st.success("Analysis complete!")
            st.markdown("### 📊 **Local Metrics**")
            st.json(metrics, expanded=False)
            st.markdown("### 🤖 **Grok Verdict**")
            st.write(verdict)
            st.markdown(f"### 🏅 **Badge: {badge}**")

# -------------------------------------------------
# 4. Mint tiered NFT (only if eligible)
# -------------------------------------------------
if st.session_state.ai_score and not st.session_state.minted:
    badge = st.session_state.ai_score["badge"]
    if badge != "None":
        st.markdown(f"### 🎖️ **Mint {badge} Trader NFT**")
        if st.button("Mint NFT", type="primary"):
            metadata = f"badge:{badge}|{st.session_state.ai_score['grok_verdict'].replace('|', ' ')}"
            payload = {
                "address": st.session_state.address,
                "metadata_uri": f"ipfs://tibbir/{badge.lower()}-{int(time.time())}|{metadata}",
            }
            with st.spinner("Minting…"):
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
        st.warning("Not eligible for a badge yet – keep trading!")

# -------------------------------------------------
# 5. Success screen
# -------------------------------------------------
if st.session_state.minted:
    st.markdown("## 🎉 **Elite Trader Status Achieved!**")
    st.caption("Built on Base • Powered by Grok • Verified on‑chain")