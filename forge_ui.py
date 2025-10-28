import streamlit as st
import requests
import pandas as pd
import time

st.title("Expert Token Forge")

# Initialize session state
for key in ['authResponse', 'verified', 'minted', 'metadata', 'address']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'verified' and key != 'minted' else False

# === 1. Connect Wallet ===
if not st.session_state.verified:
    address = st.text_input("Wallet Address (Base Sepolia)", value=st.session_state.address or "")
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Connect", key="connect_btn"):
            if not address:
                st.warning("Enter address")
            else:
                with st.spinner("Contacting Moralis..."):
                    r = requests.post("http://127.0.0.1:5000/authenticate", json={"address": address})
                    if r.status_code == 201:
                        st.session_state.authResponse = r.json()
                        st.session_state.address = address
                        st.success("Challenge generated!")
                        st.code(r.json().get("challenge", {}).get("message"))
                    else:
                        st.error(f"Failed: {r.status_code}")
                        try:
                            st.json(r.json())
                        except:
                            st.code(r.text)

# === 2. Demo Sign (Bypass) ===
if st.session_state.authResponse and not st.session_state.verified:
    if st.button("Sign Challenge (Demo Mode)", key="demo_sign"):
        st.session_state.verified = True
        st.balloons()
        st.success("Verified (demo)!")

# === 3. Upload CSV & Generate Metadata ===
if st.session_state.verified and not st.session_state.metadata:
    st.write("### Upload Trade History CSV (Save as UTF-8!)")
    uploaded = st.file_uploader(
        "CSV with columns: date, asset, profit", 
        type="csv",
        help="Save your file in Excel as 'CSV UTF-8' to avoid errors"
    )
    if uploaded:
        try:
            # Auto-detect encoding
            import chardet
            raw = uploaded.getvalue()
            encoding = chardet.detect(raw)['encoding']
            st.info(f"Detected encoding: {encoding}")

            # Read with detected encoding
            from io import StringIO
            df = pd.read_csv(StringIO(raw.decode(encoding)))
            
        except Exception as e:
            st.error("CSV read failed. Try saving as **CSV UTF-8** in Excel.")
            st.code(str(e))
            df = None

        if df is not None and 'profit' in df.columns and 'asset' in df.columns:
            st.dataframe(df)
            profit = df['profit'].sum()
            top = df['asset'].mode()[0] if not df['asset'].empty else "N/A"
            summary = f"Pro trader: ${profit:,.0f} profit, top asset: {top}"
            st.session_state.metadata = summary
            st.success("Metadata ready!")
            st.write(summary)
        else:
            st.warning("CSV must have 'profit' and 'asset' columns")

# === 4. Mint Token ===
if st.session_state.metadata and not st.session_state.minted:
    if st.button("Mint Expert Token", key="mint_btn"):
        meta_uri = "ipfs://fake/" + st.session_state.metadata.replace(" ", "_")
        payload = {
            "address": st.session_state.address,
            "metadata_uri": meta_uri
        }
        with st.spinner("Minting on Base Sepolia..."):
            m = requests.post("http://127.0.0.1:5000/mint", json=payload)
            if m.status_code == 200:
                result = m.json()
                st.session_state.minted = True
                st.balloons()
                st.success("Minted!")
                st.json(result)
                st.markdown(f"[View on Basescan]({result['explorer']})")
            else:
                st.error("Mint failed")
                st.code(m.text)

if st.session_state.minted:
    st.write("**Your $TIBBIR Expert Token is live on Base Sepolia!**")