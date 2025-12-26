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
        get_user_topic_progress,
        load_past_day_content
    )
    print("✅ Loader imported successfully.")
except ImportError as e:
    print(f"❌ Error importing loader: {e}")
    try:
        from static.content.loader import (
            load_day_content, get_all_topics, get_topic_by_id,
            start_topic_for_user, complete_day_for_user, get_user_topic_progress,
            load_past_day_content
        )
    except:
        sys.exit(1)

from static.graphics_handler import GraphicsHandler
from daily_reset import daily_reset

load_dotenv()
BOT_TOKEN = os.getenv('BALE_BOT_TOKEN')
PAYMENT_TOKEN = os.getenv('BALE_PROVIDER_TOKEN') 
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

app = Flask('')

@app.route('/')
def home():
    return "🤖 ربات معجزه شکرگزاری فعال است ✨"

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

# ========== توابع کمکی ==========

def create_progress_text(user_id):
    """📊 ساخت متن پیشرفت حرفه‌ای"""
    try:
        all_topics = get_all_topics()
        total_days = 28 * len(all_topics)
        completed_days = 0
        progress_details = ""
        
        for topic in all_topics:
            progress = get_user_topic_progress(user_id, topic['id'])
            topic_completed = len(progress.get("completed_days", []))
            completed_days += topic_completed
            
            topic_percent = (topic_completed / 28) * 100 if 28 > 0 else 0
            
            if topic_percent == 100:
                progress_emoji = "🏆"
                status_text = "کامل شده!"
            elif topic_percent >= 75:
                progress_emoji = "✨"
                status_text = "عالی!"
            elif topic_percent >= 50:
                progress_emoji = "🚀"
                status_text = "خوب!"
            elif topic_percent >= 25:
                progress_emoji = "💪"
                status_text = "ادامه دهید!"
            else:
                progress_emoji = "🌱"
                status_text = "شروع شده"
            
            filled_bars = int(topic_percent / 5)
            progress_bar = "█" * filled_bars + "░" * (20 - filled_bars)
            
            progress_details += f"""
{progress_emoji} {topic['emoji']} {topic['name']}
{progress_bar}
{topic_percent:.1f}% • {topic_completed}/۲۸ روز • {status_text}
─────────────────
"""
        
        overall_percent = (completed_days / total_days) * 100 if total_days > 0 else 0
        
        if overall_percent == 100:
            overall_emoji = "👑"
            overall_status = "شما استاد شکرگزاری هستید!"
            motivation = "🎉 به همه معجزه‌های زندگی‌تان دست یافته‌اید!"
        elif overall_percent >= 75:
            overall_emoji = "🌟"
            overall_status = "در آستانه استادی!"
            motivation = "✨ چند گام دیگر تا تحول کامل باقی مانده!"
        elif overall_percent >= 50:
            overall_emoji = "⚡"
            overall_status = "در میانه راه!"
            motivation = "🚀 نیمه راه را طی کرده‌اید، ادامه دهید!"
        elif overall_percent >= 25:
            overall_emoji = "🔥"
            overall_status = "شروع قدرتمند!"
            motivation = "💪 عادت در حال شکل‌گیری است!"
        else:
            overall_emoji = "🌷"
            overall_status = "تازه شروع کرده‌اید!"
            motivation = "🌱 مهم‌ترین قدم را برداشته‌اید!"
        
        overall_filled = int(overall_percent / 5)
        overall_bar = "▓" * overall_filled + "░" * (20 - overall_filled)
        
        progress_text = f"""
📈 نقشه سفر شکرگزاری شما

══════════════════════════════

{progress_details}
══════════════════════════════

{overall_emoji} پیشرفت کلی:
{overall_bar}
{overall_percent:.1f}% • {completed_days} از {total_days} روز

✨ {overall_status}
💫 {motivation}

══════════════════════════════

🎯 نکته طلایی:
"هر درصد، قدمی به سوی تحول است.
شما در مسیر درست قرار دارید!"
"""
        
        return progress_text
        
    except Exception as e:
        print(f"Error in progress calculation: {e}")
        return """
📊 پیشرفت شما

══════════════════════════════

🔄 در حال محاسبه...

══════════════════════════════

✨ مهم این است که شروع کرده‌اید!
"""

# ========== منطق اصلی ربات ==========

def handle_start(chat_id, user_id):
    welcome_text = GraphicsHandler.create_welcome_message()
    send_message(chat_id, welcome_text)
    time.sleep(1)
    
    start_keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 شروع سفر ۲۸ روزه", "callback_data": "start_using"}],
            [{"text": "💝 حمایت از توسعه", "callback_data": "support_developer"}],
            [{"text": "📖 راهنما", "callback_data": "help"}]
        ]
    }
    send_message(chat_id, "✨ انتخاب کنید:", start_keyboard)

