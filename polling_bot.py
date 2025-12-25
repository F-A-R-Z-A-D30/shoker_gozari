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
PAYMENT_TOKEN = os.getenv('BALE_PROVIDER_TOKEN') 
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

app = Flask('')

@app.route('/')
def home():
    return "✨ ربات معجزه شکرگزاری فعال است ✨"

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

# ========== توابع متن زیبا ==========

def create_about_me_text():
    """متن زیبا درباره توسعه‌دهنده"""
    return """
<b>🎭 درباره من</b>

<blockquote>
"هر آنچه امروز هستم، محصول قدردانی از داشته‌هایم است."
</blockquote>

<b>🧘🏻‍♂️ من فرزاد قجری هستم:</b>
• توسعه‌دهنده این ربات شکرگزاری
• معتقد به قدرت تغییر با شکرگزاری روزانه
• بیش از ۵ سال تجربه در برنامه‌نویسی و توسعه

<b>🎯 فلسفه این ربات:</b>
ربات معجزه شکرگزاری، هدیه‌ای است برای تمرکز بر داشته‌هایمان. 
بر اساس کتاب ارزشمند <b>"معجزه شکرگزاری" اثر راندا برن</b> طراحی شده است.

<b>🌟 چرا این ربات را ساختم؟</b>
چون باور دارم شکرگزاری می‌تواند زندگی هر فردی را متحول کند. 
این ربات، همراهی است برای ۲۸ روز تمرین مستمر تا شکرگزاری 
تبدیل به سبک زندگی شما شود.

<b>💫 آرزویم:</b>
امیدوارم این ربات جرقه‌ای باشد برای شروع تحولی بزرگ در زندگی شما.

<pre>──────────────</pre>
<b>🧠 جمله الهام‌بخش من:</b>
<i>"شما تبدیل به آنچه شکرگزارش هستید، می‌شوید."</i>
<pre>──────────────</pre>

✨ شکرگزارم که هستی و این لحظات را با من سهیم می‌شوی ✨
"""

def create_support_text():
    """متن زیبا برای بخش حمایت"""
    return """
<b>💝 حمایت از توسعه‌دهنده</b>

<blockquote>
"هر حمایت، انرژی ادامه دادن می‌دهد."
</blockquote>

<b>🌟 چرا حمایت شما مهم است؟</b>
این ربات با عشق و زمان زیادی توسعه یافته و به صورت کاملاً <b>رایگان</b> 
در اختیار شما قرار گرفته است. حمایت شما انگیزه‌ای است برای:
• افزودن ویژگی‌های جدید
• بهبود مستمر ربات
• توسعه محتوای بیشتر

<b>💳 نحوه حمایت در <b>بله</b>:</b>
۱. ابتدا از منوی بله، بخش <b>«کیف پول»</b> را باز کنید
۲. حساب خود را <b>شارژ</b> کنید (از درگاه بانکی)
۳. سپس به ربات بازگردید و روی دکمه حمایت کلیک کنید
۴. مبلغ مورد نظر خود را انتخاب و پرداخت کنید

<b>💰 روش‌های دیگر حمایت:</b>
• <b>کارت به کارت:</b>
<code>۶۲۱۹-۸۶۱۰-۲۳۴۵-۶۷۸۹</code>
(به نام فرزاد قجری)

• <b>دریافت لینک پرداخت:</b> (روی دکمه زیر کلیک کنید)

<pre>──────────────</pre>
<b>🎁 در ازای حمایت شما:</b>
• انرژی مثبت و دعای خیر
• آرزوی بهترین‌ها برای شما
• ادامه توسعه ربات با انگیزه بیشتر

<pre>──────────────</pre>
<b>🙏 سپاس از بودن شما</b>
هر حمایت، حتی کوچک، نشانه‌ای از قدرشناسی شماست.
"""

