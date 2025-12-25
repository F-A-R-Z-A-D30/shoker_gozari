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

# --- بخش ایمپورت‌ها ---
try:
    from loader import (
        load_day_content, get_all_topics, get_topic_by_id,
        start_topic_for_user, complete_day_for_user, get_user_topic_progress
    )
except ImportError:
    from static.content.loader import (
        load_day_content, get_all_topics, get_topic_by_id,
        start_topic_for_user, complete_day_for_user, get_user_topic_progress
    )

from static.graphics_handler import GraphicsHandler
from daily_reset import daily_reset

# --- تنظیمات سرور Flask ---
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

# بارگذاری متغیرها
load_dotenv()
BOT_TOKEN = os.getenv('BALE_BOT_TOKEN')
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

# ========== توابع ارتباط با API بله ==========

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

# ========== مدیریت منطق اصلی ربات ==========

def handle_start(chat_id, user_id):
    welcome_text = GraphicsHandler.create_welcome_message()
    send_message(chat_id, welcome_text)
    time.sleep(1)
    
    start_keyboard = {
        "inline_keyboard": [
            [{"text": "💖 حمایت از توسعه‌دهنده", "callback_data": "support_developer"}],
            [{"text": "🚀 شروع استفاده از ربات", "callback_data": "start_using"}]
        ]
    }
    send_message(chat_id, "🎯 برای شروع، یکی از گزینه‌های زیر را انتخاب کنید:", start_keyboard)

def handle_category_selection(chat_id, user_id, topic_id):
    """بخش اصلاح شده برای مدیریت زمان‌بندی ۶ صبح"""
    try:
        # ۱. دریافت پیشرفت و اطلاعات دسترسی
        user_progress = get_user_topic_progress(user_id, topic_id)
        access_info = daily_reset.get_access_info(user_id, topic_id)
        
        current_day = user_progress.get("current_day", 1)
        completed_days = user_progress.get("completed_days", [])
        topic_info = get_topic_by_id(topic_id)

        # ۲. بررسی: آیا کاربر امروز قبلاً تمرین رو انجام داده؟
        # اگر دسترسی نداشته باشه و روز فعلی منهای یک در لیست انجام شده‌ها باشه
        if not access_info["has_access"] and (current_day - 1) in completed_days:
            last_done = current_day - 1
            message = f"""
✅ <b>تمرین امروز با موفقیت انجام شده!</b>

{topic_info['emoji']} موضوع: <b>{topic_info['name']}</b>
📅 شما تمرین <b>روز {last_done}</b> را با موفقیت ثبت کردید.

⏰ <b>زمان بازنشانی:</b> فردا ساعت ۶ صبح
⏳ <b>مانده تا تمرین بعدی:</b> {access_info['remaining_text']}

🌟 <i>فردا صبح منتظر شما هستیم تا روز {current_day} را با هم شروع کنیم.</i>
"""
            keyboard = {
                "inline_keyboard": [
                    [{"text": f"📖 مرور روز {last_done}", "callback_data": f"review_{topic_id}_{last_done}"}],
                    [{"text": "🎯 انتخاب موضوع دیگر", "callback_data": "categories"}]
                ]
            }
            send_message(chat_id, message, keyboard)
            return

        # ۳. لود کردن محتوا (اگر دسترسی دارد یا اولین بار است)
        if not user_progress.get("started", False):
            content = start_topic_for_user(user_id, topic_id)
        else:
            content = load_day_content(topic_id, current_day, user_id)

        if not content:
            send_message(chat_id, "❌ خطا در بارگذاری محتوا.")
            return

        # ثبت زمان دسترسی در دیتابیس
        daily_reset.record_access(user_id, topic_id, content['day_number'])

        # نمایش محتوای روز
        is_completed = content["day_number"] in completed_days
        message = f"""
{content['topic_emoji'] * 3}
<b>{content['week_title']}</b>
📖 {content.get('author_quote', '')}

<b>{content['topic_name']}</b>
📅 روز {content['day_number']} از ۲۸
🕕 بازنشانی: ساعت ۶ صبح

<i>{content['intro']}</i>
──────────────
{content['topic_emoji']} <b>۱۰ شکرگزاری امروز:</b>
"""
        for i, item in enumerate(content['items'][:10], 1):
            message += f"\n{i}. {item}"

        message += "\n──────────────\n"
        if content.get('exercise'):
            message += f"💡 <b>تمرین:</b> {content['exercise']}\n\n"
        
        if is_completed:
            message += "✅ <b>این روز تکمیل شده است.</b>"
        else:
            message += "🙏 پس از انجام، دکمه زیر را بزنید:"

        inline_keyboard = GraphicsHandler.create_day_inline_keyboard(
            topic_id, content['day_number'], is_completed
        )
        send_message(chat_id, message, inline_keyboard)
        
        # ارسال منوی سریع
        markup_keyboard = GraphicsHandler.create_main_menu_keyboard()
        send_message(chat_id, "🔽 منوی دسترسی:", markup_keyboard)

    except Exception as e:
        traceback.print_exc()
        send_message(chat_id, "⚠️ خطا در سیستم زمان‌بندی. لطفاً دوباره تلاش کنید.")

def handle_complete_day(chat_id, user_id, topic_id, day_number):
    if complete_day_for_user(user_id, topic_id, day_number):
        access_info = daily_reset.get_access_info(user_id, topic_id)
        msg = f"✅ تبریک! روز {day_number} ثبت شد.\n\n⏰ تمرین بعدی: فردا ساعت ۶ صبح\n⏳ زمان باقی‌مانده: {access_info['remaining_text']}"
        send_message(chat_id, msg, GraphicsHandler.create_main_menu_keyboard())
    else:
        send_message(chat_id, "✅ این روز قبلاً ثبت شده بود.")

# ========== حلقه اصلی (Polling) ==========

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
                        elif "موضوعات" in text or text == "/topics":
                            send_message(chat_id, "🎯 انتخاب موضوع:", GraphicsHandler.create_categories_keyboard())
                        else:
                            # تشخیص کلیک دکمه‌های منوی اصلی (متنی)
                            topics = get_all_topics()
                            for t in topics:
                                if t['name'] in text:
                                    handle_category_selection(chat_id, user_id, t['id'])
                                    break

                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        chat_id = cb["message"]["chat"]["id"]
                        user_id = str(cb["from"]["id"])
                        data = cb.get("data", "")
                        answer_callback(cb["id"])

                        if data == "start_using" or data == "categories":
                            send_message(chat_id, "🎯 انتخاب موضوع:", GraphicsHandler.create_categories_keyboard())
                        elif data.startswith("cat_"):
                            handle_category_selection(chat_id, user_id, int(data.split("_")[1]))
                        elif data.startswith("complete_"):
                            p = data.split("_")
                            handle_complete_day(chat_id, user_id, int(p[1]), int(p[2]))
                        elif data == "support_developer":
                            send_message(chat_id, "💖 ممنون از نیت خیر شما. سیستم پرداخت در حال بروزرسانی است.")

            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
