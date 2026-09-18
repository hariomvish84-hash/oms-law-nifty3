import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import pyotp
import streamlit as st
from dotenv import load_dotenv

# ============================================================
# 🚀 AUTO RUN
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
# 🔐 LOAD CREDENTIALS
# ============================================================

load_dotenv()

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_KEY = os.getenv("ANGEL_TOTP_KEY")


# ============================================================
# 📦 SMART API
# ============================================================

try:
    from SmartApi import SmartConnect
except ImportError:
    SmartConnect = None


# ============================================================
# ⚙️ SETTINGS
# ============================================================

APP_TITLE = "OM'S LAW 2.0"

NIFTY_EXCHANGE = "NSE"
NIFTY_SYMBOL = "Nifty 50"
NIFTY_TOKEN = "99926000"

LOT_SIZE = 25

STARTING_CAPITAL = 100000.0

REFRESH_SECONDS = 5

DEFAULT_TARGET = 30.0
DEFAULT_STOPLOSS = 15.0


# ============================================================
# 🖥️ PAGE
# ============================================================

st.set_page_config(
    page_title="OM'S LAW 2.0 - NIFTY LIVE",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# 🎨 STYLE
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #f7f8fa;
    }

    h1, h2, h3, h4, h5, h6,
    p, span, label, td, th {
        color: #111111 !important;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        background: white;
    }

    td, th {
        border: 1px solid #d1d5db !important;
        padding: 10px !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 🧠 SESSION STATE
# ============================================================

if "position" not in st.session_state:
    st.session_state.position = None

if "entry_price" not in st.session_state:
    st.session_state.entry_price = 0.0

if "current_price" not in st.session_state:
    st.session_state.current_price = 0.0

if "quantity" not in st.session_state:
    st.session_state.quantity = LOT_SIZE

if "wallet" not in st.session_state:
    st.session_state.wallet = STARTING_CAPITAL

if "realized_pnl" not in st.session_state:
    st.session_state.realized_pnl = 0.0

if "last_spot" not in st.session_state:
    st.session_state.last_spot = 0.0

if "oi_data" not in st.session_state:
    st.session_state.oi_data = {}


# ============================================================
# 🔐 ANGEL ONE LOGIN
# ============================================================

@st.cache_resource(show_spinner=False)
def get_angel_session():

    if SmartConnect is None:
        return None, "SmartApi package नहीं मिला"

    if not all([
        API_KEY,
        CLIENT_ID,
        PASSWORD,
        TOTP_KEY
    ]):
        return None, (
            "Credentials missing. "
            ".env check करें."
        )

    try:

        smart_api = SmartConnect(
            api_key=API_KEY
        )

        totp = pyotp.TOTP(
            TOTP_KEY
        ).now()

        response = smart_api.generateSession(
            CLIENT_ID,
            PASSWORD,
            totp
        )

        if response and response.get("status"):
            return smart_api, "Connected"

        return None, str(
            response.get(
                "message",
                "Login failed"
            )
        )

    except Exception as e:

        return None, f"Login Error: {e}"


smart_connect, connection_status = (
    get_angel_session()
)


# ============================================================
# 📡 NIFTY LIVE SPOT
# ============================================================

def get_nifty_spot(api):

    if api is None:
        return None

    try:

        response = api.ltpData(
            NIFTY_EXCHANGE,
            NIFTY_SYMBOL,
            NIFTY_TOKEN
        )

        if (
            response
            and response.get("status")
            and response.get("data")
        ):

            return float(
                response["data"]["ltp"]
            )

    except Exception:
        pass

    return None


nifty_spot = get_nifty_spot(
    smart_connect
)


if nifty_spot is None:

    if st.session_state.last_spot > 0:
        nifty_spot = st.session_state.last_spot
    else:
        nifty_spot = 23270.60


st.session_state.last_spot = nifty_spot


# ============================================================
# 🎯 ATM STRIKE
# ============================================================

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


# ============================================================
# 📅 EXPIRY
# ============================================================

def get_next_thursday():

    today = datetime.now().date()

    days = (
        3 - today.weekday()
    ) % 7

    expiry = today + timedelta(
        days=days
    )

    return expiry.strftime(
        "%d%b%Y"
    ).upper()


expiry = get_next_thursday()


# ============================================================
# 📦 SIDEBAR
# ============================================================

st.sidebar.title(
    "🤖 NIFTY ALGO PANEL"
)


algo_active = st.sidebar.toggle(
    "🟢 Paper Algo ON",
    value=False
)


lots = st.sidebar.number_input(
    "📦 Lots",
    min_value=1,
    max_value=100,
    value=1
)


quantity = lots * LOT_SIZE


st.session_state.quantity = quantity


st.sidebar.metric(
    "Quantity",
    quantity
)


target_points = st.sidebar.number_input(
    "🎯 Target Points",
    min_value=1.0,
    value=DEFAULT_TARGET,
    step=1.0
)


stoploss_points = st.sidebar.number_input(
    "🛑 Stop Loss Points",
    min_value=1.0,
    value=DEFAULT_STOPLOSS,
    step=1.0
)


if smart_connect:
    st.sidebar.success(
        "🟢 Angel One Connected"
    )
else:
    st.sidebar.error(
        "🔴 " + connection_status
    )


# ============================================================
# 🟢 PAPER BUY
# ============================================================

def open_position(position, price):

    st.session_state.position = position

    st.session_state.entry_price = price

    st.session_state.current_price = price


# ============================================================
# 🔴 CLOSE PAPER POSITION
# ============================================================

def close_position():

    if st.session_state.position is None:
        return

    pnl = (
        st.session_state.current_price
        - st.session_state.entry_price
    ) * st.session_state.quantity

    st.session_state.realized_pnl += pnl

    st.session_state.wallet += pnl

    st.session_state.position = None

    st.session_state.entry_price = 0.0

    st.session_state.current_price = 0.0


# ============================================================
# BUY BUTTONS
# ============================================================

b1, b2 = st.sidebar.columns(2)


with b1:

    if st.button(
        "🟩 BUY CE",
        use_container_width=True
    ):

        # Paper entry
        open_position(
            "NIFTY CE",
            100.0
        )


with b2:

    if st.button(
        "🟥 BUY PE",
        use_container_width=True
    ):

        # Paper entry
        open_position(
            "NIFTY PE",
            100.0
        )


if st.sidebar.button(
    "⬜ CLOSE POSITION",
    use_container_width=True
):

    close_position()


# ============================================================
# 📊 PAPER PRICE UPDATE
# ============================================================

if st.session_state.position:

    # केवल Paper simulation
    st.session_state.current_price += 0.5

    if st.session_state.current_price <= 0:
        st.session_state.current_price = 0.05


# ============================================================
# 💰 LIVE P&L
# ============================================================

if st.session_state.position:

    live_pnl = (
        st.session_state.current_price
        - st.session_state.entry_price
    ) * st.session_state.quantity

else:

    live_pnl = 0.0


# ============================================================
# 🎯 TARGET / STOP LOSS
# ============================================================

if st.session_state.position:

    points = (
        st.session_state.current_price
        - st.session_state.entry_price
    )

    if points >= target_points:

        profit = (
            target_points
            * st.session_state.quantity
        )

        st.session_state.realized_pnl += profit

        st.session_state.wallet += profit

        st.session_state.position = None

        st.session_state.entry_price = 0.0

        st.session_state.current_price = 0.0

        st.toast(
            "🎯 Target Hit!"
        )


    elif points <= -stoploss_points:

        loss = (
            -stoploss_points
            * st.session_state.quantity
        )

        st.session_state.realized_pnl += loss

        st.session_state.wallet += loss

        st.session_state.position = None

        st.session_state.entry_price = 0.0

        st.session_state.current_price = 0.0

        st.toast(
            "🛑 Stop Loss Hit!"
        )


# ============================================================
# 🏷️ HEADER
# ============================================================

st.markdown(
    """
    <h1 style="text-align:center;">
        OM'S LAW 2.0
    </h1>
    """,
    unsafe_allow_html=True
)


st.markdown(
    """
    <h3 style="text-align:center;">
        📊 NIFTY 50 LIVE TRADING PANEL
    </h3>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 📊 TOP METRICS
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)


with c1:
    st.metric(
        "NIFTY SPOT",
        f"₹ {nifty_spot:,.2f}"
    )


with c2:
    st.metric(
        "ATM",
        atm_strike
    )


with c3:
    st.metric(
        "EXPIRY",
        expiry
    )


with c4:
    st.metric(
        "POSITION",
        st.session_state.position
        or "NONE"
    )


with c5:
    st.metric(
        "LIVE P&L",
        f"₹ {live_pnl:,.2f}"
    )


# ============================================================
# 💼 ACCOUNT
# ============================================================

st.markdown(
    "### 💼 Account Summary"
)


account = pd.DataFrame({

    "Item": [
        "Starting Capital",
        "Wallet",
        "Realized P&L",
        "Unrealized P&L",
        "Total P&L"
    ],

    "Amount": [

        STARTING_CAPITAL,

        st.session_state.wallet,

        st.session_state.realized_pnl,

        live_pnl,

        st.session_state.realized_pnl
        + live_pnl
    ]

})


account["Amount"] = account[
    "Amount"
].round(2)


st.table(account)


# ============================================================
# 📌 POSITION
# ============================================================

st.markdown(
    "### 📌 Current Position"
)


if st.session_state.position:

    position_df = pd.DataFrame({

        "Field": [
            "Position",
            "Entry",
            "Current",
            "Quantity",
            "Target",
            "Stop Loss",
            "P&L"
        ],

        "Value": [

            st.session_state.position,

            round(
                st.session_state.entry_price,
                2
            ),

            round(
                st.session_state.current_price,
                2
            ),

            st.session_state.quantity,

            round(
                st.session_state.entry_price
                + target_points,
                2
            ),

            round(
                st.session_state.entry_price
                - stoploss_points,
                2
            ),

            round(
                live_pnl,
                2
            )
        ]
    })

    st.table(position_df)

else:

    st.info(
        "अभी कोई Paper Position नहीं है."
    )


# ============================================================
# 🎯 OPTION CHAIN AREA
# ============================================================

st.markdown(
    "## 🎯 NIFTY OPTION CHAIN"
)


option_rows = []


for strike in strikes:

    # --------------------------------------------------------
    # IMPORTANT
    # --------------------------------------------------------
    # यहाँ actual Angel One option token मिलने के बाद
    # CE/PE LTP और OI fetch किया जाएगा.
    #
    # अभी dummy values को LIVE OI नहीं बताया जा रहा.
    # --------------------------------------------------------

    option_rows.append({

        "Strike": strike,

        "CE LTP": "--",

        "CE OI": "--",

        "PE OI": "--",

        "PE LTP": "--",

        "ATM": (
            "⭐ ATM"
            if strike == atm_strike
            else ""
        )

    })


option_df = pd.DataFrame(
    option_rows
)


st.dataframe(
    option_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 📡 SYSTEM STATUS
# ============================================================

st.markdown(
    "## 📡 System Status"
)


status = pd.DataFrame({

    "Component": [

        "Angel One",
        "NIFTY LTP",
        "Option Chain",
        "Trading Mode",
        "Algo",
        "Last Update"

    ],

    "Status": [

        connection_status,

        f"₹ {nifty_spot:,.2f}",

        "Waiting for option tokens",

        "PAPER / VIRTUAL",

        "ON" if algo_active else "OFF",

        datetime.now().strftime(
            "%d-%m-%Y %H:%M:%S"
        )

    ]

})


st.table(status)


# ============================================================
# ⚠️ SAFETY
# ============================================================

st.warning(
    "⚠️ यह Paper Trading version है। "
    "BUY CE / BUY PE से broker को real order नहीं भेजा जाता। "
    "Option Chain में '--' का मतलब है कि उस contract का "
    "actual token/market-data mapping अभी नहीं जोड़ा गया है।"
)


# ============================================================
# 🔄 REFRESH
# ============================================================

time.sleep(
    REFRESH_SECONDS
)

st.rerun()