def create_progress_text(user_id):
    """متن زیبا و حرفه‌ای برای بخش پیشرفت"""
    try:
        all_topics = get_all_topics()
        total_days = 28 * len(all_topics)
        completed_days = 0
        progress_details = ""
        
        for topic in all_topics:
            progress = get_user_topic_progress(user_id, topic['id'])
            topic_completed = len(progress.get("completed_days", []))
            completed_days += topic_completed
            
            # محاسبه درصد برای هر موضوع
            topic_percent = (topic_completed / 28) * 100 if 28 > 0 else 0
            
            # ساخت نوار پیشرفت زیبا
            progress_bars = ""
            filled = int(topic_percent / 10)
            for i in range(10):
                if i < filled:
                    progress_bars += "▓"
                else:
                    progress_bars += "░"
            
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
{status_emoji} <b>{topic['emoji']} {topic['name']}</b>
{progress_bars} {topic_completed}/۲۸ روز
<i>پیشرفت: {topic_percent:.1f}%</i>
──────────────────
"""
        
        # محاسبه درصد کلی
        overall_percent = (completed_days / total_days) * 100 if total_days > 0 else 0
        
        # ایموجی وضعیت کلی
        if overall_percent == 100:
            overall_emoji = "👑"
            overall_status = "<b>شما یک استاد شکرگزاری هستید!</b>"
        elif overall_percent >= 75:
            overall_emoji = "🎯"
            overall_status = "<b>در آستانه استادی!</b>"
        elif overall_percent >= 50:
            overall_emoji = "✨"
            overall_status = "<b>در میانه راه!</b>"
        elif overall_percent >= 25:
            overall_emoji = "🚀"
            overall_status = "<b>شروع قدرتمند!</b>"
        else:
            overall_emoji = "🌱"
            overall_status = "<b>تازه شروع کرده‌اید!</b>"
        
        # ساخت نوار پیشرفت کلی
        overall_bars = ""
        overall_filled = int(overall_percent / 10)
        for i in range(10):
            if i < overall_filled:
                overall_bars += "█"
            else:
                overall_bars += "▒"
        
        progress_text = f"""
<b>📊 نقشه سفر شکرگزاری شما</b>

{progress_details}
<b>{overall_emoji} پیشرفت کلی شما:</b>
{overall_bars}
<b>{completed_days} از {total_days} روز</b>
<i>پیشرفت کلی: {overall_percent:.1f}%</i>

<b>🎯 وضعیت فعلی:</b>
{overall_status}

<pre>──────────────────</pre>
<b>💡 نکات تحلیلی:</b>
"""
        
        # اضافه کردن نکات تحلیلی بر اساس پیشرفت
        if overall_percent == 100:
            progress_text += "✅ شما تمام مسیر را طی کرده‌اید!\n🌟 شکرگزاری در DNA شما جاری است.\n✨ به دیگران هم آموزش دهید!"
        elif overall_percent >= 75:
            progress_text += "✅ نزدیک به پایان هستید!\n🌟 ادامه دهید تا استاد شوید.\n✨ تمرین‌های هفته آخر عمیق‌ترین‌ها هستند."
        elif overall_percent >= 50:
            progress_text += "✅ نیمه راه را طی کرده‌اید!\n🌟 تغییرات را احساس می‌کنید.\n✨ هر روز عمیق‌تر از دیروز شکرگزاری کنید."
        elif overall_percent >= 25:
            progress_text += "✅ شروع خوبی داشته‌اید!\n🌟 عادت در حال شکل‌گیری است.\n✨ در هفته‌های آینده معجزه را خواهید دید."
        else:
            progress_text += "✅ اولین قدم‌ها را برداشته‌اید!\n🌟 مهم ترین بخش، شروع است.\n✨ ادامه دهید تا شاهد معجزه باشید."
        
        progress_text += """
──────────────────
<b>🎁 نکته طلایی:</b>
<i>"پیشرفت مهم‌تر از سرعت است.
هر روز یک قدم، شما را به مقصد می‌رساند."</i>
──────────────────