def handle_category_selection(chat_id, user_id, topic_id):
    try:
        user_progress = get_user_topic_progress(user_id, topic_id)
        access_info = daily_reset.get_access_info(user_id, topic_id)
        current_day = user_progress.get("current_day", 1)
        completed_days = user_progress.get("completed_days", [])
        topic_info = get_topic_by_id(topic_id)

        if not access_info["has_access"] and (current_day - 1) in completed_days:
            last_done = current_day - 1
            message = f"""
✅ تمرین امروز تکمیل شد!

{topic_info['emoji']} {topic_info['name']}
📅 روز {last_done} ثبت گردید.
⏳ تمرین بعدی: {access_info['remaining_text']}

🎯 برای ادامه، موضوع جدیدی را انتخاب کنید.
"""
            keyboard = GraphicsHandler.create_day_options_keyboard(topic_id, completed_days)
            send_message(chat_id, message, keyboard)
            return

        content = load_day_content(topic_id, current_day, user_id)
        if not content:
            send_message(chat_id, "⚠️ خطا در دریافت محتوا.\nلطفاً لحظاتی بعد مجدد تلاش کنید.")
            return

        daily_reset.record_access(user_id, topic_id, content['day_number'])
        is_completed = content["day_number"] in completed_days
        
        msg_text = GraphicsHandler.create_beautiful_message(topic_info['name'], content['day_number'], user_progress)
        inline_keyboard = GraphicsHandler.create_day_inline_keyboard(topic_id, content['day_number'], is_completed, completed_days)
        
        photo_path = topic_info.get("image")
        if photo_path and os.path.exists(photo_path):
            send_photo(chat_id, photo_path, caption=msg_text, keyboard=inline_keyboard)
        else:
            send_message(chat_id, msg_text, inline_keyboard)
            
        send_message(chat_id, "👇 منوی سریع:", GraphicsHandler.create_main_menu_keyboard())

    except Exception as e:
        traceback.print_exc()
        send_message(chat_id, "⚠️ مشکل موقتی پیش آمد.\nسیستم در حال به‌روزرسانی است.")

def handle_complete_day(chat_id, user_id, topic_id, day_number):
    """ثبت تکمیل روز و ارسال پیام تبریک مجزا"""
    try:
        if complete_day_for_user(user_id, topic_id, day_number):
            topic_info = get_topic_by_id(topic_id)
            access_info = daily_reset.get_access_info(user_id, topic_id)
            
            msg = f"""
🎉 تبریک!

✅ تمرین امروز با موفقیت تکمیل شد

{topic_info['emoji']} {topic_info['name']}
📅 روز {day_number} از ۲۸ ثبت گردید

⏰ تمرین بعدی: فردا ساعت ۶ صبح
⏳ زمان باقی‌مانده: {access_info['remaining_text']}

✨ شما یک قدم به تحول نزدیک‌تر شدید!
ادامه دهید تا معجزه را ببینید...
"""
            
            send_message(chat_id, msg)
            
            time.sleep(1)
            continue_keyboard = {
                "inline_keyboard": [
                    [{"text": "📅 روز بعد", "callback_data": f"cat_{topic_id}"}],
                    [{"text": "🎯 موضوعات دیگر", "callback_data": "categories"}],
                    [{"text": "📊 پیشرفت کلی", "callback_data": "overall_progress"}]
                ]
            }
            send_message(chat_id, "🎯 برای ادامه:", continue_keyboard)
            
        else:
            msg = f"""
✅ این روز قبلاً ثبت شده است

📅 روز {day_number} از ۲۸
✨ قدردان تعهد شما به شکرگزاری هستیم!
"""
            send_message(chat_id, msg)
            
    except Exception as e:
        print(f"❌ خطا در ثبت روز: {e}")
        send_message(chat_id, "⚠️ خطایی در ثبت روز رخ داد.\nلطفاً مجدد تلاش کنید.")

def handle_review_past_days(chat_id, user_id, topic_id):
    """نمایش روزهای گذشته برای مرور"""
    try:
        user_progress = get_user_topic_progress(user_id, topic_id)
        completed_days = user_progress.get("completed_days", [])
        topic_info = get_topic_by_id(topic_id)
        
        if not completed_days:
            message = f"""
📚 هنوز روزی برای مرور ندارید!

{topic_info['emoji']} {topic_info['name']}
✨ اولین روز این موضوع را شروع کنید تا بتوانید بعداً مرور کنید.

🎯 برای شروع روز اول، روی موضوع کلیک کنید.
"""
            send_message(chat_id, message)
            return
        
        message = f"""
📖 مرور روزهای گذشته

{topic_info['emoji']} {topic_info['name']}
✅ شما {len(completed_days)} روز را تکمیل کرده‌اید.

✨ روزهایی که می‌توانید مرور کنید:
"""
        for day in sorted(completed_days):
            message += f"\n📅 روز {day}"
        
        keyboard = GraphicsHandler.create_past_days_keyboard(topic_id, completed_days)
        send_message(chat_id, message, keyboard)
        
    except Exception as e:
        print(f"Error in review past days: {e}")
        send_message(chat_id, "⚠️ خطایی در دریافت روزهای گذشته رخ داد.")

