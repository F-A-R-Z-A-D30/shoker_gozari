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

try:
    from static.graphics_handler import GraphicsHandler
except ImportError:
    print("❌ فایل graphics_handler.py یافت نشد!")

try:
    from daily_reset import daily_reset
except ImportError:
    print("⚠️ daily_reset.py یافت نشد، استفاده از حالت ساده")

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

def send_message(chat_id, text, keyboard=None, reply_to=None):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    if reply_to:
        data["reply_to_message_id"] = reply_to
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
        return send_message(chat_id, caption, keyboard)

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

# ========== توابع مدیریت دکمه‌ها ==========

def handle_start(chat_id, user_id, first_name=""):
    welcome_text = f"""
✨✨✨
<b>سلام {first_name}! به ربات معجزه شکرگزاری خوش آمدید</b>

📖 بر اساس کتاب معجزه شکرگزاری اثر راندا برن

👨‍💻 <b>توسعه‌دهنده: فرزاد قجری</b>
من باور دارم شکرگزاری می‌تواند زندگی را متحول کند. این ربات هدیه‌ای است برای تمرکز بر داشته‌هایمان.

💫 <b>۸ حوزه اصلی زندگی:</b>
از سلامتی و روابط تا ثروت و معنویت.

<b>بیایید شروع کنیم!</b>
"""
    
    send_message(chat_id, welcome_text)
    time.sleep(0.5)
    
    start_keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 شروع استفاده از ربات", "callback_data": "start_using"}],
            [{"text": "💖 حمایت از ما", "callback_data": "support_developer"}],
            [{"text": "❓ راهنما", "callback_data": "help"}]
        ]
    }
    send_message(chat_id, "🎯 برای شروع، یکی از گزینه‌های زیر را انتخاب کنید:", start_keyboard)

def handle_category_selection(chat_id, user_id, topic_id):
    try:
        user_progress = get_user_topic_progress(user_id, topic_id)
        current_day = user_progress.get("current_day", 1)
        completed_days = user_progress.get("completed_days", [])
        topic_info = get_topic_by_id(topic_id)

        if not topic_info:
            send_message(chat_id, "❌ موضوع مورد نظر یافت نشد.")
            return

        # ۱. لود محتوا
        content = load_day_content(topic_id, current_day, user_id)
        if not content or not content.get('success', True):
            send_message(chat_id, "❌ متأسفانه محتوایی برای امروز یافت نشد.")
            return

        # ۲. متن پیام
        is_completed = content["day_number"] in completed_days
        msg_text = f"<b>{content['topic_emoji']} {content['topic_name']}</b>\n"
        msg_text += f"📅 روز {content['day_number']} از ۲۸\n"
        msg_text += f"<i>{content['intro']}</i>\n\n"
        
        for i, item in enumerate(content['items'][:10], 1):
            msg_text += f"{i}. {item}\n"

        if content.get('exercise'):
            msg_text += f"\n💡 <b>تمرین:</b> {content['exercise']}"

        # ۳. کیبورد و عکس
        inline_keyboard = create_day_inline_keyboard(topic_id, content['day_number'], is_completed)
        image_path = os.path.join("assets", topic_info.get("image", ""))

        if image_path and os.path.exists(image_path):
            send_photo(chat_id, image_path, caption=msg_text, keyboard=inline_keyboard)
        else:
            send_message(chat_id, msg_text, inline_keyboard)

    except Exception as e:
        print(f"❌ خطا در انتخاب موضوع: {e}")
        traceback.print_exc()
        send_message(chat_id, "❌ خطایی در پردازش درخواست رخ داد.")

def handle_support_developer(chat_id):
    support_text = """
💖 <b>حمایت از توسعه‌دهنده</b>

این ربات با عشق و علاقه توسعه داده شده است.
اگر مایل به حمایت مالی هستید:

💳 <b>شماره کارت بانکی:</b>
<code>6219-8610-2345-6789</code>

📱 <b>شماره تماس و پیام:</b>
<code>09302446141</code>

📧 <b>ایمیل:</b>
<code>farzadq.ir@gmail.com</code>

👨‍💻 <b>ارتباط برای سفارش پروژه:</b>
- طراحی و توسعه ربات‌های هوشمند
- ساخت وب‌سایت‌های اختصاصی
- برنامه‌نویسی پایتون و اتوماسیون

تشکر از حمایت شما! ❤️
"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "👨‍💻 ارتباط مستقیم", "url": "https://bale.me/farzadqj"}],
            [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "main_menu"}]
        ]
    }
    send_message(chat_id, support_text, keyboard)

def handle_contact_me(chat_id):
    contact_text = """
