import json
import os
import time
import requests
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import sys
import traceback
from datetime import datetime, timedelta
from pymongo import MongoClient
import re

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
MONGO_URI = os.getenv('MONGO_URI')
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

# ========== اتصال به MongoDB ==========

def get_mongo_client():
    """ایجاد اتصال به MongoDB"""
    try:
        if MONGO_URI:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            print("✅ اتصال به MongoDB موفقیت‌آمیز بود")
            return client
        else:
            print("⚠️ MONGO_URI تعریف نشده است")
            return None
    except Exception as e:
        print(f"❌ خطا در اتصال به MongoDB: {e}")
        return None

try:
    mongo_client = get_mongo_client()
    if mongo_client is not None:
        db = mongo_client['gratitude_bot']
        registered_users = db['registered_users']
        print("📊 دیتابیس MongoDB آماده است")
    else:
        print("⚠️ MongoDB در دسترس نیست")
        registered_users = None
except Exception as e:
    print(f"⚠️ خطا در راه‌اندازی دیتابیس: {e}")
    registered_users = None

# ========== سیستم رجیستر سریع ==========

def validate_phone_number(phone):
    """اعتبارسنجی سریع شماره تلفن"""
    # حذف فاصله و کاراکترهای غیرعددی
    phone = re.sub(r'\D', '', phone)
    
    # الگوهای سریع
    if len(phone) < 10:
        return None
    
    # اگر با 0 شروع شده، 0 را حذف کن
    if phone.startswith('0'):
        phone = phone[1:]
    
    # اگر 10 رقم باقی ماند (مثلا 9123456789)
    if len(phone) == 10 and phone.startswith('9'):
        return f"98{phone}"
    
    # اگر 11 رقم بود و با 98 شروع شد
    if len(phone) == 11 and phone.startswith('98'):
        return phone
    
    # اگر 12 رقم بود و با 989 شروع شد
    if len(phone) == 12 and phone.startswith('989'):
        return phone
    
    return None

def is_user_registered(user_id):
    """چک کردن ثبت‌نام کاربر"""
    try:
        if registered_users is not None:
            user = registered_users.find_one({"user_id": str(user_id)})
            return user is not None
        return False
    except:
        return False

def quick_register(user_id, username, first_name, last_name, phone, name):
    """ثبت‌نام سریع کاربر"""
    try:
        if registered_users is None:
            return False
        
        # نرمال‌سازی شماره
        validated_phone = validate_phone_number(phone)
        if not validated_phone:
            return False
        
        # بررسی تکراری نبودن
        existing = registered_users.find_one({"user_id": str(user_id)})
        if existing:
            return True  # قبلاً ثبت‌نام کرده
        
        # ذخیره سریع
        user_data = {
            "user_id": str(user_id),
            "username": username or "",
            "first_name": first_name or "",
            "last_name": last_name or "",
            "full_name": name.strip(),
            "phone": validated_phone,
            "registered_at": datetime.now(),
            "is_active": True,
            "last_login": datetime.now()
        }
        
        registered_users.update_one(
            {"user_id": str(user_id)},
            {"$set": user_data},
            upsert=True
        )
        
        # آپدیت پروفایل
        update_bot_profile()
        
        print(f"✅ ثبت‌نام سریع: {user_id} - {name}")
        return True
    except Exception as e:
        print(f"❌ خطای ثبت‌نام سریع: {e}")
        return False

def get_user_count():
    """دریافت تعداد کاربران"""
    try:
        if registered_users is not None:
            return registered_users.count_documents({})
        return 0
    except:
        return 0

def update_bot_profile():
    """آپدیت پروفایل ربات"""
    try:
        user_count = get_user_count()
        
        # آپدیت نام
        name_url = f"{BASE_URL}/setMyName"
        name_data = {"name": f"معجزه شکرگزاری ({user_count}+)"}
        requests.post(name_url, json=name_data, timeout=3)
        
        # آپدیت بیوگرافی
        bio_url = f"{BASE_URL}/setMyDescription"
        bio_data = {"description": f"👥 {user_count} عضو | تمرین شکرگزاری"}
        requests.post(bio_url, json=bio_data, timeout=3)
        
        print(f"📊 پروفایل آپدیت شد: {user_count} کاربر")
    except Exception as e:
        print(f"⚠️ خطا در آپدیت پروفایل: {e}")

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

# ========== منطق اصلی ربات ==========

