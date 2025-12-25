import json
import os
import time
import requests
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import sys
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- بارگذاری ایمن ماژول‌ها ---
# در فایل polling_bot.py جایگزین بخش ایمپورت قبلی کن:
try:
    from loader import (
        load_day_content, get_all_topics, get_topic_by_id,
        start_topic_for_user, complete_day_for_user, get_user_topic_progress
    )
except ImportError as e:
    print(f"❌ Critical Error: Could not find loader.py. Details: {e}")
    sys.exit(1)
    )
except ImportError:
    from static.content.loader import (
        load_day_content, get_all_topics, get_topic_by_id,
        start_topic_for_user, complete_day_for_user, get_user_topic_progress
    )

from static.graphics_handler import GraphicsHandler
from daily_reset import daily_reset

load_dotenv()
BOT_TOKEN = os.getenv('BALE_BOT_TOKEN')
PAYMENT_TOKEN = os.getenv('BALE_PROVIDER_TOKEN') 
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

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
    """ارسال تصویر به همراه متن و کیبورد"""
    url = f"{BASE_URL}/sendPhoto"
    payload = {"chat_id": chat_id, "parse_mode": "HTML"}
    if caption:
        payload["caption"] = caption
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
    
    try:
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                response = requests.post(url, data=payload, files=files, timeout=40)
                return response.json()
        else:
            print(f"⚠️ تصویر در مسیر یافت نشد: {photo_path}")
            return send_message(chat_id, caption, keyboard)
    except Exception as e:
        print(f"❌ خطا در ارسال عکس: {e}")
        return send_message(chat_id, caption, keyboard)

def get_updates(last_update_id=0):
    url = f"{BASE_URL}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 30, "limit": 100}
    try:
        response = requests.get(url, params=params, timeout=35)
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
    time.sleep(1)
    
    start_keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 شروع استفاده از ربات", "callback_data": "start_using"}],
            [{"text": "💖 حمایت از توسعه‌دهنده", "callback_data": "support_developer"}]
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

        if not access_info["has_access"] and (current_day - 1) in completed_days:
            last_done = current_day - 1
            message = f"✅ <b>تمرین امروز انجام شده!</b>\n\n{topic_info['emoji']} موضوع: <b>{topic_info['name']}</b>\n📅 روز {last_done} ثبت شد.\n⏳ مانده تا تمرین بعدی: {access_info['remaining_text']}"
            keyboard = {"inline_keyboard": [[{"text": "🎯 موضوعات دیگر", "callback_data": "categories"}]]}
            send_message(chat_id, message, keyboard)
            return

        content = load_day_content(topic_id, current_day, user_id)
        if not content:
            send_message(chat_id, "❌ خطا در بارگذاری محتوا.")
            return

        daily_reset.record_access(user_id, topic_id, content['day_number'])
        is_completed = content["day_number"] in completed_days
        
        msg_text = GraphicsHandler.create_beautiful_message(topic_info['name'], content['day_number'], user_progress)
        inline_keyboard = GraphicsHandler.create_day_inline_keyboard(topic_id, content['day_number'], is_completed)
        
        # --- اصلاح بخش ارسال عکس ---
        photo_path = topic_info.get("image")
        if photo_path:
            send_photo(chat_id, photo_path, caption=msg_text, keyboard=inline_keyboard)
        else:
            send_message(chat_id, msg_text, inline_keyboard)
            
        send_message(chat_id, "🔽 منوی دسترسی سریع:", GraphicsHandler.create_main_menu_keyboard())

    except Exception as e:
        traceback.print_exc()
        send_message(chat_id, "⚠️ مشکلی در بارگذاری رخ داد.")

def handle_complete_day(chat_id, user_id, topic_id, day_number):
    if complete_day_for_user(user_id, topic_id, day_number):
        access_info = daily_reset.get_access_info(user_id, topic_id)
        msg = f"✅ تبریک! روز {day_number} ثبت شد.\n\n⏰ تمرین بعدی: فردا ساعت ۶ صبح\n⏳ زمان باقی‌مانده: {access_info['remaining_text']}"
        send_message(chat_id, msg, GraphicsHandler.create_main_menu_keyboard())
    else:
        send_message(chat_id, "✅ این روز قبلاً ثبت شده است.")

# ========== حلقه اصلی Polling ==========

def start_polling():
    keep_alive()
    print("🚀 Bot Started...")
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
                        elif "موضوعات" in text or text == "/topics" or text == "🎯 موضوعات شکرگزاری":
                            send_message(chat_id, "🎯 انتخاب موضوع:", GraphicsHandler.create_categories_keyboard())
                        elif text == "❓ راهنما":
                            send_message(chat_id, GraphicsHandler.create_help_message())
                        elif text == "👨‍💻 ارتباط با من":
                            send_message(chat_id, GraphicsHandler.create_contact_message())
                        elif text == "📊 پیشرفت کلی":
                            all_topics = get_all_topics()
                            total = sum([len(get_user_topic_progress(user_id, t['id']).get("completed_days", [])) for t in all_topics])
                            send_message(chat_id, f"🌟 **پیشرفت کلی شما**\n\n✅ شما مجموعاً **{total}** روز را با موفقیت شکرگزاری کرده‌اید. عالیه!")
                        else:
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
                            handle_complete_day(chat_id, user_id, int(p[1]), int(p[2]))
                        elif data.startswith("progress_"):
                            t_id = int(data.split("_")[1])
                            prog = get_user_topic_progress(user_id, t_id)
                            send_message(chat_id, f"📊 پیشرفت این موضوع: {len(prog.get('completed_days', []))} از ۲۸ روز.")
                        elif data == "support_developer":
                            invoice_url = f"{BASE_URL}/sendInvoice"
                            invoice_data = {
                                "chat_id": chat_id,
                                "title": "حمایت از توسعه‌دهنده",
                                "description": "حمایت مالی برای بهبود ربات شکرگزاری",
                                "payload": "support_payload",
                                "provider_token": PAYMENT_TOKEN,
                                "currency": "IRR",
                                "prices": [{"label": "حمایت", "amount": 100000}]
                            }
                            requests.post(invoice_url, json=invoice_data)

            time.sleep(0.5)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_polling()

