import os
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import yfinance as yf

app = Flask(__name__)

# 安全設定：從環境變數抓取金鑰
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

# 🌟 新增：氣象署 API 查詢函式
def get_taiwan_weather(location):
    api_key = os.environ.get('CWA_API_KEY')
    if not api_key:
        return "系統找不到氣象 API 金鑰，請檢查 Render 環境變數。"
    
    # 防呆機制：氣象署 API 只吃「臺」，不吃「台」
    location = location.replace("台", "臺")
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={api_key}&locationName={location}"
    
    try:
        res = requests.get(url).json()
        if res.get("success") == "true":
            records = res.get("records", {}).get("location", [])
            if not records:
                return f"找不到「{location}」的資料，請確認輸入的是完整的縣市名稱（例如：臺北市、苗栗縣）。"

            data = records[0]["weatherElement"]
            # 抓取預報參數 (Wx:天氣, PoP:降雨機率, MinT:最低溫, MaxT:最高溫)
            wx = data[0]["time"][0]["parameter"]["parameterName"]
            pop = data[1]["time"][0]["parameter"]["parameterName"]
            min_t = data[2]["time"][0]["parameter"]["parameterName"]
            max_t = data[4]["time"][0]["parameter"]["parameterName"]
            
            return (f"📍 【{location}】今明36小時預報\n"
                    f"☁️ 狀況：{wx}\n"
                    f"☔ 降雨機率：{pop}%\n"
                    f"🌡️ 氣溫：{min_t}°C ~ {max_t}°C")
        else:
            return "氣象署 API 回傳異常，請稍後再試。"
    except Exception as e:
        return f"氣象查詢發生錯誤：{e}"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 🌟 訊息處理中心 (Routing)
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.upper().strip()
    
    # 路線 A：天氣查詢 (如果訊息裡面包含 "天氣" 兩個字)
    if "天氣" in user_msg:
        city = user_msg.replace("天氣", "").strip() 
        reply_content = get_taiwan_weather(city)
        
    # 路線 B：股價查詢 (如果是 4 位數以上數字，或是全英文字母)
    elif (user_msg.isdigit() and len(user_msg) >= 4) or user_msg.isalpha():
        try:
            stock_id = f"{user_msg}.TW" if user_msg.isdigit() else user_msg
            stock = yf.Ticker(stock_id)
            info = stock.fast_info
            price = info['last_price']
            prev_close = info['previous_close']
            change = price - prev_close
            change_percent = (change / prev_close) * 100
            
            reply_content = (
                f"📈 標的: {user_msg}\n"
                f"💰 現價: {price:.2f}\n"
                f"📊 漲跌: {change:+.2f} ({change_percent:+.2f}%)"
            )
        except:
            reply_content = f"找不到 {user_msg} 的資料，請確認代號是否正確。"
            
    # 路線 C：都不符合的防呆回覆
    else:
        reply_content = "請輸入股票代號（如 2330 或 NVDA）或天氣查詢（如 苗栗縣天氣）。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_content))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
