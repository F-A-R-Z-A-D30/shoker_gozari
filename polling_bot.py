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
import re  # برای بررسی شماره تلفن

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
    if mongo_client is not None:  # اصلاح: مقایسه با None
        db = mongo_client['gratitude_bot']
        users_collection = db['registered_users']  # کاربران ثبت‌نام شده
        temp_users_collection = db['temp_users']   # کاربران در حال ثبت‌نام
        print("📊 دیتابیس MongoDB آماده است")
    else:
        print("⚠️ MongoDB در دسترس نیست")
        users_collection = None
        temp_users_collection = None
except Exception as e:
    print(f"⚠️ خطا در راه‌اندازی دیتابیس: {e}")
    users_collection = None
    temp_users_collection = None

# ========== سیستم رجیستر با شماره تلفن ==========

def validate_phone_number(phone):
    """اعتبارسنجی شماره تلفن ایرانی"""
    # حذف فاصله و کاراکترهای غیرعددی
    phone = re.sub(r'\D', '', phone)
    
    # الگوهای شماره تلفن ایران
    patterns = [
        r'^09[0-9]{9}$',        # موبایل: 09123456789
        r'^9[0-9]{9}$',         # موبایل بدون صفر: 9123456789
        r'^\+989[0-9]{9}$',     # موبایل با +98
        r'^00989[0-9]{9}$',     # موبایل با 0098
    ]
    
    for pattern in patterns:
        if re.match(pattern, phone):
            # نرمال‌سازی به فرمت 989xxxxxxxxx برای ذخیره
            if phone.startswith('0'):
                phone = '98' + phone[1:]
            elif phone.startswith('9'):
                phone = '98' + phone
            elif phone.startswith('+98'):
                phone = phone[1:]  # حذف +
            return phone
    
    return None

def register_user(user_id, username, first_name, last_name, phone_number):
    """ثبت‌نام کاربر در دیتابیس"""
    try:
        if users_collection is None:  # اصلاح: مقایسه با None
            return {"success": False, "message": "دیتابیس در دسترس نیست"}
        
        now = datetime.now()
        
        # بررسی آیا کاربر قبلاً ثبت‌نام کرده
        existing_user = users_collection.find_one({"user_id": str(user_id)})
        
        if existing_user:
            return {"success": False, "message": "شما قبلاً ثبت‌نام کرده‌اید"}
        
        # بررسی آیا شماره قبلاً استفاده شده
        existing_phone = users_collection.find_one({"phone_number": phone_number})
        if existing_phone:
            return {"success": False, "message": "این شماره قبلاً ثبت شده است"}
        
        # ذخیره کاربر
        user_data = {
            "user_id": str(user_id),
            "username": username or "",
            "first_name": first_name or "",
            "last_name": last_name or "",
            "full_name": f"{first_name or ''} {last_name or ''}".strip(),
            "phone_number": phone_number,
            "registration_date": now,
            "is_active": True,
            "total_days_completed": 0,
            "last_login": now,
            "registration_date_str": now.strftime("%Y-%m-%d")
        }
        
        users_collection.insert_one(user_data)
        
        # حذف از کاربران موقت
        if temp_users_collection is not None:  # اصلاح: مقایسه با None
            temp_users_collection.delete_one({"user_id": str(user_id)})
        
        print(f"✅ کاربر ثبت‌نام شد: {user_id} | شماره: {phone_number}")
        
        # آپدیت بیوگرافی ربات
        update_bot_profile()
        
        return {"success": True, "message": "ثبت‌نام شما با موفقیت انجام شد! 🎉"}
        
    except Exception as e:
        print(f"❌ خطا در ثبت‌نام کاربر: {e}")
        return {"success": False, "message": "خطا در ثبت‌نام، لطفاً مجدد تلاش کنید"}

def get_registered_users_count():
    """دریافت تعداد کاربران ثبت‌نام شده"""
    try:
        if users_collection is not None:  # اصلاح: مقایسه با None
            return users_collection.count_documents({})
        return 0
    except:
        return 0

def get_active_users_count():
    """دریافت تعداد کاربران فعال (30 روز گذشته)"""
    try:
        if users_collection is not None:  # اصلاح: مقایسه با None
            thirty_days_ago = datetime.now() - timedelta(days=30)
            return users_collection.count_documents({
                "last_login": {"$gte": thirty_days_ago}
            })
        return 0
    except:
        return 0

