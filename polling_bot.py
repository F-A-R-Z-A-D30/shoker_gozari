import json
import os
import time
import requests
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import sys
import traceback

# اضافه کردن مسیر جاری به سیستم برای شناسایی لودر
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- بارگذاری ایمن ماژول‌ها ---
try:
    from loader import (
        load_day_content, 
        get_all_topics, 
        get_topic_by_id,
        start_topic_for_user, 
        complete_day_for_user, 
        get_user_topic_progress
    )
    print("✅ Loader imported successfully.")
except ImportError as e:
    print(f"❌ Error importing loader: {e}")
    # تلاش برای مسیر جایگزین در صورت نیاز
    try:
        from static.content.loader import (
            load_day_content, get_all_topics, get_topic_by_id,
            start_topic_for_user, complete_day_for_user, get_user_topic_progress
        )
    except:
        sys.exit(1)

from static.graphics_handler import GraphicsHandler
from daily_reset import daily_reset

load_dotenv()
BOT_TOKEN = os.getenv('BALE_BOT_TOKEN')
PAYMENT_TOKEN = os.getenv('BALE_PROVIDER_TOKEN', '')  # استفاده از مقدار پیش‌فرض
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

app = Flask('')

@app.route('/')
def home():
    return "✨ ربات شکرگزاری فعال است"

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
            print(f"⚠️ تصویر یافت نشد: {photo_path}")
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

# ========== توابع متن زیبا و کوتاه ==========

def create_about_me_text():
    """متن کوتاه درباره توسعه‌دهنده"""
    return """
<b>🧘🏻‍♂️ درباره من</b>

<code>─────────────────</code>

<b>👨‍💻 فرزاد قجری</b>
• توسعه‌دهنده ربات شکرگزاری
• معتقد به قدرت تغییر با شکرگزاری

<b>🎯 فلسفه این ربات:</b>
هدیه‌ای برای تمرکز بر داشته‌هایتان
بر اساس کتاب <b>"معجزه شکرگزاری"</b>

<b>🌟 چرا ساختم؟</b>
چون معتقدم شکرگزاری زندگی را متحول می‌کند.

<code>─────────────────</code>

<b>✨ شکرگزارم که هستی ✨</b>
"""

def create_support_text():
    """متن کوتاه برای بخش حمایت"""
    return """
<b>💝 حمایت از توسعه‌دهنده</b>

<code>─────────────────</code>

<b>🌟 چرا حمایت مهمه؟</b>
• ادامه توسعه ربات
• افزودن ویژگی‌های جدید
• بهبود کیفیت

<b>💳 شماره کارت:</b>
<code>۵۸۵۹-۸۳۱۰-۱۲۶۸-۶۱۶۷</code>
(بانک تجارت - به نام فرزاد قجری)

<b>📲 روش پرداخت:</b>
۱. از منوی بله، کیف پول را باز کنید
۲. حساب را شارژ کنید
۳. کارت به کارت کنید

<code>─────────────────</code>

<b>🙏 سپاس از حمایت شما</b>
"""

def create_progress_text(user_id):
    """متن کوتاه و حرفه‌ای برای بخش پیشرفت"""
    try:
        all_topics = get_all_topics()
        total_days = 28 * len(all_topics)
        completed_days = 0
        progress_details = ""
        
        for topic in all_topics:
            progress = get_user_topic_progress(user_id, topic['id'])
            topic_completed = len(progress.get("completed_days", []))
            completed_days += topic_completed
            
            # محاسبه درصد
            topic_percent = (topic_completed / 28) * 100 if 28 > 0 else 0
            
            # نوار پیشرفت
            progress_bars = "▓" * int(topic_percent / 10) + "░" * (10 - int(topic_percent / 10))
            
            # ایموجی وضعیت
            if topic_percent == 100:
                status_emoji = "🏆"
            elif topic_percent >= 75:
                status_emoji = "🌟"
            elif topic_percent >= 50:
                status_emoji = "👍"
            elif topic_percent >= 25:
                status_emoji = "💪"
            else:
                status_emoji = "🌱"
            
            progress_details += f"""
<b>{status_emoji} {topic['emoji']} {topic['name']}</b>
{progress_bars} <b>{topic_completed}/۲۸ روز</b>
<b>{topic_percent:.1f}%</b>
─────────────────
"""
        
        # محاسبه درصد کلی
        overall_percent = (completed_days / total_days) * 100 if total_days > 0 else 0
        
        # ایموجی وضعیت کلی
        if overall_percent == 100:
            overall_status = "🏆 <b>استاد شکرگزاری!</b>"
        elif overall_percent >= 75:
            overall_status = "🎯 <b>در آستانه استادی!</b>"
        elif overall_percent >= 50:
            overall_status = "✨ <b>در میانه راه!</b>"
        elif overall_percent >= 25:
            overall_status = "🚀 <b>شروع قدرتمند!</b>"
        else:
            overall_status = "🌱 <b>تازه شروع!</b>"
        
        # نوار پیشرفت کلی
        overall_bars = "█" * int(overall_percent / 10) + "▒" * (10 - int(overall_percent / 10))
        
        return f"""
<b>📊 پیشرفت شما</b>

<code>─────────────────</code>

{progress_details}
<b>{overall_status}</b>
{overall_bars}
<b>{completed_days} از {total_days} روز</b>
<b>{overall_percent:.1f}%</b>

<code>─────────────────</code>

<b>✨ ادامه دهید تا معجزه را ببینید ✨</b>
"""
        
    except Exception as e:
        print(f"Error in progress calculation: {e}")
        return """
<b>📊 پیشرفت شما</b>

<code>─────────────────</code>

<b>🌟 در حال محاسبه...</b>

<code>─────────────────</code>

<b>✨ مهم شروع کردن است ✨</b>
"""

