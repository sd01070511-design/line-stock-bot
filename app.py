import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import yfinance as yf

app = Flask(__name__)

# 安全設定：從環境變數抓取金鑰
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.upper().strip()
    
    # 判斷是否為 4 位數字（台股）或英文字母（美股）
    if (user_msg.isdigit() and len(user_msg) >= 4) or user_msg.isalpha():
        try:
            # 台股自動補上 .TW (如果是 0050 或 2330)
            stock_id = f"{user_msg}.TW" if user_msg.isdigit() else user_msg
            stock = yf.Ticker(stock_id)
            
            # 取得最新價格資訊
            info = stock.fast_info
            price = info['last_price']
            prev_close = info['previous_close']
            change = price - prev_close
            change_percent = (change / prev_close) * 100
            
            reply = (
                f"📈 標的: {user_msg}\n"
                f"💰 現價: {price:.2f}\n"
                f"📊 漲跌: {change:+.2f} ({change_percent:+.2f}%)"
            )
        except:
            reply = f"找不到 {user_msg} 的資料，請確認代號是否正確。"
    else:
        reply = "請輸入股票代號（例如：2330 或 NVDA）"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