def update_bot_profile():
    """آپدیت پروفایل ربات با تعداد کاربران"""
    try:
        total_users = get_registered_users_count()
        active_users = get_active_users_count()
        
        # ایجاد متن برای بیوگرافی (حداکثر 70 کاراکتر در بله)
        bio_text = f"👥 {total_users} کاربر ثبت‌نامی"
        
        # اگر تعداد قابل توجهی کاربر فعال داریم
        if active_users > 0:
            bio_text = f"👥 {total_users} کاربر | 🔥 {active_users} فعال"
        
        # آپدیت نام ربات (اختیاری)
        name_text = f"معجزه شکرگزاری ({total_users}+)"
        
        # آپدیت بیوگرافی
        url = f"{BASE_URL}/setMyDescription"
        data = {"description": bio_text[:70]}  # محدودیت کاراکتر
        response = requests.post(url, json=data, timeout=5)
        
        # آپدیت نام ربات
        url_name = f"{BASE_URL}/setMyName"
        data_name = {"name": name_text[:64]}  # محدودیت کاراکتر نام
        requests.post(url_name, json=data_name, timeout=5)
        
        print(f"📊 پروفایل ربات آپدیت شد: {bio_text}")
        
    except Exception as e:
        print(f"⚠️ خطا در آپدیت پروفایل: {e}")

