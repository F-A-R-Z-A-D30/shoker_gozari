import json
import os
import time
import requests
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import sys
import traceback

# تنظیم مسیر پروژه برای شناسایی ماژول‌ها
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# --- بارگذاری ایمن Loader ---
try:
    from loader import (
        load_day_content, get_all_topics, get_topic_by_id,
        start_topic_for_user, complete_day_for_user, get_user_topic_progress
    )
except ImportError:
    try:
        from static.content.loader import (
            load_day_content, get_all_topics, get_topic_by_id,
            start_topic_for_user, complete_day_for_user, get_user_topic_progress
        )
    except ImportError:
        print("❌ بحرانی: فایل loader.py یافت نشد!")
        sys.exit(1)

from static.graphics_handler import GraphicsHandler
from daily_reset import daily_reset

# --- تنظیمات Flask برای Render ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running! 🚀"

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

load_dotenv()
BOT_TOKEN = os.getenv('BALE_BOT_TOKEN')
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

# ========== توابع API ==========

def send_message(chat_id, text, keyboard=None):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    try:
        response = requests.post(url, json=data, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ خطا در ارسال پیام: {e}")
        return None

def send_photo(chat_id, photo_path, caption=None, keyboard=None):
    """ارسال عکس با مدیریت خطا و چک کردن وجود فایل"""
    if not os.path.exists(photo_path):
        print(f"⚠️ عکس در مسیر یافت نشد: {photo_path}")
        return send_message(chat_id, caption, keyboard)

    url = f"{BASE_URL}/sendPhoto"
    # برای بله، پارامترهای غیر فایلی باید در قالب دیتا ارسال شوند
    payload = {"chat_id": chat_id, "parse_mode": "HTML"}
    if caption:
        payload["caption"] = caption
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
        
    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            response = requests.post(url, data=payload, files=files, timeout=40)
            return response.json()
    except Exception as e:
        print(f"❌ خطا در ارسال عکس: {e}")
        return send_message(chat_id, caption, keyboard) # Fallback به متن در صورت خطای عکس

def get_updates(last_update_id=0):
    url = f"{BASE_URL}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 20, "limit": 50}
    try:
        response = requests.get(url, params=params, timeout=25)
        return response.json()
    except:
        return {"ok": False}

def answer_callback(callback_id):
    url = f"{BASE_URL}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_id}, timeout=5)
    except:
        pass

# ========== منطق اصلی ربات ==========

def handle_start(chat_id, user_id):
    welcome_text = GraphicsHandler.create_welcome_message()
    send_message(chat_id, welcome_text)
    time.sleep(0.5)
    
    start_keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 شروع استفاده از ربات", "callback_data": "start_using"}],
            [{"text": "💖 حمایت از ما", "callback_data": "support_developer"}]
        ]
    }
    send_message(chat_id, "🎯 برای شروع، یکی از گزینه‌های زیر را انتخاب کنید:", start_keyboard)

def handle_category_selection(chat_id, user_id, topic_id):
    try:
        user_progress = get_user_topic_progress(user_id, topic_id)
        access_info = daily_reset.get_access_info(user_id, topic_id)
        current_day = user_progress.get("current_day", 1)
        completed_days = user_progress.get("completed_days", [])
        topic_info = get_topic_by_id(topic_id)

        # ۱. بررسی دسترسی زمانی
        if not access_info["has_access"] and (current_day - 1) in completed_days:
            last_done = current_day - 1
            message = f"✅ <b>تمرین امروز انجام شده!</b>\n\n{topic_info['emoji']} موضوع: <b>{topic_info['name']}</b>\n📅 روز {last_done} تکمیل شد.\n\n⏳ مانده تا تمرین بعدی: {access_info['remaining_text']}"
            keyboard = {"inline_keyboard": [[{"text": "🎯 موضوعات دیگر", "callback_data": "categories"}]]}
            send_message(chat_id, message, keyboard)
            return

        # ۲. لود محتوا
        content = load_day_content(topic_id, current_day, user_id)
        if not content or not content.get('success', True):
            send_message(chat_id, "❌ متأسفانه محتوایی برای امروز یافت نشد.")
            return

        # ۳. ثبت در سیستم ریست
        daily_reset.record_access(user_id, topic_id, content['day_number'])

        # ۴. متن پیام
        is_completed = content["day_number"] in completed_days
        msg_text = f"<b>{content['topic_emoji']} {content['topic_name']}</b>\n"
        msg_text += f"📅 روز {content['day_number']} از ۲۸\n"
        msg_text += f"<i>{content['intro']}</i>\n\n"
        
        for i, item in enumerate(content['items'][:10], 1):
            msg_text += f"{i}. {item}\n"

        if content.get('exercise'):
            msg_text += f"\n💡 <b>تمرین:</b> {content['exercise']}"

        # ۵. کیبورد و عکس
        inline_keyboard = GraphicsHandler.create_day_inline_keyboard(topic_id, content['day_number'], is_completed)
        image_path = topic_info.get("image")

        if image_path:
            send_photo(chat_id, image_path, caption=msg_text, keyboard=inline_keyboard)
        else:
            send_message(chat_id, msg_text, inline_keyboard)

    except Exception as e:
        print(f"❌ خطا در انتخاب موضوع: {e}")
        traceback.print_exc()

def start_polling():
    keep_alive()
    print("🚀 Bot is Polling...")
    last_update_id = 0
    
    while True:
        try:
            updates = get_updates(last_update_id)
            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    last_update_id = update["update_id"]
                    
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = str(msg["from"]["id"])
                        text = msg.get("text", "")
                        
                        if text == "/start":
                            handle_start(chat_id, user_id)
                        elif "موضوعات" in text or text == "/topics":
                            send_message(chat_id, "🎯 انتخاب موضوع:", GraphicsHandler.create_categories_keyboard())
                        else:
                            # چک کردن کلیک روی کیبورد متنی موضوعات
                            for t in get_all_topics():
                                if t['name'] in text:
                                    handle_category_selection(chat_id, user_id, t['id'])
                                    break

                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        chat_id = cb["message"]["chat"]["id"]
                        user_id = str(cb["from"]["id"])
                        data = cb.get("data", "")
                        answer_callback(cb["id"])

                        if data in ["start_using", "categories"]:
                            send_message(chat_id, "🎯 انتخاب موضوع:", GraphicsHandler.create_categories_keyboard())
                        elif data.startswith("cat_"):
                            handle_category_selection(chat_id, user_id, int(data.split("_")[1]))
                        elif data.startswith("complete_"):
                            p = data.split("_")
                            complete_day_for_user(user_id, int(p[1]), int(p[2]))
                            send_message(chat_id, "✅ تبریک! تمرین امروز ثبت شد.")

            time.sleep(0.5) # وقفه کوتاه برای جلوگیری از فشار به پردازنده
        except Exception as e:
            print(f"⚠️ خطای حلقه اصلی: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
