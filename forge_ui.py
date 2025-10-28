import streamlit as st
import requests
import pandas as pd
import chardet
from io import StringIO

# ------------------- LIVE RAILWAY BACKEND -------------------
BASE_URL = "https://tibbir-forge-production.up.railway.app"

st.set_page_config(page_title="$TIBBIR Expert Token Forge", page_icon="🔥")

st.title("🔥 $TIBBIR Expert Token Forge")
st.markdown("**Mint your trading expertise as an ERC-404 token on Base Sepolia**")

# ------------------- SESSION STATE -------------------
if 'authResponse' not in st.session_state:
    st.session_state.authResponse = None
if 'verified' not in st.session_state:
    st.session_state.verified = False
if 'minted' not in st.session_state:
    st.session_state.minted = False
if 'metadata' not in st.session_state:
    st.session_state.metadata = None
if 'address' not in st.session_state:
    st.session_state.address = None

# ------------------- 1. WALLET CONNECTION -------------------
if not st.session_state.verified:
    address = st.text_input(
        "Wallet Address (Base Sepolia)",
        placeholder="0x...",
        help="Enter your MetaMask address on Base Sepolia"
    )

    if st.button("Connect Wallet", type="primary"):
        if not address:
            st.warning("Please enter a wallet address")
        else:
            with st.spinner("Requesting challenge from Moralis..."):
                try:
                    r = requests.post(f"{BASE_URL}/authenticate", json={"address": address})
                    if r.status_code == 201:
                        data = r.json()
                        st.session_state.authResponse = data
                        st.session_state.address = address
                        st.success("Challenge generated!")
                        st.code(data.get("message", "Sign in wallet"))
                    else:
                        st.error(f"Auth failed: {r.status_code}")
                        st.code(r.text)
                except Exception as e:
                    st.error("Connection failed")
                    st.code(str(e))

# ------------------- 2. DEMO SIGN (BYPASS) -------------------
if st.session_state.authResponse and not st.session_state.verified:
    st.info("**Demo Mode**: Click to bypass wallet signature")
    if st.button("Sign Challenge (DEMO)", type="secondary"):
        st.session_state.verified = True
        st.balloons()
        st.success("Wallet verified (demo mode)!")

# ------------------- 3. UPLOAD CSV & GENERATE METADATA -------------------
if st.session_state.verified and not st.session_state.metadata:
    st.markdown("### Upload Trade History (CSV)")
    uploaded = st.file_uploader(
        "Must have columns: **date, asset, profit**",
        type="csv",
        help="Save as **CSV UTF-8** in Excel"
    )

    if uploaded:
        with st.spinner("Reading CSV..."):
            try:
                raw = uploaded.getvalue()
                encoding = chardet.detect(raw)['encoding']
                st.info(f"Detected encoding: {encoding}")
                df = pd.read_csv(StringIO(raw.decode(encoding)))

                # Validate columns
                required = ['profit', 'asset']
                if not all(col.lower() in df.columns.str.lower() for col in required):
                    st.error(f"Missing columns. Need: {required}")
                else:
                    st.dataframe(df)

                    profit = df['profit'].sum()
                    top_asset = df['asset'].mode()[0]
                    summary = f"Pro trader: ${profit:,.0f} profit, top asset: {top_asset}"

                    st.session_state.metadata = summary
                    st.success("Metadata generated!")
                    st.markdown(f"**{summary}**")
            except Exception as e:
                st.error("Failed to read CSV")
                st.code(f"Save as **CSV UTF-8** in Excel.\nError: {e}")

# ------------------- 4. MINT TOKEN -------------------
if st.session_state.metadata and not st.session_state.minted:
    st.markdown("### Ready to Mint")
    st.write(st.session_state.metadata)

    if st.button("Mint Expert Token", type="primary"):
        metadata_uri = "ipfs://tibbir/" + st.session_state.metadata.replace(" ", "_")
        payload = {
            "address": st.session_state.address,
            "metadata_uri": metadata_uri
        }

        with st.spinner("Minting on Base Sepolia..."):
            try:
                m = requests.post(f"{BASE_URL}/mint", json=payload)
                if m.status_code == 200:
                    result = m.json()
                    st.session_state.minted = True
                    st.balloons()
                    st.success("**Expert Token Minted!**")
                    st.json(result)
                    st.markdown(f"[View on Basescan]({result['explorer']})")
                else:
                    st.error(f"Mint failed: {m.status_code}")
                    st.code(m.text)
            except Exception as e:
                st.error("Mint request failed")
                st.code(str(e))

# ------------------- 5. FINAL SUCCESS -------------------
if st.session_state.minted:
    st.markdown("## 🎉 **Your $TIBBIR Expert Token is LIVE on Base Sepolia!**")
    st.markdown("Share your expertise. Trade your reputation. Own your alpha.")
    st.markdown("---")
    st.caption("Built with ❤️ on Base | Powered by Moralis, Web3.py, Streamlit")