def start_registration(chat_id, user_id, username, first_name, last_name):
    """شروع فرآیند ثبت‌نام"""
    try:
        # بررسی آیا کاربر قبلاً ثبت‌نام کرده
        if users_collection is not None:  # اصلاح: مقایسه با None
            existing = users_collection.find_one({"user_id": str(user_id)})
            if existing:
                message = f"""
✅ شما قبلاً ثبت‌نام کرده‌اید!

👤 نام: {existing.get('full_name', '')}
📱 شماره: {existing.get('phone_number', '')}
📅 تاریخ ثبت‌نام: {existing.get('registration_date_str', '')}

🎯 اکنون می‌توانید از امکانات ربات استفاده کنید.
"""
                send_message(chat_id, message)
                return
        
        # ذخیره موقت اطلاعات کاربر
        if temp_users_collection is not None:  # اصلاح: مقایسه با None
            temp_users_collection.update_one(
                {"user_id": str(user_id)},
                {
                    "$set": {
                        "username": username or "",
                        "first_name": first_name or "",
                        "last_name": last_name or "",
                        "full_name": f"{first_name or ''} {last_name or ''}".strip(),
                        "chat_id": chat_id,
                        "registration_start": datetime.now()
                    }
                },
                upsert=True
            )
        
        # ارسال پیام درخواست شماره
        message = """
📱 **ثبت‌نام در ربات معجزه شکرگزاری**

برای استفاده کامل از ربات، لطفاً شماره تلفن خود را ارسال کنید.

✨ **مزایای ثبت‌نام:**
• دسترسی به تمامی تمرین‌ها
• ذخیره پیشرفت شخصی
• دریافت نوتیفیکیشن روزانه
• شرکت در چالش‌های ویژه

📌 **نحوه ارسال شماره:**
1. شماره موبایل خود را به صورت متن بفرستید
2. یا از دکمه «ارسال شماره» استفاده کنید

مثال: ۰۹۱۲۳۴۵۶۷۸۹
"""
        
        keyboard = {
            "keyboard": [
                [{"text": "📱 ارسال شماره تلفن", "request_contact": True}],
                [{"text": "🔙 بازگشت"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        
        send_message(chat_id, message, keyboard)
        
    except Exception as e:
        print(f"❌ خطا در شروع ثبت‌نام: {e}")
        send_message(chat_id, "⚠️ خطایی رخ داد، لطفاً مجدد تلاش کنید.")

def handle_phone_number(chat_id, user_id, phone_number):
    """پردازش شماره تلفن دریافتی"""
    try:
        # اعتبارسنجی شماره
        validated_phone = validate_phone_number(phone_number)
        
        if not validated_phone:
            message = """
⚠️ **شماره تلفن نامعتبر است**

لطفاً شماره موبایل معتبر ایرانی وارد کنید.

📌 فرمت صحیح:
• ۰۹۱۲۳۴۵۶۷۸۹
• ۹۱۲۳۴۵۶۷۸۹
• +۹۸۹۱۲۳۴۵۶۷۸۹

🔹 دوباره شماره خود را ارسال کنید:
"""
            send_message(chat_id, message)
            return
        
        # دریافت اطلاعات کاربر از دیتابیس موقت
        user_info = None
        if temp_users_collection is not None:  # اصلاح: مقایسه با None
            user_info = temp_users_collection.find_one({"user_id": str(user_id)})
        
        if not user_info:
            # اگر اطلاعات کاربر موجود نبود
            send_message(chat_id, "⚠️ لطفاً مجدداً فرآیند ثبت‌نام را شروع کنید.")
            return
        
        # ثبت‌نام کاربر
        result = register_user(
            user_id,
            user_info.get('username'),
            user_info.get('first_name'),
            user_info.get('last_name'),
            validated_phone
        )
        
        if result["success"]:
            # پاک کردن کیبورد
            remove_keyboard = {"remove_keyboard": True}
            send_message(chat_id, "✅", remove_keyboard)
            
            time.sleep(0.5)
            
            # ارسال پیام تبریک
            welcome_message = f"""
{result["message"]}

✨ **به خانواده شکرگزاری خوش آمدید!**

👤 **اطلاعات ثبت‌نام:**
• نام: {user_info.get('full_name', '')}
• شماره: {validated_phone}
• تاریخ: {datetime.now().strftime("%Y/%m/%d")}

🎯 **هم اکنون می‌توانید:**
• از تمرین‌های روزانه استفاده کنید
• پیشرفت خود را دنبال کنید
• در چالش‌ها شرکت کنید

📊 **آمار ربات:**
در حال حاضر {get_registered_users_count()} نفر در ربات ثبت‌نام کرده‌اند.

برای شروع روی دکمه زیر کلیک کنید:
"""
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🚀 شروع سفر شکرگزاری", "callback_data": "start_using"}],
                    [{"text": "📊 مشاهده آمار", "callback_data": "show_stats"}]
                ]
            }
            
            send_message(chat_id, welcome_message, keyboard)
            
        else:
            send_message(chat_id, result["message"])
            
    except Exception as e:
        print(f"❌ خطا در پردازش شماره: {e}")
        send_message(chat_id, "⚠️ خطایی رخ داد، لطفاً مجدد تلاش کنید.")

def show_registration_stats(chat_id):
    """نمایش آمار ثبت‌نام"""
    try:
        total_users = get_registered_users_count()
        active_users = get_active_users_count()
        
        # محاسبه کاربران جدید امروز
        today = datetime.now().strftime("%Y-%m-%d")
        new_today = 0
        if users_collection is not None:  # اصلاح: مقایسه با None
            new_today = users_collection.count_documents({
                "registration_date_str": today
            })
        
        # محاسبه درصد رشد روزانه
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        new_yesterday = 0
        if users_collection is not None:  # اصلاح: مقایسه با None
            new_yesterday = users_collection.count_documents({
                "registration_date_str": yesterday
            })
        
        growth_rate = 0
        if new_yesterday > 0:
            growth_rate = ((new_today - new_yesterday) / new_yesterday) * 100
        
        stats_message = f"""
📊 **آمار ثبت‌نام ربات شکرگزاری**

👥 **کاربران ثبت‌نام شده:**
├ کل کاربران: {total_users:,} نفر
├ فعال (۳۰ روز گذشته): {active_users:,} نفر
├ جدید امروز: {new_today:,} نفر
└ رشد روزانه: {growth_rate:+.1f}% 📈

📅 **تاریخچه ثبت‌نام:**
"""
        
        # آمار ۷ روز گذشته
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            day_count = 0
            if users_collection is not None:  # اصلاح: مقایسه با None
                day_count = users_collection.count_documents({
                    "registration_date_str": date
                })
            
            if day_count > 0:
                stats_message += f"├ {date}: {day_count} کاربر جدید\n"
        
        # ۵ کاربر آخر
        if users_collection is not None:  # اصلاح: مقایسه با None
            last_users = list(users_collection.find(
                {},
                {"full_name": 1, "registration_date_str": 1, "phone_number": 1}
            ).sort("registration_date", -1).limit(5))
            
            if last_users:
                stats_message += "\n👤 **آخرین کاربران:**\n"
                for i, user in enumerate(last_users, 1):
                    name = user.get("full_name", "بدون نام")
                    phone = user.get("phone_number", "")[-4:]  # ۴ رقم آخر
                    date = user.get("registration_date_str", "")
                    stats_message += f"{i}. {name} (...{phone}) - {date}\n"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 بروزرسانی آمار", "callback_data": "refresh_reg_stats"}],
                [{"text": "📥 خروجی Excel", "callback_data": "export_users"}],
                [{"text": "🏠 منوی اصلی", "callback_data": "main_menu"}]
            ]
        }
        
        send_message(chat_id, stats_message, keyboard)
        
    except Exception as e:
        print(f"⚠️ خطا در نمایش آمار: {e}")
        send_message(chat_id, "⚠️ خطایی در دریافت آمار رخ داد.")

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
        
        # آپدیت last_login کاربر
        if users_collection is not None:  # اصلاح: مقایسه با None
            users_collection.update_one(
                {"user_id": str(user_id)},
                {"$set": {"last_login": datetime.now()}}
            )
        
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

