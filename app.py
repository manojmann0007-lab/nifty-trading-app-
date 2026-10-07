TELEGRAM_BOT_TOKEN = "Aapka_BotFather_Token"
TELEGRAM_CHAT_ID = "Aapki_User_ID"
import xml.etree.ElementTree as ET
import pandas as pd
import pandas_ta as ta
import requests
import streamlit as st
import yfinance as yf

# ---------------- CONFIGURATION ----------------
# Apna BotFather ka token aur apni Chat ID yahan daalein
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"
# -----------------------------------------------

st.set_page_config(
    page_title="Nifty & Sensex Pro Scanner + Alerts",
    layout="wide",
    page_icon="📈",
)


def send_telegram_alert(message_text):
  """Bina kisi paid tool ke Telegram par instant notification bhejta hai."""
  if (
      TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE"
      or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE"
  ):
    return False
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {
      "chat_id": TELEGRAM_CHAT_ID,
      "text": message_text,
      "parse_mode": "Markdown",
  }
  try:
    response = requests.post(url, data=payload, timeout=4)
    return response.status_code == 200
  except Exception:
    return False


@st.cache_data(ttl=60)
def get_market_data(ticker="^NSEI", interval="5m", period="5d"):
  df = yf.download(
      ticker, period=period, interval=interval, progress=False, multi_level_index=False
  )
  return df


# Session state to avoid spamming the same alert repeatedly
if "last_alert" not in st.session_state:
  st.session_state.last_alert = None

st.title("📊 Nifty & Sensex Live Engine + 📲 Instant Telegram Alerts")

index_choice = st.sidebar.selectbox("Index Select Karein:", ["NIFTY 50", "SENSEX"])
symbol = "^NSEI" if index_choice == "NIFTY 50" else "^BSESN"

df = get_market_data(symbol)

if not df.empty:
  # Indicator Calculations
  df["RSI"] = ta.rsi(df["Close"], length=14)
  st_data = ta.supertrend(
      df["High"], df["Low"], df["Close"], length=10, multiplier=3
  )
  df["ST_DIR"] = st_data["SUPERTd_10_3.0"]
  df["ADX"] = ta.adx(df["High"], df["Low"], df["Close"], length=14)["ADX_14"]

  bb = ta.bbands(df["Close"], length=20, std=2)
  df["BB_WIDTH"] = (bb["BBU_20_2.0"] - bb["BBL_20_2.0"]) / bb["BBM_20_2.0"]

  last = df.iloc[-1]
  atr = ta.atr(df["High"], df["Low"], df["Close"]).iloc[-1]
  is_sideways = last["ADX"] < 20 or last["BB_WIDTH"] < 0.012

  entry = round(last["Close"], 2)

  # Check Signals
  current_signal = None
  alert_message = ""

  if is_sideways:
    current_signal = "SIDEWAYS"
    alert_message = (
        f"⚠️ *SIDEWAYS MARKET ALERT ({index_choice})*\n"
        f"• Price: ₹{entry}\n"
        f"• ADX: {round(last['ADX'], 1)} (Low Momentum)\n"
        f"• Action: Naked Call/Put Buy Na Karein. Option decay ho sakta hai."
    )
  elif last["ST_DIR"] == 1 and last["RSI"] > 55:
    current_signal = "CALL_BUY"
    sl = round(entry - (1.5 * atr), 2)
    tgt = round(entry + (3 * atr), 2)
    alert_message = (
        f"🚀 *CALL (CE) BUY SIGNAL ({index_choice})*\n"
        f"• Entry: ₹{entry}\n"
        f"• Stop Loss (SL): ₹{sl}\n"
        f"• Target (1:2): ₹{tgt}\n"
        f"• RSI: {round(last['RSI'], 1)} | Supertrend: Bullish 🟢"
    )
  elif last["ST_DIR"] == -1 and last["RSI"] < 45:
    current_signal = "PUT_BUY"
    sl = round(entry + (1.5 * atr), 2)
    tgt = round(entry - (3 * atr), 2)
    alert_message = (
        f"🔻 *PUT (PE) BUY SIGNAL ({index_choice})*\n"
        f"• Entry: ₹{entry}\n"
        f"• Stop Loss (SL): ₹{sl}\n"
        f"• Target (1:2): ₹{tgt}\n"
        f"• RSI: {round(last['RSI'], 1)} | Supertrend: Bearish 🔴"
    )

  # Trigger Telegram Message only if signal has changed
  if current_signal and (st.session_state.last_alert != current_signal):
    sent = send_telegram_alert(alert_message)
    if sent:
      st.toast("📲 Telegram Alert Sent Successfully!", icon="🔔")
      st.session_state.last_alert = current_signal

  # Display Dashboard
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("LTP", f"₹{entry}")
  col2.metric("RSI (14)", f"{round(last['RSI'], 1)}")
  col3.metric(
      "Supertrend", "BULLISH 🟢" if last["ST_DIR"] == 1 else "BEARISH 🔴"
  )
  col4.metric(
      "Market State", "SIDEWAYS 🟡" if is_sideways else "TRENDING 🚀"
  )

  st.divider()
  if alert_message:
    st.markdown(alert_message)

  # Manual test button
  if st.sidebar.button("Test Telegram Message"):
    if send_telegram_alert("✅ Test Alert: Telegram bot sahi se kaam kar raha hai!"):
      st.sidebar.success("Test message phone par bhej diya gaya!")
    else:
      st.sidebar.error("Bot token ya Chat ID galat hai, check karein.")