def handle_show_past_day(chat_id, user_id, topic_id, day_number):
    """نمایش محتوای یک روز گذشته برای مرور"""
    try:
        content = load_past_day_content(topic_id, day_number, user_id)
        if not content or not content.get('success', True):
            send_message(chat_id, "⚠️ محتوای این روز در دسترس نیست.")
            return
            
        topic_info = get_topic_by_id(topic_id)
        user_progress = get_user_topic_progress(user_id, topic_id)
        completed_days = user_progress.get("completed_days", [])
        is_completed = day_number in completed_days
        
        msg_text = GraphicsHandler.create_beautiful_message(topic_info['name'], day_number, user_progress)
        keyboard = GraphicsHandler.create_review_keyboard(topic_id, day_number, completed_days)
        
        photo_path = topic_info.get("image")
        if photo_path and os.path.exists(photo_path):
            send_photo(chat_id, photo_path, caption=msg_text, keyboard=keyboard)
        else:
            send_message(chat_id, msg_text, keyboard)
            
    except Exception as e:
        print(f"Error showing past day: {e}")
        send_message(chat_id, "⚠️ خطایی در نمایش محتوا رخ داد.")

def handle_support_developer(chat_id, user_id=None):
    """هندلر حمایت توسعه‌دهنده"""
    invoice_url = f"{BASE_URL}/sendInvoice"
    invoice_data = {
        "chat_id": chat_id,
        "title": "💝 حمایت از توسعه‌دهنده",
        "description": "✨ حمایت شما انگیزه ادامه توسعه این ربات است\n\n🎯 هر میزان حمایت، قدردانی می‌شود",
        "payload": "support_payload",
        "provider_token": PAYMENT_TOKEN,
        "currency": "IRR",
        "prices": [
            {"label": "🌱 حمایت دوستانه", "amount": 200000},
            {"label": "💫 حمایت ویژه", "amount": 500000},
            {"label": "🌟 حمایت استثنایی", "amount": 1000000},
            {"label": "✨ مبلغ دلخواه", "amount": 0}
        ],
        "suggested_tip_amounts": [200000, 500000, 1000000, 0],
        "is_flexible": True
    }
    try:
        response = requests.post(invoice_url, json=invoice_data)
        if response.status_code != 200:
            print(f"⚠️ خطا در ارسال فاکتور: {response.text}")
            send_message(chat_id, "⚠️ در حال حاضر امکان پرداخت وجود ندارد. لطفاً از روش کارت به کارت استفاده کنید.")
    except Exception as e:
        print(f"❌ Error sending invoice: {e}")
        send_message(chat_id, "⚠️ خطایی در ایجاد درگاه پرداخت رخ داد.")

# ========== حلقه اصلی Polling ==========

def start_polling():
    keep_alive()
    print("🤖 ربات معجزه شکرگزاری فعال شد...")
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
                            send_message(chat_id, "🎯 یک حوزه از زندگی خود را برای شکرگزاری انتخاب کنید:", GraphicsHandler.create_categories_keyboard())
                        elif text == "❓ راهنما":
                            send_message(chat_id, GraphicsHandler.create_help_message())
                        elif text == "👨‍💻 ارتباط با من":
                            send_message(chat_id, GraphicsHandler.create_contact_message())
                        elif text == "📊 پیشرفت کلی":
                            progress_text = create_progress_text(user_id)
                            send_message(chat_id, progress_text)
                        elif text == "💝 حمایت":
                            handle_support_developer(chat_id, user_id)
                        elif text == "overall_progress":
                            progress_text = create_progress_text(user_id)
                            send_message(chat_id, progress_text)
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
                            send_message(chat_id, "🎯 یک حوزه از زندگی خود را برای شکرگزاری انتخاب کنید:", GraphicsHandler.create_categories_keyboard())
                        elif data == "help":
                            send_message(chat_id, GraphicsHandler.create_help_message())
                        elif data.startswith("cat_"):
                            handle_category_selection(chat_id, user_id, int(data.split("_")[1]))
                        elif data.startswith("complete_"):
                            p = data.split("_")
                            handle_complete_day(chat_id, user_id, int(p[1]), int(p[2]))
                        elif data.startswith("progress_"):
                            progress_text = create_progress_text(user_id)
                            send_message(chat_id, progress_text)
                        elif data == "overall_progress":
                            progress_text = create_progress_text(user_id)
                            send_message(chat_id, progress_text)
                        elif data.startswith("review_"):
                            parts = data.split("_")
                            topic_id = int(parts[1])
                            handle_review_past_days(chat_id, user_id, topic_id)
                        elif data.startswith("pastday_"):
                            parts = data.split("_")
                            topic_id = int(parts[1])
                            day_number = int(parts[2])
                            handle_show_past_day(chat_id, user_id, topic_id, day_number)
                        elif data == "support_developer":
                            handle_support_developer(chat_id, user_id)

            time.sleep(0.5)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