def handle_start(chat_id, user_id, username=None, first_name=None, last_name=None):
    """هندلر استارت جدید با چک ثبت‌نام"""
    welcome_text = GraphicsHandler.create_welcome_message()
    send_message(chat_id, welcome_text)
    time.sleep(1)
    
    # بررسی آیا کاربر ثبت‌نام کرده
    is_registered = False
    if users_collection is not None:  # اصلاح: مقایسه با None
        user_data = users_collection.find_one({"user_id": str(user_id)})
        is_registered = user_data is not None
    
    if is_registered:
        # کاربر ثبت‌نام کرده - منوی اصلی
        start_keyboard = {
            "inline_keyboard": [
                [{"text": "🚀 شروع سفر ۲۸ روزه", "callback_data": "start_using"}],
                [{"text": "📊 آمار ثبت‌نام", "callback_data": "show_reg_stats"}],
                [{"text": "💝 حمایت از توسعه", "callback_data": "support_developer"}],
                [{"text": "📖 راهنما", "callback_data": "help"}]
            ]
        }
        message = "✨ به ربات معجزه شکرگزاری خوش آمدید! انتخاب کنید:"
    else:
        # کاربر ثبت‌نام نکرده - درخواست ثبت‌نام
        start_keyboard = {
            "inline_keyboard": [
                [{"text": "📝 ثبت‌نام در ربات", "callback_data": "start_registration"}],
                [{"text": "❓ چرا باید ثبت‌نام کنم؟", "callback_data": "why_register"}],
                [{"text": "📊 آمار ربات", "callback_data": "show_reg_stats"}]
            ]
        }
        message = f"""
👋 سلام {first_name or 'عزیز'}!

برای استفاده از ربات **معجزه شکرگزاری**، لطفاً ثبت‌نام کنید.

📌 **لازمه ثبت‌نام:**
• شماره موبایل معتبر ایرانی
• فقط چند ثانیه زمان می‌برد

🎯 **پس از ثبت‌نام:**
• به تمام تمرین‌ها دسترسی دارید
• پیشرفت شما ذخیره می‌شود
• در چالش‌ها شرکت می‌کنید

👥 **در حال حاضر {get_registered_users_count()} نفر عضو ربات هستند.**

✨ انتخاب کنید:
"""
    
    send_message(chat_id, message, start_keyboard)

def handle_category_selection(chat_id, user_id, topic_id):
    """دسترسی به محتوا فقط برای کاربران ثبت‌نام شده"""
    try:
        # بررسی ثبت‌نام
        if users_collection is not None:  # اصلاح: مقایسه با None
            user_data = users_collection.find_one({"user_id": str(user_id)})
            if not user_data:
                # کاربر ثبت‌نام نکرده
                message = """
⛔ **دسترسی محدود**

برای استفاده از تمرین‌های شکرگزاری، ابتدا ثبت‌نام کنید.

📌 **مراحل ثبت‌نام:**
۱. روی دکمه «ثبت‌نام در ربات» کلیک کنید
۲. شماره موبایل خود را وارد کنید
۳. ثبت‌نام شما تأیید می‌شود
۴. دسترسی کامل پیدا می‌کنید

👥 **هم‌اکنون {get_registered_users_count()} نفر عضو هستند.**
"""
                message = message.format(get_registered_users_count())
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "📝 ثبت‌نام در ربات", "callback_data": "start_registration"}],
                        [{"text": "🔙 بازگشت", "callback_data": "main_menu"}]
                    ]
                }
                send_message(chat_id, message, keyboard)
                return
        
        # ادامه کد قبلی برای کاربران ثبت‌نام شده
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

# سایر توابع (handle_complete_day, handle_review_past_days, etc.) 
# مانند قبل باقی می‌مانند، فقط حتماً چک ثبت‌نام اضافه کنید

