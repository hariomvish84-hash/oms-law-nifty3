import os
import sys
import time
import logging
import pyotp
import pandas as pd
import streamlit as st
import numpy as np
from datetime import datetime, timedelta

# ============================================================
# 🚀 AUTO-RUN SETTING
# ============================================================
if __name__ == "__main__":
    if not os.environ.get("STREAMLIT_RUNNING"):
        os.environ["STREAMLIT_RUNNING"] = "True"

        import subprocess

        subprocess.run([
            sys.executable,
            "-m",
            "streamlit",
            "run",
            os.path.abspath(__file__)
        ])

        sys.exit()


# ============================================================
# 🔇 LOGGING
# ============================================================
logging.getLogger("SmartApi").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.CRITICAL)

# NOTE:
# sys.stderr को बंद नहीं किया गया है ताकि वास्तविक errors दिखाई दें.


# ============================================================
# 📡 ANGEL ONE SMART API
# ============================================================
try:
    from SmartApi import SmartConnect
except ImportError:
    SmartConnect = None


# ============================================================
# 🖥️ PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="OM'S LAW 2.0 - NIFTY LIVE",
    layout="wide"
)


# ============================================================
# 🎨 CSS THEME
# ============================================================
st.markdown(
    """
    <style>

    .stApp {
        background-color: #f8f9fa;
    }

    h1, h2, h3, h4, h5, h6,
    p, span, label, td, th {
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
# ⚙️ BASIC SETTINGS
# ============================================================
BASE_LOT_SIZE = 25


# ============================================================
# 💾 SESSION STATE
# ============================================================
if "v_position" not in st.session_state:
    st.session_state.v_position = "None"

if "v_pnl" not in st.session_state:
    st.session_state.v_pnl = 0.0

if "v_wallet" not in st.session_state:
    st.session_state.v_wallet = 100000.0

if "oi_history" not in st.session_state:
    st.session_state.oi_history = {}

if "start_time_base" not in st.session_state:
    st.session_state.start_time_base = (
        datetime.combine(
            datetime.today(),
            datetime.min.time()
        ).replace(
            hour=9,
            minute=15,
            second=0
        )
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
# 🔐 ANGEL ONE LOGIN
# ============================================================
@st.cache_resource
def get_angel_session():

    if SmartConnect is None:
        return None

    try:
        # Environment variables से credentials लें
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

        totp = pyotp.TOTP(totp_key).now()

        data = smart_connect.generateSession(
            client_id,
            password,
            totp
        )

        if data and data.get("status"):
            return smart_connect

        return None

    except Exception as e:
        logging.error(
            "Angel One login failed: %s",
            e
        )
        return None


smart_connect = get_angel_session()


# ============================================================
# 📊 SIDEBAR
# ============================================================
st.sidebar.markdown("### 🤖 NIFTY ALGO PANEL")

algo_active = st.sidebar.toggle(
    "🟢 एल्गो रोबोट चालू करें",
    value=False
)

st.sidebar.markdown(
    "### 📈 NIFTY VIRTUAL CONTROLS"
)


# ============================================================
# 📦 LOT SIZE
# ============================================================
lot_size = st.sidebar.number_input(
    "📦 लॉट साइज चुनें (Lots):",
    min_value=1,
    max_value=100,
    value=1,
    step=1
)

qty = lot_size * BASE_LOT_SIZE


# ============================================================
# 🟢 BUY BUTTONS
# ============================================================
col_btn1, col_btn2 = st.sidebar.columns(2)

with col_btn1:

    if st.button(
        "🟩 BUY NIFTY CE",
        use_container_width=True
    ):

        st.session_state.v_position = "NIFTY CE"
        st.session_state.v_pnl = 0.0


with col_btn2:

    if st.button(
        "🟥 BUY NIFTY PE",
        use_container_width=True
    ):

        st.session_state.v_position = "NIFTY PE"
        st.session_state.v_pnl = 0.0


# ============================================================
# ⬜ CLOSE POSITION
# ============================================================
if st.sidebar.button(
    "⬜ CLOSE POSITION",
    use_container_width=True
):

    if st.session_state.v_position in [
        "NIFTY CE",
        "NIFTY PE"
    ]:

        st.session_state.v_wallet += (
            st.session_state.v_pnl * qty
        )

    st.session_state.v_position = "None"
    st.session_state.v_pnl = 0.0


# ============================================================
# 📡 MAIN DISPLAY
# ============================================================
placeholder = st.empty()

with placeholder.container():

    # ========================================================
    # 📡 LIVE NIFTY SPOT
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

        if (
            spot_res
            and spot_res.get("data")
            and spot_res["data"].get("ltp") is not None
        ):

            nifty_spot = float(
                spot_res["data"]["ltp"]
            )

        else:
            nifty_spot = 23270.60

    except Exception as e:

        logging.error(
            "NIFTY LTP error: %s",
            e
        )

        nifty_spot = 23270.60


    # ========================================================
    # 🎯 ATM STRIKE
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
    # ⏱️ TIME GRID
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
    # 💰 VIRTUAL P&L
    # ========================================================
    if st.session_state.v_position in [
        "NIFTY CE",
        "NIFTY PE"
    ]:

        st.session_state.v_pnl += np.random.uniform(
            -1.5,
            2.0
        )

        # ----------------------------
        # 🎯 TARGET
        # ----------------------------
        if st.session_state.v_pnl >= 30.0:

            st.session_state.v_wallet += (
                30.0 * qty
            )

            st.session_state.v_position = (
                "None (Target Hit! 🎉)"
            )

            st.session_state.v_pnl = 0.0


        # ----------------------------
        # 🛑 STOPLOSS
        # ----------------------------
        elif st.session_state.v_pnl <= -15.0:

            st.session_state.v_wallet += (
                -15.0 * qty
            )

            st.session_state.v_position = (
                "None (Stoploss Hit! 🛑)"
            )

            st.session_state.v_pnl = 0.0


    # ========================================================
    # 💵 TOTAL MONEY P&L
    # ========================================================
    total_money_pnl = (
        st.session_state.v_pnl * qty
        if st.session_state.v_position in [
            "NIFTY CE",
            "NIFTY PE"
        ]
        else 0.0
    )

    pnl_color = (
        "green"
        if st.session_state.v_pnl >= 0
        else "red"
    )


    # ========================================================
    # 🏷️ HEADER
    # ========================================================
    st.markdown(
        """
        <h1 style="
            text-align:center;
            font-weight:bold;
            color:blue;
            margin-bottom:5px;
        ">
            OM'S LAW 2.0
        </h1>
        """,
        unsafe_allow_html=True
    )


    st.markdown(
        """
        <h3 style="
            text-align:center;
            font-weight:bold;
            color:green;
            margin-top:0px;
        ">
            📊 NIFTY 50 LIVE TRADING PANEL
        </h3>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # 📊 SUMMARY BOX
    # ========================================================
    st.markdown(
        f"""
        <table>

            <tr>

                <td style="width:25%;">
                    <b>INDEX: NIFTY 50 🟢</b>
                </td>

                <td style="width:25%;">
                    <b>NIFTY SPOT: ₹ {nifty_spot:.2f}</b>
                </td>

                <td style="width:25%;">
                    <b>EXPIRY: 17SEP2026</b>
                </td>

                <td style="
                    width:25%;
                    background-color:#fef8f8;
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
                        ₹ {total_money_pnl:.2f}
                    </span>

                    <br>

                    💼 Wallet:
                    <b>
                        ₹ {st.session_state.v_wallet:.2f}
                    </b>

                </td>

            </tr>

        </table>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # 📈 STRIKE TABLES
    # ========================================================
    for strike in strikes:

        atm_text = (
            " ⭐ (ATM)"
            if strike == atm_strike
            else ""
        )

        st.markdown(
            f"""
            <h3>
                🎯 NIFTY Strike {strike}{atm_text}
            </h3>
            """,
            unsafe_allow_html=True
        )


        # ====================================================
        # 🛠️ INITIAL OI DATA
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
        # 📈 CALL OI UPDATE
        # ====================================================
        d["call"].pop(0)

        d["call"].append(
            int(
                d["call"][-1]
                + np.random.randint(-4, 6)
            )
        )


        # ====================================================
        # 📉 PUT OI UPDATE
        # ====================================================
        d["put"].pop(0)

        d["put"].append(
            int(
                d["put"][-1]
                + np.random.randint(-6, 4)
            )
        )


        # ====================================================
        # 📊 TABLE
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
            "<div style='margin-bottom:20px;'></div>",
            unsafe_allow_html=True
        )


# ============================================================
# 🔄 AUTO REFRESH
# ============================================================
time.sleep(2)
st.rerun()