def handle_start(chat_id, user_id, username=None, first_name=None, last_name=None):
    """هندلر استارت جدید با فرم سریع"""
    
    # بررسی آیا کاربر ثبت‌نام کرده
    if is_user_registered(user_id):
        # کاربر ثبت‌نام کرده - مستقیماً به منو برو
        welcome_text = GraphicsHandler.create_welcome_message()
        send_message(chat_id, welcome_text)
        time.sleep(1)
        
        start_keyboard = {
            "inline_keyboard": [
                [{"text": "🚀 شروع سفر ۲۸ روزه", "callback_data": "start_using"}],
                [{"text": "📊 آمار ربات", "callback_data": "show_stats"}],
                [{"text": "💝 حمایت", "callback_data": "support_developer"}],
                [{"text": "📖 راهنما", "callback_data": "help"}]
            ]
        }
        
        send_message(chat_id, f"✨ خوش آمدید {first_name or 'عزیز'}! انتخاب کنید:", start_keyboard)
        return
    
    # کاربر جدید - نمایش فرم سریع
    welcome_text = GraphicsHandler.create_welcome_message()
    send_message(chat_id, welcome_text)
    time.sleep(1)
    
    form_message = f"""
📝 **فرم ثبت‌نام سریع**

سلام {first_name or 'عزیز'}! برای استفاده از ربات، لطفاً اطلاعات زیر را وارد کنید:

📌 **لطفاً در یک خط بنویسید:**
**نام و نام خانوادگی - شماره موبایل**

✨ **مثال:**
`علی محمدی - 09123456789`

🔹 **نکات مهم:**
• نام واقعی خود را وارد کنید
• شماره باید معتبر ایرانی باشد
• فقط ۱۰ ثانیه زمان می‌برد

👥 **در حال حاضر {get_user_count()} نفر عضو ربات هستند.**

📱 **همین حالا اطلاعات خود را وارد کنید:**
"""
    
    send_message(chat_id, form_message)

def handle_quick_form(chat_id, user_id, username, first_name, last_name, text):
    """پردازش فرم سریع کاربر"""
    try:
        # جدا کردن نام و شماره
        if '-' in text:
            parts = text.split('-', 1)
            name = parts[0].strip()
            phone = parts[1].strip()
        else:
            # اگر خط تایپ نکرد، سعی کن تشخیص بده
            import re
            phone_match = re.search(r'(\d{10,})', text)
            if phone_match:
                phone = phone_match.group(1)
                name = text.replace(phone, '').strip()
            else:
                send_message(chat_id, "⚠️ فرمت صحیح نیست.\n\nلطفاً به این صورت وارد کنید:\n`نام شما - 09123456789`")
                return
        
        # ثبت‌نام سریع
        success = quick_register(user_id, username, first_name, last_name, phone, name)
        
        if success:
            # پیام موفقیت
            success_msg = f"""
✅ **ثبت‌نام شما با موفقیت انجام شد!**

👤 **نام:** {name}
📱 **شماره:** {phone}
📅 **تاریخ:** {datetime.now().strftime("%Y/%m/%d")}

🎉 **به خانواده شکرگزاری خوش آمدید!**

✨ **حالا می‌توانید:**
• از تمرین‌های روزانه استفاده کنید
• پیشرفت خود را دنبال کنید
• در چالش‌ها شرکت کنید

👥 **شما کاربر {get_user_count()}ام ربات هستید.**

🚀 **برای شروع روی دکمه زیر کلیک کنید:**
"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🎯 شروع تمرین‌ها", "callback_data": "start_using"}],
                    [{"text": "📊 مشاهده آمار", "callback_data": "show_stats"}]
                ]
            }
            
            send_message(chat_id, success_msg, keyboard)
            
            # آپدیت پروفایل ربات
            update_bot_profile()
            
        else:
            error_msg = """
⚠️ **خطا در ثبت‌نام**

لطفاً دوباره سعی کنید:

📌 **فرمت صحیح:**
`نام و نام خانوادگی - شماره موبایل`

✨ **مثال صحیح:**
`علی محمدی - 09123456789`
`سارا احمدی - 9123456789`

📱 **دوباره اطلاعات خود را وارد کنید:**
"""
            send_message(chat_id, error_msg)
            
    except Exception as e:
        print(f"❌ خطا در پردازش فرم: {e}")
        send_message(chat_id, "⚠️ خطایی رخ داد. لطفاً مجدد اطلاعات را وارد کنید.")

def handle_category_selection(chat_id, user_id, topic_id):
    """دسترسی به محتوا"""
    try:
        # چک ثبت‌نام
        if not is_user_registered(user_id):
            # اگر ثبت‌نام نکرده، فرم نشان بده
            handle_start(chat_id, user_id)
            return
        
        # ادامه کد قبلی
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

# ========== حلقه اصلی Polling ==========

def start_polling():
    keep_alive()
    print("🤖 ربات معجزه شکرگزاری فعال شد...")
    print(f"📊 دیتابیس: {'MongoDB ✅' if registered_users is not None else 'عدم دسترسی ⚠️'}")
    print(f"👥 کاربران ثبت‌نام شده: {get_user_count()}")
    
    # آپدیت اولیه پروفایل
    try:
        update_bot_profile()
    except:
        pass
    
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
                        
                        username = msg["from"].get("username", "")
                        first_name = msg["from"].get("first_name", "")
                        last_name = msg["from"].get("last_name", "")
                        
                        text = msg.get("text", "")
                        
                        if text == "/start":
                            handle_start(chat_id, user_id, username, first_name, last_name)
                        
                        elif text == "/stats":
                            # نمایش آمار ساده
                            stats = f"""
