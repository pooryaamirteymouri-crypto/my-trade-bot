import os
import requests
import yfinance as yf
import pandas as pd
import ta
from datetime import datetime
from bs4 import BeautifulSoup

# =====================================================================
# 🔑 CONFIGURATION
# =====================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

TOTAL_CAPITAL = 1000.0
RISK_PER_TRADE = 2.0

# =====================================================================
# 🌐 TELEGRAM DISPATCHER
# =====================================================================
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

# =====================================================================
# 🧠 ENGINES
# =====================================================================
def fetch_market_news(ticker):
    query = ticker.split("-")[0]
    url = f"https://news.google.com/rss/search?q={query}+crypto+stock&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, 'xml')
        titles = [item.title.text for item in soup.find_all('item')[:3]]
        score = sum(1 for t in titles if any(w in t.lower() for w in ['bullish', 'surge', 'buy', 'growth']))
        score -= sum(1 for t in titles if any(w in t.lower() for w in ['bearish', 'crash', 'drop', 'sell']))
        return "Positive" if score >= 0 else "Negative"
    except: return "Neutral"

def ask_ai_analyst(ticker, technical_summary, sentiment):
    if not GROQ_API_KEY: return "Technical setup confirmed."
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = f"Analyze {ticker}. Score: {technical_summary}, Sentiment: {sentiment}. Give 1-line action plan."
    data = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}
    try:
        res = requests.post(url, headers=headers, json=data, timeout=8).json()
        return res['choices'][0]['message']['content']
    except: return "Technical setup confirmed."

# =====================================================================
# 🚀 CORE EXECUTION
# =====================================================================
def run_main_scan():
    print("🚀 Starting Automated Market Scan...")
    tickers = ["BTC-USD", "ETH-USD", "SOL-USD", "NEAR-USD", "NVDA", "AAPL"]
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            if len(hist) < 200: continue
            
            close = hist['Close']
            rsi = ta.momentum.rsi(close, window=14).iloc[-1]
            ema_200 = ta.trend.ema_indicator(close, window=200).iloc[-1]
            current_price = close.iloc[-1]
            
            # استراتژی ساده خرید
            if current_price > ema_200 and rsi < 45:
                sentiment = fetch_market_news(ticker)
                if sentiment != "Negative":
                    ai_advice = ask_ai_analyst(ticker, "Buy Setup", sentiment)
                    msg = (f"🎯 *SIGNAL: LONG {ticker}*\n"
                           f"Price: ${current_price:.2f}\n"
                           f"RSI: {rsi:.1f}\n"
                           f"Sentiment: {sentiment}\n"
                           f"AI Advice: {ai_advice}")
                    send_telegram_message(msg)
                    print(f"Sent signal for {ticker}")
        except Exception as e:
            print(f"Error scanning {ticker}: {e}")

if __name__ == "__main__":
    run_main_scan()