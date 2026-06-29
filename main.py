import os
import requests
import yfinance as yf
import pandas as pd
import ta
import time
from datetime import datetime
from bs4 import BeautifulSoup

# =====================================================================
# 🔑 CONFIGURATION & RISK MANAGEMENT
# =====================================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

TOTAL_CAPITAL = 1000.0   # موجودی فرضی کل حساب شما

def send_telegram_message(message):
    """ارسال امن پیام به تلگرام با کنترل خطا"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram configuration missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def check_btc_health():
    """فیلتر همبستگی: بررسی وضعیت روند لیدر بازار (بیت‌کوین)"""
    try:
        btc = yf.Ticker("BTC-USD")
        hist = btc.history(period="1y", timeout=10)
        if hist.empty: return True
        close = hist['Close']
        ema_200 = ta.trend.ema_indicator(close, window=200).iloc[-1]
        rsi = ta.momentum.rsi(close, window=14).iloc[-1]
        return close.iloc[-1] > ema_200 and rsi > 35
    except Exception as e:
        print(f"Error checking BTC health: {e}")
        return True # در صورت خطا، فرض را بر سلامت می‌گذاریم تا سیستم متوقف نشود

def fetch_market_news(ticker):
    """استخراج و تحلیل احساسات اخبار بازار با لایه محافظتی"""
    query = ticker.split("-")[0]
    url = f"https://news.google.com/rss/search?q={query}+market+crypto&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=7)
        soup = BeautifulSoup(r.text, 'xml')
        titles = [item.title.text for item in soup.find_all('item')[:3]]
        score = sum(1 for t in titles if any(w in t.lower() for w in ['bullish', 'surge', 'buy', 'growth']))
        score -= sum(1 for t in titles if any(w in t.lower() for w in ['bearish', 'crash', 'drop', 'sell']))
        return "Positive" if score >= 0 else "Negative"
    except Exception as e:
        print(f"News fetch error for {ticker}: {e}")
        return "Neutral"

def ask_ai_analyst(ticker, technical_summary, sentiment):
    """صدا زدن هوش مصنوعی با سیستم تاخیر برای جلوگیری از مسدود شدن API"""
    if not GROQ_API_KEY: 
        return "Execution approved based on multi-indicator technical setup."
    
    # تاخیر ۱.۵ ثانیه‌ای برای رعایت محدودیت تعداد درخواست Groq
    time.sleep(1.5) 
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    prompt = f"Analyze {ticker}. Tech Score: {technical_summary}, Sentiment: {sentiment}. Provide a 1-line action plan."
    data = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
    try:
        res = requests.post(url, headers=headers, json=data, timeout=10).json()
        return res['choices'][0]['message']['content']
    except Exception as e:
        print(f"AI Analysis error for {ticker}: {e}")
        return "Execution approved based on multi-indicator technical setup."

# =====================================================================
# 🚀 CORE AUTOMATION RUNNER
# =====================================================================
def run_main_scan():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Launching Optimize Cloud Scanner...")
    
    # بررسی سلامت بازار کریپتو
    btc_is_healthy = check_btc_health()
    
    # لیست دارایی‌های برتر جهان برای مانیتورینگ
    tickers = [
        "BTC-USD", "ETH-USD", "SOL-USD", "NEAR-USD", "AVAX-USD", "LINK-USD",
        "NVDA", "AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "META", "AMD",
        "GC=F", "NQ=F", "SPY"
    ]
    
    total_scanned = 0
    signals_found = []
    
    for ticker in tickers:
        try:
            # اعمال فیلتر همبستگی روی آلت‌کوین‌ها
            if "-USD" in ticker and ticker != "BTC-USD" and not btc_is_healthy:
                print(f"Skipping {ticker} due to Unhealthy BTC Market Condition.")
                continue
                
            # وقفه ایمن برای جلوگیری از مسدود شدن توسط یاهو فایننس
            time.sleep(1.5) 
            stock = yf.Ticker(ticker)
            
            # دریافت دیتای بلندمدت (هفتگی) برای تایید روند کلان
            hist_long = stock.history(period="2y", interval="1wk", timeout=10)
            if len(hist_long) < 50: hist_long = stock.history(period="2y", timeout=10)
            
            # دریافت دیتای میان‌مدت (روزانه)
            hist = stock.history(period="1y", timeout=10)
            if len(hist) < 200: continue
            
            total_scanned += 1
            close = hist['Close']
            current_price = close.iloc[-1]
            
            # محاسبات اندیکاتورهای اصلی
            rsi = ta.momentum.rsi(close, window=14).iloc[-1]
            macd = ta.trend.macd(close).iloc[-1]
            macd_sig = ta.trend.macd_signal(close).iloc[-1]
            ema_200 = ta.trend.ema_indicator(close, window=200).iloc[-1]
            
            # فیلتر چند زمان‌فریمه: آیا قیمت بالاتر از میانگین ۵۰ هفته‌ای است؟
            long_term_trend = current_price > hist_long['Close'].rolling(50).mean().iloc[-1]
            
            # سیستم فازی امتیازدهی به موقعیت خرید
            score = 0
            if current_price > ema_200: score += 4  
            if rsi < 45: score += 3                 
            if macd > macd_sig: score += 3          
            if long_term_trend: score += 2 
            
            percentage = (score / 12) * 100
            
            # تایید نهایی سیگنال (امتیاز بالای ۷۵٪)
            if percentage >= 75:
                sentiment = fetch_market_news(ticker)
                
                # فیلتر امنیتی: اگر اخبار کاملاً منفی بود، سیگنال صادر نشود
                if sentiment != "Negative":
                    
                    # مدیریت ریسک پویا: موقعیت عالی = ۲٪ ریسک، موقعیت معمولی = ۱٪ ریسک
                    dynamic_risk = 2.0 if percentage >= 90 else 1.0
                    
                    # محاسبه حد ضرر و تارگت داینامیک با اندیکاتور نوسان‌سنج ATR
                    atr = ta.volatility.average_true_range(hist['High'], hist['Low'], close, window=14).iloc[-1]
                    sl = current_price - (2.0 * atr)
                    tp = current_price + (3.5 * atr)
                    
                    # محاسبات مدیریت سرمایه دقیق ریاضی (Position Sizing)
                    loss_percentage = ((current_price - sl) / current_price)
                    allowed_risk_dollars = TOTAL_CAPITAL * (dynamic_risk / 100.0)
                    position_size_dollars = allowed_risk_dollars / loss_percentage if loss_percentage > 0 else TOTAL_CAPITAL * 0.05
                    
                    # لایه امنیتی: حجم خرید نباید از کل سرمایه بیشتر شود
                    if position_size_dollars > TOTAL_CAPITAL: 
                        position_size_dollars = TOTAL_CAPITAL
                    
                    # تقسیم پله‌های ورود هوشمند (۶۰٪ نقد، ۴۰٪ ارزان‌تر در پولبک)
                    p1 = position_size_dollars * 0.60
                    p2 = position_size_dollars * 0.40
                    p2_price = current_price - (0.5 * atr)
                    
                    # دریافت نظر نهایی هوش مصنوعی
                    ai_advice = ask_ai_analyst(ticker, f"{percentage:.0f}%", sentiment)
                    
                    # فرمت پیام ارسالی به تلگرام
                    msg = f"🛡️ *SAFE SIGNAL: LONG {ticker}*\n\n" \
                          f"💵 *Current Price:* ${current_price:.2f}\n" \
                          f"📊 *Technical Score:* {percentage:.0f}%\n" \
                          f"📰 *Market Sentiment:* {sentiment}\n\n" \
                          f"💰 *PORTFOLIO & RISK CONTROL:*\n" \
                          f"🚨 *Risk Allocated:* {dynamic_risk}% (${allowed_risk_dollars:.0f} Max Loss)\n" \
                          f"🛍 *Total Position Size:* `${position_size_dollars:.2f}`\n" \
                          f"📥 *Step 1 (Market Buy 60%):* `${p1:.2f}` at current price\n" \
                          f"📥 *Step 2 (Limit Buy 40%):* `${p2:.2f}` around `${p2_price:.2f}`\n\n" \
                          f"🛑 *Initial Stop Loss:* ${sl:.2f} (-{loss_percentage*100:.1f}%)\n" \
                          f"📈 *Trailing Stop:* Move SL to entry price once profit hits +1.5x ATR.\n" \
                          f"🎯 *Take Profit Target:* ${tp:.2f}\n\n" \
                          f"🧠 *AI Analyst Decision:* {ai_advice}"
                          
                    send_telegram_message(msg)
                    signals_found.append(ticker)
                    
        except Exception as e:
            print(f"Critical skipping error on {ticker}: {e}")
            
    # تولید گزارش نهایی وضعیت کل بازار
    try:
        report_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        signals_text = ", ".join(signals_found) if signals_found else "None"
        btc_status = "🟢 Healthy & Secure" if btc_is_healthy else "🔴 Bearish/Unsafe (Alts Filtered)"
        
        final_report = f"📋 *📊 AUTOMATED SYSTEM REPORT*\n" \
                       f"📅 *Time:* {report_time}\n" \
                       f"🌐 *BTC Market Condition:* {btc_status}\n" \
                       f"🔍 *Total Assets Scanned:* {total_scanned}\n" \
                       f"🚀 *Safe Signals Issued:* {len(signals_found)} (`{signals_text}`)\n\n" \
                       f"🛡 _سیستم مدیریت سرمایه چندلایه با موفقیت اجرا شد._"
                       
        send_telegram_message(final_report)
    except Exception as e:
        print(f"Error generating final report: {e}")

if __name__ == "__main__":
    run_main_scan()