📊 **آمار ربات شکرگزاری**

👥 کاربران ثبت‌نام شده: {get_user_count():,} نفر
✨ شما هم می‌توانید عضو شوید!

برای ثبت‌نام، دستور /start را بفرستید.
"""
                            send_message(chat_id, stats)
                        
                        elif "-" in text or re.search(r'\d{10,}', text):
                            # احتمالاً فرم ثبت‌نام است
                            handle_quick_form(chat_id, user_id, username, first_name, last_name, text)
                        
                        elif "موضوعات" in text or text == "/topics" or text == "🎯 موضوعات شکرگزاری":
                            # چک ثبت‌نام
                            if not is_user_registered(user_id):
                                handle_start(chat_id, user_id, username, first_name, last_name)
                                continue
                            send_message(chat_id, "🎯 یک حوزه از زندگی خود را برای شکرگزاری انتخاب کنید:", GraphicsHandler.create_categories_keyboard())
                        
                        elif text == "📊 پیشرفت کلی":
                            if not is_user_registered(user_id):
                                handle_start(chat_id, user_id, username, first_name, last_name)
                                continue
                            from main import create_progress_text
                            progress_text = create_progress_text(user_id)
                            send_message(chat_id, progress_text)
                        
                        elif text == "💝 حمایت":
                            from main import handle_support_developer
                            handle_support_developer(chat_id, user_id)
                        
                        else:
                            # اگر متن دیگر بود، شاید موضوع را انتخاب کرده
                            topics_found = False
                            for t in get_all_topics():
                                if t['name'] in text:
                                    handle_category_selection(chat_id, user_id, t['id'])
                                    topics_found = True
                                    break
                            
                            # اگر موضوعی پیدا نشد و کاربر ثبت‌نام نکرده
                            if not topics_found and not is_user_registered(user_id) and len(text) > 5:
                                # شاید کاربر فرم را اشتباه پر کرده
                                handle_start(chat_id, user_id, username, first_name, last_name)

                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        chat_id = cb["message"]["chat"]["id"]
                        user_id = str(cb["from"]["id"])
                        data = cb.get("data", "")
                        answer_callback(cb["id"])
                        
                        username = cb["from"].get("username", "")
                        first_name = cb["from"].get("first_name", "")
                        last_name = cb["from"].get("last_name", "")

                        if data == "start_using":
                            # چک ثبت‌نام
                            if not is_user_registered(user_id):
                                handle_start(chat_id, user_id, username, first_name, last_name)
                                continue
                            send_message(chat_id, "🎯 یک حوزه از زندگی خود را برای شکرگزاری انتخاب کنید:", GraphicsHandler.create_categories_keyboard())
                        
                        elif data == "show_stats":
                            stats = f"""
📊 **آمار ربات شکرگزاری**

👥 کاربران ثبت‌نام شده: {get_user_count():,} نفر

✨ پروفایل ربات:
معجزه شکرگزاری ({get_user_count()}+)
👥 {get_user_count()} عضو | تمرین شکرگزاری
"""
                            send_message(chat_id, stats)
                        
                        elif data in ["categories", "start_using"]:
                            if not is_user_registered(user_id):
                                handle_start(chat_id, user_id, username, first_name, last_name)
                                continue
                            send_message(chat_id, "🎯 یک حوزه از زندگی خود را برای شکرگزاری انتخاب کنید:", GraphicsHandler.create_categories_keyboard())
                        
                        elif data == "help":
                            from main import GraphicsHandler
                            send_message(chat_id, GraphicsHandler.create_help_message())
                        
                        elif data.startswith("cat_"):
                            if not is_user_registered(user_id):
                                handle_start(chat_id, user_id, username, first_name, last_name)
                                continue
                            handle_category_selection(chat_id, user_id, int(data.split("_")[1]))
                        
                        elif data == "main_menu":
                            handle_start(chat_id, user_id, username, first_name, last_name)

            time.sleep(0.5)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
