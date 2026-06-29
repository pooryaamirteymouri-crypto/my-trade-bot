import os
import requests
import yfinance as yf
import pandas as pd
import ta
import time
from datetime import datetime
from bs4 import BeautifulSoup

# =====================================================================
# 🔑 CONFIGURATION & MONEY MANAGEMENT
# =====================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

TOTAL_CAPITAL = 1000.0   # کل موجودی دلاری شما
RISK_PER_TRADE = 2.0     # میزان ریسک در هر معامله (۲ درصد)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: print("Telegram error")

def fetch_market_news(ticker):
    query = ticker.split("-")[0]
    url = f"https://news.google.com/rss/search?q={query}+market+crypto&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, 'xml')
        titles = [item.title.text for item in soup.find_all('item')[:3]]
        score = sum(1 for t in titles if any(w in t.lower() for w in ['bullish', 'surge', 'buy', 'growth']))
        score -= sum(1 for t in titles if any(w in t.lower() for w in ['bearish', 'crash', 'drop', 'sell']))
        return "Positive" if score >= 0 else "Negative"
    except: return "Neutral"

def ask_ai_analyst(ticker, technical_summary, sentiment):
    if not GROQ_API_KEY: return "Execution based on trend setup."
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = f"Analyze {ticker}. Tech Score: {technical_summary}, Sentiment: {sentiment}. Provide a 1-line action plan."
    data = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}
    try:
        res = requests.post(url, headers=headers, json=data, timeout=8).json()
        return res['choices'][0]['message']['content']
    except: return "Execution based on trend setup."

# =====================================================================
# 🚀 CORE RUNNER
# =====================================================================
def run_main_scan():
    # لیست طلایی: کریپتو، سهام بزرگ، طلا و شاخص‌ها
    tickers = [
        # --- CRYPTO ---
        "BTC-USD", "ETH-USD", "SOL-USD", "NEAR-USD", "AVAX-USD", "LINK-USD", "XRP-USD", "ADA-USD",
        # --- US TECH STOCKS ---
        "NVDA", "AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "COIN",
        # --- COMMODITIES & INDICES ---
        "GC=F", "NQ=F", "SPY"  # طلا، فیوچرز نزدک، شاخص اس‌اندپی ۵۰۰
    ]
    
    total_scanned = 0
    signals_found = []
    
    print(f"شروع اسکن بزرگ بازار برای {len(tickers)} نماد...")
    
    for ticker in tickers:
        try:
            # وقفه کوتاه برای جلوگیری از بلاک شدن توسط یاهو
            time.sleep(1.2) 
            
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            if len(hist) < 200: continue
            
            total_scanned += 1
            close = hist['Close']
            rsi = ta.momentum.rsi(close, window=14).iloc[-1]
            macd = ta.trend.macd(close).iloc[-1]
            macd_sig = ta.trend.macd_signal(close).iloc[-1]
            ema_200 = ta.trend.ema_indicator(close, window=200).iloc[-1]
            current_price = close.iloc[-1]
            
            # سیستم امتیازدهی تکنیکال
            score = 0
            if current_price > ema_200: score += 4  
            if rsi < 45: score += 3                 
            if macd > macd_sig: score += 3          
            percentage = (score / 10) * 100
            
            # فیلتر صادر شدن سیگنال خرید (امتیاز ۷۰ به بالا)
            if percentage >= 70:
                sentiment = fetch_market_news(ticker)
                if sentiment != "Negative":
                    
                    # محاسبه مدیریت ریسک نوسانی (ATR)
                    atr = ta.volatility.average_true_range(hist['High'], hist['Low'], close, window=14).iloc[-1]
                    sl = current_price - (2 * atr)
                    tp = current_price + (4 * atr)
                    
                    # محاسبه حجم ورود به دلار
                    loss_percentage = ((current_price - sl) / current_price)
                    allowed_risk_dollars = TOTAL_CAPITAL * (RISK_PER_TRADE / 100.0)
                    position_size_dollars = allowed_risk_dollars / loss_percentage if loss_percentage > 0 else TOTAL_CAPITAL * 0.1
                    if position_size_dollars > TOTAL_CAPITAL: position_size_dollars = TOTAL_CAPITAL
                    
                    ai_advice = ask_ai_analyst(ticker, f"{percentage}%", sentiment)
                    
                    # ارسال سیگنال خرید فوری
                    msg = f"🎯 *SIGNAL: LONG {ticker}*\n\n" \
                          f"💵 *Price:* ${current_price:.2f} (Tech: {percentage}%)\n" \
                          f"📰 *Sentiment:* {sentiment}\n\n" \
                          f"📊 *RISK MANAGEMENT:*\n" \
                          f"🛍️ *POSITION SIZE:* `${position_size_dollars:.2f}`\n" \
                          f"🛑 *Stop Loss:* ${sl:.2f} (-{loss_percentage*100:.1f}%)\n" \
                          f"🎯 *Take Profit:* ${tp:.2f}\n\n" \
                          f"🧠 *AI Reason:* {ai_advice}"
                          
                    send_telegram_message(msg)
                    signals_found.append(ticker)
                    
        except Exception as e:
            print(f"Error on {ticker}: {e}")
            
    # =====================================================================
    # 📊 REPORT GENERATOR (گزارش پایانی اسکن)
    # =====================================================================
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    signals_text = ", ".join(signals_found) if signals_found else "هیچ سیگنال معتبری یافت نشد."
    
    final_report = f"📋 *📊 MARKET SCAN REPORT*\n" \
                   f"📅 *Time:* {report_time}\n" \
                   f"🔍 *Total Scanned:* {total_scanned} Assets\n" \
                   f"🚀 *Buy Signals Issued:* {len(signals_found)}\n" \
                   f"🌟 *Assets Triggered:* `{signals_text}`\n\n" \
                   f"🤖 _ربات با موفقیت کار خود را پایان داد و به خواب رفت._"
                   
    send_telegram_message(final_report)

if __name__ == "__main__":
    run_main_scan()