✨ <b>قدردان تلاش ارزشمند شما هستم</b> ✨
"""
        
        return progress_text
        
    except Exception as e:
        print(f"Error in progress calculation: {e}")
        return """
<b>📊 پیشرفت شما</b>

🌟 در حال محاسبه پیشرفت شما هستم...
لطفاً لحظاتی صبر کنید یا دوباره تلاش کنید.

✨ <i>مهم نیست از کجا شروع کرده‌اید،
مهم این است که شروع کرده‌اید.</i>
"""

# ========== منطق اصلی ربات ==========

def handle_start(chat_id, user_id):
    welcome_text = GraphicsHandler.create_welcome_message()
    send_message(chat_id, welcome_text)
    time.sleep(1)
    
    start_keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 شروع استفاده از ربات", "callback_data": "start_using"}],
            [{"text": "💖 حمایت از توسعه‌دهنده", "callback_data": "support_developer"}],
            [{"text": "🎭 درباره من", "callback_data": "about_me"}]
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
                            # استفاده از تابع جدید پیشرفت
                            progress_text = create_progress_text(user_id)
                            send_message(chat_id, progress_text)
                        elif text == "🎭 درباره من":
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
                            # استفاده از تابع جدید پیشرفت
                            progress_text = create_progress_text(user_id)
                            send_message(chat_id, progress_text)
                        elif data == "support_developer":
                            # ارسال متن حمایت زیبا
                            support_text = create_support_text()
                            support_keyboard = {
                                "inline_keyboard": [
                                    [{"text": "💳 پرداخت در بله", "callback_data": "payment_in_bale"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "main_menu"}]
                                ]
                            }
                            send_message(chat_id, support_text, support_keyboard)
                        elif data == "payment_in_bale":
                            if PAYMENT_TOKEN:
                                # ایجاد فاکتور پرداخت
                                invoice_url = f"{BASE_URL}/sendInvoice"
                                invoice_data = {
                                    "chat_id": chat_id,
                                    "title": "🏆 حمایت از توسعه‌دهنده ربات شکرگزاری",
                                    "description": "حمایت مالی برای ادامه توسعه و بهبود ربات معجزه شکرگزاری\n\n💝 هر میزان حمایت شما قدردانی می‌شود.",
                                    "payload": "support_payment",
                                    "provider_token": PAYMENT_TOKEN,
                                    "currency": "IRR",
                                    "prices": [
                                        {"label": "🌱 حمایت تشویقی", "amount": 100000},
                                        {"label": "💫 حمایت ویژه", "amount": 500000},
                                        {"label": "🌟 حمایت استثنایی", "amount": 1000000}
                                    ],
                                    "suggested_tip_amounts": [100000, 500000, 1000000],
                                    "photo_url": "https://example.com/support.jpg",  # اگر عکس دارید
                                    "need_name": False,
                                    "need_phone_number": False,
                                    "need_email": False,
                                    "need_shipping_address": False,
                                    "is_flexible": False
                                }
                                try:
                                    response = requests.post(invoice_url, json=invoice_data)
                                    if response.status_code == 200:
                                        print(f"✅ Invoice sent to {user_id}")
                                    else:
                                        print(f"❌ Failed to send invoice: {response.text}")
                                        send_message(chat_id, "⚠️ در حال حاضر امکان پرداخت وجود ندارد. لطفاً از روش کارت به کارت استفاده کنید.")
                                except Exception as e:
                                    print(f"❌ Error sending invoice: {e}")
                                    send_message(chat_id, "⚠️ خطایی در ایجاد درگاه پرداخت رخ داد.")
                            else:
                                send_message(chat_id, "⚠️ درگاه پرداخت فعال نیست. لطفاً از روش کارت به کارت استفاده کنید.")

            time.sleep(0.5)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
