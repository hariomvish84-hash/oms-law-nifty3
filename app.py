import os
import sys
import time
import logging
import pyotp
import pandas as pd
import streamlit as st
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ============================================================
# 🔐 LOAD SECURE CREDENTIALS
# ============================================================
load_dotenv()

# ============================================================
# बैकग्राउंड एरर्स को ब्लॉक करना
# ============================================================
logging.getLogger("SmartApi").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')

try:
    from SmartApi import SmartConnect
except ImportError:
    SmartConnect = None

# ============================================================
# 🖥️ पेज कॉन्फ़िगरेशन
# ============================================================
st.set_page_config(
    page_title="OM'S LAW 2.0 - NIFTY LIVE",
    layout="wide"
)

# ============================================================
# 🎨 सीएसएस थीम सेटिंग्स
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f8f9fa; }

    h1, h2, h3, h4, h5, h6, p, span, label, td, th {
        color: #000000 !important;
        font-family: monospace !important;
    }

    table {
        width: 100%;
        border: 1px solid #d1d5db !important;
        border-collapse: collapse;
        background-color: white;
        margin-bottom: 20px;
    }

    td, th {
        border: 1px solid #d1d5db !important;
        padding: 12px !important;
        vertical-align: top;
    }

    .stTable {
        width: 100% !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# निफ्टी लॉट साइज और सेटिंग्स
# ============================================================
qty = 25

# ============================================================
# 💰 मेमोरी स्टेट्स
# ============================================================
if "v_position" not in st.session_state:
    st.session_state.v_position = "None"

if "v_pnl" not in st.session_state:
    st.session_state.v_pnl = 0.0

if "v_wallet" not in st.session_state:
    st.session_state.v_wallet = 100000.0

if "oi_history" not in st.session_state:
    st.session_state.oi_history = {}

# ============================================================
# फिक्स स्टार्टिंग 09:15 मेमोरी
# ============================================================
if "start_time_base" not in st.session_state:
    st.session_state.start_time_base = datetime.combine(
        datetime.today(),
        datetime.min.time()
    ).replace(
        hour=9,
        minute=15,
        second=0
    )

if "time_columns_list" not in st.session_state:
    st.session_state.time_columns_list = [
        (
            st.session_state.start_time_base
            + timedelta(seconds=i * 2)
        ).strftime("%H:%M:%S")
        for i in range(6)
    ]

# ============================================================
# 🔐 ANGEL ONE SESSION
# ============================================================
@st.cache_resource
def get_angel_session():

    if SmartConnect is None:
        return None

    try:

        # Credentials .env से आएंगे
        api_key = os.environ.get("ANGEL_API_KEY")
        client_id = os.environ.get("ANGEL_CLIENT_ID")
        password = os.environ.get("ANGEL_PASSWORD")
        totp_key = os.environ.get("ANGEL_TOTP_KEY")

        if not all([
            api_key,
            client_id,
            password,
            totp_key
        ]):
            return None

        smart_connect = SmartConnect(
            api_key=api_key
        )

        totp = pyotp.TOTP(
            totp_key
        ).now()

        data = smart_connect.generateSession(
            client_id,
            password,
            totp
        )

        if data and data.get("status"):
            return smart_connect

        return None

    except Exception:
        return None


smart_connect = get_angel_session()

# ============================================================
# 🖥️ SIDEBAR CONTROLS
# ============================================================
st.sidebar.markdown(
    "### 🤖 NIFTY ALGO PANEL"
)

algo_active = st.sidebar.toggle(
    "🟢 एल्गो रोबोट चालू करें",
    value=False
)

st.sidebar.markdown(
    "### 📈 NIFTY VIRTUAL CONTROLS"
)

lot_size = st.sidebar.number_input(
    "📦 लॉट साइज चुनें (Lots):",
    min_value=1,
    max_value=100,
    value=1,
    step=1
)

qty = lot_size * 25

col_btn1, col_btn2 = st.sidebar.columns(2)

with col_btn1:

    if st.button("🟩 BUY NIFTY CE"):

        st.session_state.v_position = "NIFTY CE"
        st.session_state.v_pnl = 0.0

with col_btn2:

    if st.button("🟥 BUY NIFTY PE"):

        st.session_state.v_position = "NIFTY PE"
        st.session_state.v_pnl = 0.0

if st.sidebar.button("⬜ CLOSE POSITION"):

    if st.session_state.v_position != "None":

        st.session_state.v_wallet += (
            st.session_state.v_pnl * qty
        )

    st.session_state.v_position = "None"
    st.session_state.v_pnl = 0.0

placeholder = st.empty()

with placeholder.container():

    # ========================================================
    # 📡 लाइव निफ्टी स्पॉट
    # ========================================================

    try:

        spot_res = (
            smart_connect.ltpData(
                "NSE",
                "Nifty 50",
                "99926000"
            )
            if smart_connect
            else None
        )

        nifty_spot = (
            float(spot_res["data"]["ltp"])
            if spot_res and spot_res.get("data")
            else 23270.60
        )

    except Exception:

        nifty_spot = 23270.60

    # ========================================================
    # एटीएम और 2 स्ट्राइक ऊपर/नीचे
    # ========================================================

    atm_strike = int(
        round(nifty_spot / 50) * 50
    )

    strikes = [
        atm_strike - 100,
        atm_strike - 50,
        atm_strike,
        atm_strike + 50,
        atm_strike + 100
    ]

    # ========================================================
    # टाइम ग्रिड
    # ========================================================

    st.session_state.start_time_base += timedelta(
        seconds=np.random.randint(1, 5)
    )

    next_timestamp = (
        st.session_state.start_time_base
        .strftime("%H:%M:%S")
    )

    st.session_state.time_columns_list.pop(0)

    st.session_state.time_columns_list.append(
        next_timestamp
    )

    # ========================================================
    # वर्चुअल ट्रेड लाभ/हानि
    # ========================================================

    if st.session_state.v_position != "None":

        st.session_state.v_pnl += np.random.uniform(
            -1.5,
            2.0
        )

        if st.session_state.v_pnl >= 30.0:

            st.session_state.v_wallet += (
                30.0 * qty
            )

            st.session_state.v_position = (
                "None (Target Hit! 🎉)"
            )

            st.session_state.v_pnl = 0.0

        elif st.session_state.v_pnl <= -15.0:

            st.session_state.v_wallet += (
                -15.0 * qty
            )

            st.session_state.v_position = (
                "None (Stoploss Hit! 🛑)"
            )

            st.session_state.v_pnl = 0.0

    total_money_pnl = (
        st.session_state.v_pnl * qty
        if "NIFTY" in st.session_state.v_position
        else 0.0
    )

    pnl_color = (
        "green"
        if st.session_state.v_pnl >= 0
        else "red"
    )

    # ========================================================
    # मुख्य हेडर
    # ========================================================

    st.markdown(
        """
        <h1 style="
            text-align: center;
            font-weight: bold;
            color: blue;
            margin-bottom: 5px;
        ">
            OM'S LAW 2.0
        </h1>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <h3 style="
            text-align: center;
            font-weight: bold;
            color: green;
            margin-top: 0px;
        ">
            📊 NIFTY 50 LIVE TRADING PANEL
        </h3>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # मुख्य समरी टेबल
    # ========================================================

    st.markdown(
        f"""
        <table>

          <tr>

            <td style="width: 25%;">
                <b>INDEX: NIFTY 50 🟢</b>
            </td>

            <td style="width: 25%;">
                <b>NIFTY SPOT: ₹ {nifty_spot}</b>
            </td>

            <td style="width: 25%;">
                <b>EXPIRY: 17SEP2026</b>
            </td>

            <td style="
                width: 25%;
                background-color: #fef8f8;
            ">

                <b>📊 LIVE P&L (लाभ/हानि)</b>
                <br>

                💼 Pos:

                <span style="
                    color:blue;
                    font-weight:bold;
                ">
                    {st.session_state.v_position}
                </span>

                <br>

                💰 Amt:

                <span style="
                    color:{pnl_color};
                    font-weight:bold;
                ">
                    ₹ {np.round(total_money_pnl, 2)}
                </span>

            </td>

          </tr>

        </table>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # 5 STRIKE PRICES DATA
    # ========================================================

    for strike in strikes:

        st.markdown(
            f"""
            ### 🎯 NIFTY Strike {strike}
            {'⭐ (ATM)' if strike == atm_strike else ''}
            """
        )

        # ====================================================
        # FIXED INITIAL VALUES
        # ====================================================

        if strike not in st.session_state.oi_history:

            st.session_state.oi_history[strike] = {

                "call": [
                    120,
                    145,
                    132,
                    160,
                    175,
                    190
                ],

                "put": [
                    -190,
                    -158,
                    -200,
                    -250,
                    -290,
                    -500
                ]

            }

        d = st.session_state.oi_history[strike]

        # ====================================================
        # LIVE DATA CHANGE
        # ====================================================

        d["call"].pop(0)

        d["call"].append(
            int(
                d["call"][-1]
                + np.random.randint(-4, 6)
            )
        )

        d["put"].pop(0)

        d["put"].append(
            int(
                d["put"][-1]
                + np.random.randint(-6, 4)
            )
        )

        # ====================================================
        # DATA TIME TABLE GRID
        # ====================================================

        table_df = pd.DataFrame(
            [
                d["call"],
                d["put"]
            ],
            columns=st.session_state.time_columns_list,
            index=[
                "NIFTY Call OI",
                "NIFTY Put OI"
            ]
        )

        st.table(table_df)

        st.markdown(
            "<div style='margin-bottom: 20px;'></div>",
            unsafe_allow_html=True
        )

# ============================================================
# 🔄 SCREEN REFRESH
# ============================================================

time.sleep(2)

st.rerun()