👨‍💻 <b>ارتباط با من</b>

📱 <b>شماره تماس:</b>
<code>09302446141</code>

📧 <b>ایمیل:</b>
<code>farzadq.ir@gmail.com</code>

💼 <b>خدمات ارائه شده:</b>
• طراحی و توسعه ربات‌های هوشمند
• ساخت وب‌سایت‌های اختصاصی
• برنامه‌نویسی پایتون و اتوماسیون
• مشاوره فنی پروژه‌های نرم‌افزاری

🌐 <b>ارتباط از طریق بله:</b>
برای ارتباط مستقیم در بله روی دکمه زیر کلیک کنید:
"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "👨‍💻 ارتباط در بله", "url": "https://bale.me/farzadqj"}],
            [{"text": "💖 حمایت مالی", "callback_data": "support_developer"}],
            [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "main_menu"}]
        ]
    }
    send_message(chat_id, contact_text, keyboard)

def handle_help(chat_id):
    help_text = """
❓ <b>راهنمای استفاده از ربات</b>

📖 <b>معجزه شکرگزاری چیست؟</b>
این ربات بر اساس کتاب معجزه شکرگزاری اثر راندا برن طراحی شده است.
هدف: ایجاد عادت روزانه شکرگزاری در ۸ حوزه اصلی زندگی.

🎯 <b>چگونه کار می‌کند؟</b>
۱. یک موضوع از ۸ موضوع اصلی انتخاب کنید
۲. هر روز ۱۰ مورد شکرگزاری دریافت می‌کنید
۳. بعد از مطالعه، دکمه «امروز شکرگزار بودم» را بزنید
۴. روز بعد تمرین جدید برای شما باز می‌شود

📅 <b>برنامه ۲۸ روزه:</b>
• هر موضوع ۲۸ روز تمرین دارد (۴ هفته)
• هر هفته ۷ تمرین روزانه
• تمرین‌ها به تدریج عمیق‌تر می‌شوند

🏆 <b>نکات مهم:</b>
• سعی کنید هر روز سر ساعت مشخصی تمرین کنید
• تمرین‌ها را با احساس و توجه انجام دهید
• تغییرات را در زندگی خود ثبت کنید
• صبور باشید، معجزه شکرگزاری تدریجی است

✨ <b>تعهد ۲۸ روزه باعث تغییر مدار ذهنی شما می‌شود!</b>
"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "🚀 شروع موضوعات", "callback_data": "categories"}],
            [{"text": "🔙 بازگشت", "callback_data": "main_menu"}]
        ]
    }
    send_message(chat_id, help_text, keyboard)

def handle_overall_progress(chat_id, user_id):
    try:
        topics = get_all_topics()
        total_completed = 0
        total_days = 28 * len(topics)
        
        progress_text = "📊 <b>پیشرفت کلی شما</b>\n\n"
        
        for topic in topics:
            user_progress = get_user_topic_progress(user_id, topic['id'])
            completed = len(user_progress.get("completed_days", []))
            total_completed += completed
            
            progress_percent = (completed / 28) * 100 if 28 > 0 else 0
            
            # نمایش نوار پیشرفت
            bars = int(progress_percent / 10)
            progress_bar = "▓" * bars + "░" * (10 - bars)
            
            progress_text += f"{topic['emoji']} <b>{topic['name']}</b>\n"
            progress_text += f"{progress_bar} {completed}/28 روز ({progress_percent:.1f}%)\n\n"
        
        overall_percent = (total_completed / total_days) * 100 if total_days > 0 else 0
        progress_text += f"📈 <b>جمع کل:</b> {total_completed} از {total_days} روز\n"
        progress_text += f"🏆 <b>پیشرفت کلی:</b> {overall_percent:.1f}%\n\n"
        
        if overall_percent == 100:
            progress_text += "🎉 <b>تبریک! شما تمام دوره‌ها را کامل کرده‌اید!</b> 🎉\n"
        elif overall_percent > 75:
            progress_text += "🌟 <b>عالی هستید! ادامه دهید!</b>\n"
        elif overall_percent > 50:
            progress_text += "👍 <b>خوب پیش می‌روید!</b>\n"
        elif overall_percent > 25:
            progress_text += "💪 <b>در مسیر درست هستید!</b>\n"
        else:
            progress_text += "🚀 <b>تازه شروع کرده‌اید! ادامه دهید!</b>\n"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "🎯 ادامه موضوعات", "callback_data": "categories"}],
                [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "main_menu"}]
            ]
        }
        
        send_message(chat_id, progress_text, keyboard)
        
    except Exception as e:
        print(f"❌ خطا در نمایش پیشرفت کلی: {e}")
        send_message(chat_id, "❌ خطایی در دریافت اطلاعات پیشرفت رخ داد.")

# ========== توابع کمکی ==========

def create_categories_keyboard():
    """ساخت کیبورد اینلاین برای موضوعات"""
    topics = get_all_topics()
    
    keyboard = {"inline_keyboard": []}
    
    # اضافه کردن موضوعات در ردیف‌های ۲ تایی
    row = []
    for i, topic in enumerate(topics):
        row.append({
            "text": f"{topic['emoji']} {topic['name']}",
            "callback_data": f"cat_{topic['id']}"
        })
        
        if (i + 1) % 2 == 0 or i == len(topics) - 1:
            keyboard["inline_keyboard"].append(row)
            row = []
    
    # اضافه کردن دکمه‌های پایین
    keyboard["inline_keyboard"].append([
        {"text": "📊 پیشرفت کلی", "callback_data": "overall_progress"},
        {"text": "❓ راهنما", "callback_data": "help"}
    ])
    keyboard["inline_keyboard"].append([
        {"text": "👨‍💻 ارتباط با من", "callback_data": "contact_me"},
        {"text": "💖 حمایت از ما", "callback_data": "support_developer"}
    ])
    
    return keyboard

def create_day_inline_keyboard(topic_id, day_number, is_completed=False):
    """ساخت کیبورد برای صفحه روز"""
    topics = get_all_topics()
    topic_emoji = "🙏"
    for topic in topics:
        if topic["id"] == topic_id:
            topic_emoji = topic["emoji"]
            break

    keyboard = {"inline_keyboard": []}

    # دکمه اصلی
    button_text = "✅ این روز ثبت شده" if is_completed else f"{topic_emoji} امروز شکرگزار بودم"
    
    keyboard["inline_keyboard"].append([
        {
            "text": button_text,
            "callback_data": f"complete_{topic_id}_{day_number}"
        }
    ])

    # دکمه‌های پایین
    keyboard["inline_keyboard"].append([
        {"text": "📊 پیشرفت موضوع", "callback_data": f"progress_{topic_id}"},
        {"text": "🎯 موضوعات دیگر", "callback_data": "categories"}
    ])
    
    keyboard["inline_keyboard"].append([
        {"text": "🔙 بازگشت به منوی اصلی", "callback_data": "main_menu"}
    ])

    return keyboard

def create_main_menu_keyboard():
    """منوی اصلی (کیبورد ریپلای)"""
    return {
        "keyboard": [
            ["🎯 موضوعات شکرگزاری"],
            ["📊 پیشرفت کلی", "❓ راهنما"],
            ["👨‍💻 ارتباط با من", "💖 حمایت از ما"]
        ],
        "resize_keyboard": True
    }

# ========== تابع اصلی پولینگ ==========

def start_polling():
    keep_alive()
    print("🚀 ربات معجزه شکرگزاری شروع به کار کرد...")
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
                        text = msg.get("text", "").strip()
                        first_name = msg["from"].get("first_name", "")
                        
                        print(f"📩 پیام از {first_name} ({user_id}): {text}")
                        
                        if text == "/start":
                            handle_start(chat_id, user_id, first_name)
                            
                        elif text == "/help" or text == "❓ راهنما":
                            handle_help(chat_id)
                            
                        elif text == "/topics" or text == "🎯 موضوعات شکرگزاری" or "موضوعات" in text:
                            keyboard = create_categories_keyboard()
                            send_message(chat_id, "🎯 لطفاً یکی از موضوعات زیر را انتخاب کنید:", keyboard)
                            
                        elif text == "📊 پیشرفت کلی":
                            handle_overall_progress(chat_id, user_id)
                            
                        elif text == "👨‍💻 ارتباط با من":
                            handle_contact_me(chat_id)
                            
                        elif text == "💖 حمایت از ما":
                            handle_support_developer(chat_id)
                            
                        elif text and text.startswith("/"):
                            send_message(chat_id, "❌ دستور نامعتبر است. از /start استفاده کنید.")
                            
                        else:
                            # چک کردن کلیک روی کیبورد متنی موضوعات
                            topics = get_all_topics()
                            for topic in topics:
                                if topic['name'] in text or topic['emoji'] in text:
                                    handle_category_selection(chat_id, user_id, topic['id'])
                                    break

                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        chat_id = cb["message"]["chat"]["id"]
                        user_id = str(cb["from"]["id"])
                        data = cb.get("data", "")
                        
                        print(f"🔘 کلیک از {user_id}: {data}")
                        
                        # پاسخ به کلیک (برای برداشتن ساعت)
                        answer_callback(cb["id"])
                        
                        if data == "start_using":
                            keyboard = create_categories_keyboard()
                            send_message(chat_id, "🎯 لطفاً یکی از موضوعات زیر را انتخاب کنید:", keyboard)
                            
                        elif data == "categories":
                            keyboard = create_categories_keyboard()
                            send_message(chat_id, "🎯 لطفاً یکی از موضوعات زیر را انتخاب کنید:", keyboard)
                            
                        elif data == "main_menu":
                            handle_start(chat_id, user_id)
                            
                        elif data == "help":
                            handle_help(chat_id)
                            
                        elif data == "support_developer":
                            handle_support_developer(chat_id)
                            
                        elif data == "contact_me":
                            handle_contact_me(chat_id)
                            
                        elif data == "overall_progress":
                            handle_overall_progress(chat_id, user_id)
                            
                        elif data.startswith("cat_"):
                            topic_id = int(data.split("_")[1])
                            handle_category_selection(chat_id, user_id, topic_id)
                            
                        elif data.startswith("complete_"):
                            p = data.split("_")
                            topic_id = int(p[1])
                            day_number = int(p[2])
                            
                            # ثبت روز کامل شده
                            complete_day_for_user(user_id, topic_id, day_number)
                            
                            # ارسال پیام تأیید
                            send_message(chat_id, f"✅ تبریک! تمرین روز {day_number} با موفقیت ثبت شد. 🎉")
                            
                            # نمایش منوی ادامه
                            time.sleep(1)
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "📅 روز بعد", "callback_data": f"cat_{topic_id}"}],
                                    [{"text": "🎯 موضوعات دیگر", "callback_data": "categories"}],
                                    [{"text": "📊 پیشرفت کلی", "callback_data": "overall_progress"}]
                                ]
                            }
                            send_message(chat_id, "🎯 برای ادامه یکی از گزینه‌های زیر را انتخاب کنید:", keyboard)
                            
                        elif data.startswith("progress_"):
                            topic_id = int(data.split("_")[1])
                            topic_info = get_topic_by_id(topic_id)
                            user_progress = get_user_topic_progress(user_id, topic_id)
                            
                            if topic_info and user_progress:
                                completed = len(user_progress.get("completed_days", []))
                                progress_percent = (completed / 28) * 100 if 28 > 0 else 0
                                
                                # ساخت نوار پیشرفت
                                bars = int(progress_percent / 10)
                                progress_bar = "▓" * bars + "░" * (10 - bars)
                                
                                progress_text = f"📊 <b>پیشرفت در {topic_info['emoji']} {topic_info['name']}</b>\n\n"
                                progress_text += f"{progress_bar} {completed}/28 روز\n\n"
                                progress_text += f"✅ روزهای تکمیل شده: {completed}\n"
                                progress_text += f"📅 روز جاری: {user_progress.get('current_day', 1)}\n"
                                progress_text += f"🏆 درصد پیشرفت: {progress_percent:.1f}%\n\n"
                                
                                if completed == 28:
                                    progress_text += "🎉 <b>تبریک! شما این موضوع را کامل کرده‌اید!</b>\n"
                                elif completed >= 21:
                                    progress_text += "🌟 <b>عالی! نزدیک به پایان هستید!</b>\n"
                                elif completed >= 14:
                                    progress_text += "👍 <b>خوب پیش می‌روید!</b>\n"
                                
                                keyboard = {
                                    "inline_keyboard": [
                                        [{"text": "🔙 بازگشت به موضوع", "callback_data": f"cat_{topic_id}"}],
                                        [{"text": "📊 پیشرفت کلی", "callback_data": "overall_progress"}]
                                    ]
                                }
                                send_message(chat_id, progress_text, keyboard)

            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\n🛑 ربات متوقف شد.")
            break
            
        except Exception as e:
            print(f"⚠️ خطای حلقه اصلی: {e}")
            traceback.print_exc()
            time.sleep(5)

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 ربات معجزه شکرگزاری - نسخه بهبود یافته")
    print(f"📁 مسیر جاری: {BASE_DIR}")
    print(f"🤵 توکن: {'موجود' if BOT_TOKEN else '❌ یافت نشد'}")
    print("=" * 50)
    
    if not BOT_TOKEN:
        print("❌ خطا: BALE_BOT_TOKEN در فایل .env تنظیم نشده است!")
        print("لطفاً ابتدا فایل .env را ایجاد کنید و توکن ربات را وارد کنید.")
    else:
        start_polling()