# ========== منطق اصلی ربات ==========

def handle_start(chat_id, user_id):
    welcome_text = GraphicsHandler.create_welcome_message()
    send_message(chat_id, welcome_text)
    time.sleep(1)
    
    start_keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 شروع استفاده از ربات", "callback_data": "start_using"}],
            [{"text": "💝 حمایت", "callback_data": "support_developer"}],
            [{"text": "🧘🏻‍♂️ درباره من", "callback_data": "about_me"}]
        ]
    }
    send_message(chat_id, "🎯 برای شروع انتخاب کنید:", start_keyboard)

def handle_category_selection(chat_id, user_id, topic_id):
    try:
        user_progress = get_user_topic_progress(user_id, topic_id)
        access_info = daily_reset.get_access_info(user_id, topic_id)
        current_day = user_progress.get("current_day", 1)
        completed_days = user_progress.get("completed_days", [])
        topic_info = get_topic_by_id(topic_id)

        if not access_info["has_access"] and (current_day - 1) in completed_days:
            last_done = current_day - 1
            message = f"✅ <b>تمرین امروز انجام شده!</b>\n\n<b>{topic_info['emoji']} {topic_info['name']}</b>\n📅 روز {last_done} ثبت شد\n⏳ {access_info['remaining_text']}"
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
        
        # ارسال عکس به همراه متن
        photo_path = topic_info.get("image")
        if photo_path and os.path.exists(photo_path):
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
        msg = f"✅ <b>تبریک!</b> روز {day_number} ثبت شد.\n\n⏰ تمرین بعدی: فردا\n⏳ {access_info['remaining_text']}"
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
                            progress_text = create_progress_text(user_id)
                            send_message(chat_id, progress_text)
                        elif text == "🧘🏻‍♂️ درباره من":
                            about_text = create_about_me_text()
                            send_message(chat_id, about_text)
                        elif text == "💝 حمایت":
                            support_text = create_support_text()
                            send_message(chat_id, support_text)
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
                        elif data == "about_me":
                            about_text = create_about_me_text()
                            send_message(chat_id, about_text)
                        elif data.startswith("cat_"):
                            handle_category_selection(chat_id, user_id, int(data.split("_")[1]))
                        elif data.startswith("complete_"):
                            p = data.split("_")
                            handle_complete_day(chat_id, user_id, int(p[1]), int(p[2]))
                        elif data.startswith("progress_"):
                            progress_text = create_progress_text(user_id)
                            send_message(chat_id, progress_text)
                        elif data == "support_developer":
                            support_text = create_support_text()
                            support_keyboard = {
                                "inline_keyboard": [
                                    [{"text": "💳 شماره کارت", "callback_data": "card_number"}],
                                    [{"text": "📞 تماس", "url": "https://bale.me/farzadqj"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "main_menu"}]
                                ]
                            }
                            send_message(chat_id, support_text, support_keyboard)
                        elif data == "card_number":
                            # نمایش شماره کارت با فرمت زیبا
                            card_text = """
<b>💳 شماره کارت بانکی</b>

<code>─────────────────</code>

<b>بانک تجارت :</b>
<code>۵۸۵۹ ۸۳۱۰ ۱۲۶۸ ۶۱۶۷</code>

<b>به نام:</b>
<b>فرزاد قجری</b>

<code>─────────────────</code>

<b>🙏 سپاس از حمایت شما</b>
"""
                            send_message(chat_id, card_text)

            time.sleep(0.5)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