# ========== حلقه اصلی Polling ==========

def start_polling():
    keep_alive()
    print("🤖 ربات معجزه شکرگزاری فعال شد...")
    
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
                        
                        elif text == "📱 ارسال شماره تلفن":
                            # کاربر دکمه ارسال شماره را زده
                            message = """
لطفاً شماره تلفن خود را به صورت متن وارد کنید:

مثال: ۰۹۱۲۳۴۵۶۷۸۹

یا از دکمه اشتراک‌گذاری شماره در صفحه کلید استفاده کنید.
"""
                            send_message(chat_id, message)
                        
                        elif text == "🔙 بازگشت":
                            handle_start(chat_id, user_id, username, first_name, last_name)
                        
                        elif "شماره" in text or re.search(r'\d+', text):
                            # احتمالاً شماره تلفن ارسال شده
                            handle_phone_number(chat_id, user_id, text)
                        
                        elif text == "/stats":
                            show_registration_stats(chat_id)
                        
                        elif "موضوعات" in text or text == "/topics" or text == "🎯 موضوعات شکرگزاری":
                            # چک ثبت‌نام قبل از نمایش موضوعات
                            if users_collection is not None:  # اصلاح: مقایسه با None
                                user_data = users_collection.find_one({"user_id": str(user_id)})
                                if not user_data:
                                    send_message(chat_id, "⛔ ابتدا ثبت‌نام کنید.")
                                    continue
                            send_message(chat_id, "🎯 یک حوزه از زندگی خود را برای شکرگزاری انتخاب کنید:", GraphicsHandler.create_categories_keyboard())
                        
                        elif text == "📊 پیشرفت کلی":
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
                        
                        username = cb["from"].get("username", "")
                        first_name = cb["from"].get("first_name", "")
                        last_name = cb["from"].get("last_name", "")

                        if data == "start_registration":
                            start_registration(chat_id, user_id, username, first_name, last_name)
                        
                        elif data == "show_reg_stats" or data == "refresh_reg_stats":
                            show_registration_stats(chat_id)
                        
                        elif data == "why_register":
                            message = f"""
❓ **چرا باید ثبت‌نام کنم؟**

✨ **مزایای ثبت‌نام:**
۱. 🔐 **دسترسی کامل:** به تمامی ۲۸ روز هر موضوع
۲. 💾 **ذخیره پیشرفت:** تمرین‌های شما ذخیره می‌شود
۳. 📊 **گزارش شخصی:** نمودار پیشرفت روزانه
۴. 🎯 **چالش‌های ویژه:** فقط برای اعضا
۵. 🔔 **نوتیفیکیشن:** یادآوری تمرین روزانه

👥 **جامعه کاربران:**
در حال حاضر {get_registered_users_count()} نفر عضو ربات هستند.

📌 **اطلاعات شما محفوظ است:**
• شماره شما فقط برای احراز هویت استفاده می‌شود
• اطلاعات شخصی شما فروخته نمی‌شود
• می‌توانید هر زمان حساب خود را حذف کنید

✨ برای ثبت‌نام روی دکمه زیر کلیک کنید:
"""
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "📝 ثبت‌نام در ربات", "callback_data": "start_registration"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "main_menu"}]
                                ]
                            }
                            send_message(chat_id, message, keyboard)
                        
                        elif data == "main_menu":
                            handle_start(chat_id, user_id, username, first_name, last_name)
                        
                        # سایر callback ها مانند قبل
                        elif data in ["start_using", "categories"]:
                            # چک ثبت‌نام
                            if users_collection is not None:  # اصلاح: مقایسه با None
                                user_data = users_collection.find_one({"user_id": str(user_id)})
                                if not user_data:
                                    send_message(chat_id, "⛔ ابتدا ثبت‌نام کنید.")
                                    continue
                            send_message(chat_id, "🎯 یک حوزه از زندگی خود را برای شکرگزاری انتخاب کنید:", GraphicsHandler.create_categories_keyboard())
                        
                        # ... ادامه callback های دیگر

            time.sleep(0.5)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print("🤖 راه‌اندازی ربات معجزه شکرگزاری...")
    print(f"📊 دیتابیس: {'MongoDB ✅' if users_collection is not None else 'عدم دسترسی ⚠️'}")  # اصلاح: is not None
    print(f"👥 کاربران ثبت‌نام شده: {get_registered_users_count()}")
    start_polling()
